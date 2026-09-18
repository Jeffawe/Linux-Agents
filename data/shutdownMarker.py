import os

MARKER_NAME = "clean-shutdown"


def _state_dir():
    # systemd hands StateDirectory= over as $STATE_DIRECTORY (colon-separated).
    from_systemd = os.getenv("STATE_DIRECTORY")

    if from_systemd:
        return from_systemd.split(":")[0]

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(repo_root, ".state")


def _marker_path():
    return os.path.join(_state_dir(), MARKER_NAME)


def mark_clean_shutdown():
    """Record that this stop was intentional.

    Stays synchronous on purpose: Bus.publish runs sync subscribers inline, so
    the marker is on disk before the process can exit. A task scheduled from the
    signal handler might never get a turn.
    """
    path = _marker_path()

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w") as f:
            f.write("clean\n")
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        print(f"Could not record clean shutdown: {e}")


def consume_clean_shutdown():
    """True if the previous run stopped cleanly. Clears the marker either way."""
    path = _marker_path()

    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        print(f"Could not read the clean shutdown marker: {e}")
        return False
