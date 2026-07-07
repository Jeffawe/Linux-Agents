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

`Restart=always` + `RuntimeMaxSec=21600` forces a clean restart every 6h.
This isn't just for crashes: the Telegram long-polling connection can go
silently dead (e.g. after the host suspends/resumes or a network blip) while
the process itself keeps running — no exception, no exit, just a socket that
looks `ESTAB` but never receives another update. `Restart=on-failure` alone
won't recover from that since nothing ever "fails". The periodic restart is
a blunt but reliable backstop; `Restart=always` is required because systemd
does not treat `KillSignal=SIGINT` (or any clean exit) as a failure, so
`on-failure` would silently not restart the service once `RuntimeMaxSec` (or
graceful KillSignal restarts) stop it.

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
   "Shutting down..." — that confirms the graceful-shutdown path works:
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
