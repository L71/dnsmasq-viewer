"""
A web server for viewing dnsmasq lease information and system metrics.

This server provides endpoints to:
- /leases - Get DNS lease information
- /system-info - Get system information (CPU, memory, uptime)
- /status - Simple health check endpoint
"""

import signal
import threading
import http.server
import socketserver
import json
import os
import platform
import socket
import logging
import ipaddress

LEASE_FILE = os.environ.get('LEASEFILE', '/var/lib/misc/dnsmasq.leases')
HOSTNAME_OVERRIDE = os.environ.get('HOSTNAME')
DEBUG = os.environ.get('DEBUG')
REBOOT_REQUIRED_FILE = os.environ.get('REBOOT_REQUIRED', '/var/run/reboot-required')
ALLOWED_NETWORKS = os.environ.get(
    'ALLOWED_NETWORKS', '192.168.0.0/16,127.0.0.1'
)

ALLOWED_NETWORK_OBJ = []
for net in ALLOWED_NETWORKS.split(','):
    net = net.strip()
    if '/' not in net:
        net += '/32'
    try:
        ALLOWED_NETWORK_OBJ.append(ipaddress.ip_network(net, strict=False))
    except ValueError:
        logging.warning(f'Skipping invalid network: {net}')

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.WARNING,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

def parse_leases():
    """
    Parse DNS lease entries from the lease file.

    Returns:
        list: Sorted list of lease dictionaries, sorted by expiry time (descending)
    """
    with open(LEASE_FILE, 'r', encoding='utf-8') as f:
        data = f.read().strip().split('\n')
    leases = []
    for line in data:
        parts = line.split()
        if len(parts) >= 5:
            expiry = int(parts[0])
            leases.append({
                'expiry': expiry,
                'mac': parts[1],
                'ip': parts[2],
                'hostname': parts[3] if parts[3] != '*' else '-',
                'id': parts[4] if parts[4] != '*' else '-'
            })
    leases.sort(key=lambda l: l['expiry'], reverse=True)
    return leases

def get_system_info():
    """
    Gather system information including CPU load, memory usage, and uptime.

    Returns:
        dict: Dictionary containing:
            - fileMtime: Lease file modification time (milliseconds since epoch)
            - cpuLoad: Current CPU load as string
            - memUsage: Memory usage percentage as string
            - platform: OS platform name
            - arch: CPU architecture
            - uptime: System uptime in seconds
            - hostname: System hostname
    """
    cpu_load = '0'
    uptime = 0
    reboot_required = os.path.exists(REBOOT_REQUIRED_FILE)
    if platform.system() == 'Linux':
        try:
            with open('/proc/loadavg', 'r') as f:
                cpu_load = f'{float(f.read().split()[0]):.2f}'
        except Exception:
            pass
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = int(float(f.read().split()[0]))
        except Exception:
            pass

    total_mem = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    used_mem = total_mem

    if platform.system() == 'Linux':
        cgroup = False
        try:
            with open('/sys/fs/cgroup/memory.max', 'r') as f:
                limit = f.read().strip()
                if limit != 'max':
                    total_mem = int(limit)
                    with open('/sys/fs/cgroup/memory.current', 'r') as f2:
                        used_mem = int(f2.read().strip())
                    cgroup = True
        except (FileNotFoundError, PermissionError, ValueError):
            pass

        if not cgroup:
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemAvailable:'):
                            available = int(line.split()[1]) * 1024
                            used_mem = total_mem - available
                            break
            except Exception:
                pass
    else:
        used_mem = total_mem - os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_AVPHYS_PAGES')
    mem_usage = f'{(used_mem / total_mem) * 100:.2f}' if total_mem > 0 else '0'

    file_mtime = 0
    try:
        file_mtime = os.path.getmtime(LEASE_FILE)
    except Exception:
        pass

    return {
        'fileMtime': file_mtime * 1000,
        'cpuLoad': cpu_load,
        'memUsage': mem_usage,
        'platform': platform.system(),
        'arch': platform.machine(),
        'uptime': uptime,
        'hostname': HOSTNAME_OVERRIDE or socket.gethostname(),
        'rebootRequired': reboot_required,
    }


def is_allowed(client_ip):
    """Check if the client IP is in the allowed networks."""
    try:
        addr = ipaddress.ip_address(client_ip)
        return any(addr in network for network in ALLOWED_NETWORK_OBJ)
    except ValueError:
        return False

class Handler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for the dnsmasq viewer server."""

    def __init__(self, *args, **kwargs):
        dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public'))
        super().__init__(*args, **kwargs, directory=dir_path)

    def do_GET(self):
        """
        Handle HTTP GET requests.

        Supported endpoints:
        - /leases: Get DNS lease information
        - /system-info: Get system metrics
        - /status: Health check
        - /, /index.html: Serve index page
        """
        if not is_allowed(self.client_address[0]):
            logging.warning(
                f"Denied connection from {self.client_address[0]}"
            )
            self.send_error_json(403, 'Access denied')
            return

        if self.path == '/leases':
            try:
                leases = parse_leases()
                self.send_json({'leases': leases})
            except Exception:
                self.send_error_json(500, 'Failed to read or parse leases')
        elif self.path == '/system-info':
            try:
                self.send_json(get_system_info())
            except Exception:
                self.send_error_json(500, 'Failed to get system info')
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path in ('/', '/index.html'):
            super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        """
        Send a JSON response.

        Args:
            data: Dictionary to serialize and send as JSON
        """
        body = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code, message):
        """
        Send a JSON error response without leaking internal details.

        Args:
            code: HTTP status code
            message: Generic error message for the client
        """
        body = json.dumps({'error': message}).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Log messages if DEBUG is enabled."""
        if DEBUG:
            logging.info(f"{self.address_string()}: {format % args}")

def signal_handler(signum, frame):
    """Handle SIGINT and SIGTERM with immediate shutdown."""
    threading.Thread(target=httpd.shutdown).start()


if __name__ == '__main__':
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8000))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        print(f'Serving at http://{HOST}:{PORT}')
        httpd.serve_forever()
