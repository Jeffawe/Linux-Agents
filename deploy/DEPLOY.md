# Deploying linux-agents with systemd

Target layout: repo checked out at `/opt/linux-agents`, running as the
unprivileged user `serveruser`, managed by systemd unit `linux-agents.service`.

The unit file lives in this repo at `deploy/linux-agents.service` so it's
versioned alongside the code, but the copy systemd actually reads is
`/etc/systemd/system/linux-agents.service` (root-owned). Always `cp` into
place rather than symlinking the repo checkout directly into
`/etc/systemd/system/` — `serveruser` owns the checkout, and a unit file that
systemd loads straight out of a location that account can write to is a
privilege-escalation path (it could edit `User=` or add an `ExecStartPre=`
and have it run as root on the next reload).

## Liveness: watchdog, not a 6h timer

The Telegram long-polling connection can go silently dead (e.g. after the host
suspends/resumes or a network blip) while the process itself keeps running — no
exception, no exit, just a socket that looks `ESTAB` but never receives another
update. `Restart=on-failure` can't recover from that since nothing ever "fails".

This used to be handled with `RuntimeMaxSec=21600`, a blanket restart every 6h.
That worked, but it restarted the service 4x/day whether or not anything was
wrong, and each restart announced itself over Telegram — the charger/startup
message spam. It's now a real liveness check instead:

- `Type=notify` + `WatchdogSec=180`: the app sends `READY=1` once collectors are
  up, then pings `WATCHDOG=1` every 90s — but only while every collector reports
  itself healthy (`core/watchdog.py`).
- `TelegramCollector` calls `get_me()` every 60s while the updater is polling.
  A run of failures outlasting `TELEGRAM_HEALTH_TIMEOUT` (default 900s) stops the
  pings, so systemd restarts the process. Time spent in the reconnect/backoff
  path counts as healthy — that loop already heals itself.
- `PowerCollector` beats once per poll, so a wedged loop is caught within ~20s.
- Health uses `time.monotonic()`, which excludes suspend, so a laptop waking from
  sleep is not mistaken for a stall.

`Restart=always` is still required: systemd does not treat `KillSignal=SIGINT`
(or any clean exit) as a failure, so `on-failure` would silently not restart the
service after a graceful stop.

`StateDirectory=linux-agents` gives the app `/var/lib/linux-agents` (created and
chowned by systemd, exposed as `$STATE_DIRECTORY`). It holds the clean-shutdown
marker: an intentional stop writes it, and startup only sends a Telegram alert
when it's missing — i.e. only when the restart was *not* asked for. Deploys and
`systemctl restart` stay quiet; crashes and watchdog kills still notify.

`Environment=PYTHONUNBUFFERED=1` matters more than it looks: without it Python
block-buffers stdout into the journal pipe and only flushes at exit, so log lines
appear under the timestamp of the *next* shutdown rather than when they happened.

## First-time deploy

1. Clone the repo:
   ```
   sudo git clone <repo-url> /opt/linux-agents
   ```

2. Create the virtualenv and install dependencies:
   ```
   cd /opt/linux-agents
   sudo python3 -m venv .venv
   sudo .venv/bin/pip install -r requirements.txt
   ```

3. Create `/opt/linux-agents/.env` by hand (it's gitignored, `git pull` never
   brings it over). Required/optional vars:
   ```
   TELEGRAM_TOKEN=<bot token>
   TELEGRAM_CHAT_ID=<chat id>
   POWER_FILE_PATH=/sys/class/power_supply/BAT1/capacity   # optional, this is the default
   AC_FILE_PATH=/sys/class/power_supply/ACAD/online        # optional, this is the default
   TELEGRAM_HEALTH_TIMEOUT=900                             # optional, seconds of failed
                                                           # probes before the watchdog
                                                           # restarts the service
   ```
   Lock it down:
   ```
   sudo chmod 600 /opt/linux-agents/.env
   ```

4. Confirm `serveruser` exists, then hand the checkout over to it:
   ```
   id serveruser   # create it first if this fails
   sudo chown -R serveruser:serveruser /opt/linux-agents
   ```

5. Verify the battery/AC hardware paths are actually readable as
   `serveruser` (paths vary by machine — check `ls /sys/class/power_supply/`
   if this fails and update `.env` accordingly):
   ```
   sudo -u serveruser cat /sys/class/power_supply/BAT1/capacity
   sudo -u serveruser cat /sys/class/power_supply/ACAD/online
   ```

6. Dry-run the app manually before wiring up systemd. Ctrl+C should print
   "Shutting down..." — that confirms the graceful-shutdown path works. Outside
   systemd there is no `$NOTIFY_SOCKET`, so it logs "No systemd watchdog
   configured" and writes its marker to `./.state/` instead of
   `/var/lib/linux-agents/`:
   ```
   sudo -u serveruser /opt/linux-agents/.venv/bin/python3 /opt/linux-agents/main.py
   ```

7. Install the unit file (copy, don't symlink — see note above):
   ```
   sudo cp /opt/linux-agents/deploy/linux-agents.service /etc/systemd/system/linux-agents.service
   sudo chown root:root /etc/systemd/system/linux-agents.service
   sudo chmod 644 /etc/systemd/system/linux-agents.service
   ```

8. Enable and start:
   ```
   sudo systemctl daemon-reload
   sudo systemctl enable --now linux-agents
   sudo systemctl status linux-agents
   journalctl -u linux-agents -f
   ```

## Redeploy (after a code update)

1. Pull the update:
   ```
   cd /opt/linux-agents
   sudo -u serveruser git pull
   ```

2. Re-sync dependencies (harmless no-op if `requirements.txt` didn't change):
   ```
   sudo .venv/bin/pip install -r requirements.txt
   ```

3. If `deploy/linux-agents.service` changed, re-install it (diff first if
   you want to see what changed):
   ```
   diff /opt/linux-agents/deploy/linux-agents.service /etc/systemd/system/linux-agents.service
   sudo cp /opt/linux-agents/deploy/linux-agents.service /etc/systemd/system/linux-agents.service
   sudo systemctl daemon-reload
   ```

4. Restart the service:
   ```
   sudo systemctl restart linux-agents
   sudo systemctl status linux-agents
   journalctl -u linux-agents -f
   ```
