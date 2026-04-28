# DNSmasq Lease Viewer

A slightly over-engineered but lightweight web app that displays DHCP lease information from a dnsmasq server's lease file, along with basic system information (system load, memory usage, uptime, hostname). This is currently used to display DHCP leases handed out from a Raspberry Pi 3 running `dnsmasq` in a homelab.


## Features

- Parses the dnsmasq lease file and displays leases in a table, reverse sorted by lease expiry time, which usually results in the most recent lease being on top
- Fields displayed: Lease expiry time, MAC address, IP address, hostname as seen by `dnsmasq`. The DHCP client ID field is returned by the server but ignored by the frontend for now (I am not using it; my `dnsmasq` is running with `dhcp-ignore-clid`)
- Auto-refreshes every 5 seconds
- Shows some system info: CPU load, memory usage, uptime, hostname
- Displays "(reboot required)" next to the Uptime label when `/var/run/reboot-required` exists on the host
- Times and dates should be displayed using the client/browser's time zone conventions if correctly configured in the browser and/or the client OS.
- Connection status banner (Hidden unless needed)
  - Alerts if the backend is offline
  - Alerts if the lease file cannot be read (permission denied/wrong path/corrupt file)
- Dark theme toggle
- Minimal dependencies — uses only Python stdlib
- Network access control — restricts access to specific IP ranges
- Deployment toolkit included (more info below)

This is what it looks like, also showing the disconnected alert.

![Screenshot](screenshot.png)


In the `/script` directory there is a Python script that can be run on a dnsmasq server to display the current lease info in a similar way. This is completely separate from the web app.


## How & Why

This was an experiment in building a small app for my homelab using OpenCode and various mostly local LLMs. The basic features were converted to Python by Qwen3.6 (cloud, via OpenCode) from an earlier Node.js prototype built using glm-4.7 if I remember correctly. A few architectural changes and performance fixes were made after manual review and testing but all updates to code and container-related files (possibly with a few single-line exceptions) were done by LLMs. The same applies to this README, except for this text.

LLMs used: Mostly the Qwen family, 3.5/3.6 35B-A3B and Google Gemma-4 26B-A4B. Additional reviews are also provided occasionally by glm-4.7-flash and gpt-oss-20b.


## Requirements

Python3, tested and run on 3.12, 3.13 and 3.14. The code was built and tested on Linux, Debian 13 (x86_64) and Ubuntu 24.04 (aarch64).

The server uses about 10-20 MB memory and does no processing at all unless unless a client is actively requesting data via the web page. This does not cause noticeable load.

Any modern browser with Javascript enabled should work fine on the client side.

## Running

### Standalone

```bash
python src/server.py
```

Open http://localhost:8000

### Docker / Podman

Docker Compose V2.20+ required (for `pull_policy`).

```bash
docker compose up --build -d
```

Or build and run manually:

```bash
docker build -t dnsmasq-viewer .
docker run -d -p 8000:8000 \
  -e REBOOT_REQUIRED=/mnt/run/reboot-required \
  -v /var/lib/misc/dnsmasq.leases:/var/lib/misc/dnsmasq.leases:ro \
  -v /var/run:/mnt/run:ro \
  dnsmasq-viewer
```

### systemd

Copy the required files to their expected locations and enable the service:

```bash
sudo mkdir -p /opt/dnsmasq-viewer
sudo cp -r src/ public/ /opt/dnsmasq-viewer/
sudo cp dnsmasq-viewer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dnsmasq-viewer.service
```

The service runs with systemd's `DynamicUser` (random unprivileged user, no home directory) and a hardened sandbox (`ProtectSystem=strict`, `NoNewPrivileges=yes`, etc.). Adjust `WorkingDirectory` and `ExecStart` in the unit file if you install the app somewhere other than `/opt/dnsmasq-viewer`.

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Serves the web UI |
| `GET /leases` | Returns lease data as JSON |
| `GET /system-info` | Returns system metrics as JSON |
| `GET /status` | Returns `OK` and HTTP status 200 when running |

## Configuration

When using Docker Compose, you can also use a `.env` file in the project root to manage these variables. Copy `.env.example` and adjust as needed:

```bash
cp .env.example .env
```

| Environment variable | Description | Default |
|---------------------|-------------|---------|
| `HOST` | HTTP listen address | `0.0.0.0` (all addresses) |
| `PORT` | HTTP listen port | `8000` |
| `LEASEFILE` | Path to the dnsmasq lease file | `/var/lib/misc/dnsmasq.leases` |
| `HOSTNAME` | Override the system hostname | |
| `REBOOT_REQUIRED` | Path to the reboot-required marker file. Set to empty string to disable the check. | `/var/run/reboot-required` |
| `ALLOWED_NETWORKS` | Comma-separated list of allowed IPv4/IPv6 networks in CIDR notation. Connections from other IPs are rejected with `403 Forbidden`. | `192.168.0.0/16,127.0.0.1` |
| `DEBUG` | Enable detailed HTTP request logging to console | Empty (logging disabled) |

Example:

```bash
# Enable debug logging to see HTTP request details
DEBUG=1 python src/server.py

# Or in Docker
docker run -d -e DEBUG=1 -p 8000:8000 \
  -v /var/lib/misc/dnsmasq.leases:/var/lib/misc/dnsmasq.leases:ro \
  dnsmasq-viewer
```

## Known issues / Good-to-know

- DHCP client IDs not displayed since I am not using that in my setup.
- Network access control is enabled by default — only IPs in `192.168.0.0/16` or `127.0.0.1` can connect. Set `ALLOWED_NETWORKS` to customize, e.g. `10.0.0.0/8,172.16.0.0/12`. Use `0.0.0.0/0` to allow all connections (`::/0` for IPv6).
- The `reboot-required` file check is specific to Debian/Ubuntu-based Linux distributions with the `unattended-upgrades` package installed.
- There is no strict input validation on the lease file structure.
- By default, HTTP request logging is disabled to keep the console clean. Set the `DEBUG` environment variable to enable detailed request logging. When enabled, you may see garbled "Bad request" messages from clients that retry with HTTPS on the HTTP port — this is harmless and can be safely ignored.
