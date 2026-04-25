# DNSmasq Lease Viewer

A possibly just a bit over-engineered but lightweight web app that displays DHCP lease information from a dnsmasq server's lease file, along with basic system information (system load, memory usage, uptime, hostname). This is currently used to display DHCP leases handed out from a Raspberry Pi 3 running `dnsmasq` in a homelab.


## Features

- Parses the dnsmasq lease file and displays leases in a table, reverse sorted by lease expiry time which usually results in last lease on top
- Fields displayed: Lease expiry time, MAC address, IP address, hostname as seen by `dnsmasq`. The DHCP client ID field is returned by the server but ignored by the front end for now (I am not using it, my `dnsmasq` is running with `dhcp-ignore-clid`)
- Auto-refreshes every 5 seconds
- Shows some system info: lease count, CPU load, memory usage, uptime, hostname
- Displays "(reboot required)" next to the Uptime label when `/var/run/reboot-required` exists on the host
- Times and dates should be displayed using the client/browser's time zone conventions if correctly configured and requested from the browser
- Connection status banner (Hidden unless needed)
  - Alerts if the backend is offline
  - Alerts if lease file can not be read (permission denied/wrong path/corrupt file)
- Dark theme toggle
- Minimal dependencies — uses only Python stdlib
- Network access control — restricts access to specific IP ranges
- Deployment toolkit included (more info below)

This what it looks like, also showing the disconnected alert.

![Screenshot](screenshot.png)


## How & Why

This was an experiment in building small apps with OpenCode and various LLMs. Most basic features were converted to Python by Qwen3.6 from an earlier Node.js prototype built using glm-4.7 if I remember correctly. Some other LLMs have also given input on code quality, structure etc. and some manual reviews & minor tweaks to this README have also been done.

In the `/script` directory there is also a Python script that can be run on a dnsmasq server and that will display the current lease info in a similar way. This is completely separate from the web app. Run it via `watch` to see updates continuously.


## Requirements

Python3, tested and run on 3.12, 3.13 and 3.14. The code was built and tested on Linux, Debian 13 (x86_64) and Ubuntu 24.04 (aarch64).

It uses about 10-20 MB memory and very little CPU, a tiny bit more CPU when the lease table is updated if the web page is opened in a browser.

Any modern browser with Javascript enabled should work fine on the client side.

## Running

### Standalone

```bash
python src/server.py
```

Open http://localhost:8000

### Docker / Podman

```bash
docker compose up --build
```

Or build and run manually:

```bash
docker build -t dnsmasq-viewer-python .
docker run -d -p 8000:8000 \
  -v /var/lib/misc/dnsmasq.leases:/var/lib/misc/dnsmasq.leases:ro \
  dnsmasq-viewer-python
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
docker run -d -e DEBUG=1 -p 8080:8080 \
  -v /var/lib/misc/dnsmasq.leases:/var/lib/misc/dnsmasq.leases:ro \
  dnsmasq-viewer-python
```

## Known issues / Good-to-know

- DHCP client IDs not displayed since I am not using that in my setup.
- Network access control is enabled by default — only IPs in `192.168.0.0/16` or `127.0.0.1` can connect. Set `ALLOWED_NETWORKS` to customize, e.g. `10.0.0.0/8,172.16.0.0/12`. Use `0.0.0.0/0` to allow all connections.
- There is no strict input validation on the lease file structure.
- By default, HTTP request logging is disabled to keep the console clean. Set the `DEBUG` environment variable to enable detailed request logging. When enabled, you may see garbled "Bad request" messages from clients that retry with HTTPS on the HTTP port — this is harmless and can be safely ignored.
