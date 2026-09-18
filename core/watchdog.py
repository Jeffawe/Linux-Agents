import asyncio
import os
import socket


def _notify_socket_address():
    addr = os.getenv("NOTIFY_SOCKET")

    if not addr:
        return None

    # systemd spells abstract-namespace sockets with a leading "@".
    if addr.startswith("@"):
        return "\0" + addr[1:]

    return addr


def notify(message):
    """Send one datagram to systemd's notify socket. No-op outside systemd."""
    addr = _notify_socket_address()

    if not addr:
        return False

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC) as sock:
            sock.connect(addr)
            sock.sendall(message.encode())

        return True
    except OSError as e:
        print(f"Could not reach the systemd notify socket: {e}")
        return False


def notify_ready():
    """Tell systemd we finished starting up (required by Type=notify)."""
    return notify("READY=1")


def watchdog_interval():
    """Seconds between pings, or None when systemd configured no watchdog."""
    usec = os.getenv("WATCHDOG_USEC")

    if not usec:
        return None

    # systemd only honours pings from the PID it started unless NotifyAccess=all.
    pid = os.getenv("WATCHDOG_PID")

    if pid and pid != str(os.getpid()):
        return None

    try:
        # systemd asks to be pinged at half the configured interval.
        return int(usec) / 2_000_000
    except ValueError:
        return None


async def run_watchdog(collectors, stopping):
    """Ping systemd only while every collector still looks alive.

    Withholding the ping is the whole mechanism: a collector that has silently
    stopped making progress (the dead Telegram long-poll this service used to
    restart on a 6h timer) lets WatchdogSec expire and systemd restarts us.
    """
    interval = watchdog_interval()

    if interval is None:
        print("No systemd watchdog configured; liveness pings disabled")
        return

    print(f"systemd watchdog active; pinging every {interval:.0f}s while collectors are healthy")

    while not stopping.is_set():
        try:
            await asyncio.wait_for(stopping.wait(), timeout=interval)
            return  # shutting down
        except TimeoutError:
            pass

        unhealthy = [type(c).__name__ for c in collectors if not c.is_healthy()]

        if unhealthy:
            print(f"⚠️  Withholding watchdog ping, unhealthy collectors: {', '.join(unhealthy)}")
            continue

        notify("WATCHDOG=1")
