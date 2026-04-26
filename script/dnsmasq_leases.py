#!/usr/bin/env python3
"""Display dnsmasq lease data in a formatted table."""

import argparse
import datetime
import os
import sys


def parse_lease_file(filepath):
    """Parse the dnsmasq leases file and return a list of lease records."""
    leases = []

    stat = os.stat(filepath)
    file_mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            try:
                expiry_epoch = int(parts[0])
                mac = parts[1]
                ip = parts[2]
                hostname = parts[3]
            except ValueError:
                continue

            leases.append({
                'expiry_epoch': expiry_epoch,
                'mac': mac,
                'ip': ip,
                'hostname': hostname
            })

    return leases, file_mtime


def format_expiry(epoch):
    """Convert Unix epoch to human-readable local time format."""
    dt = datetime.datetime.fromtimestamp(epoch)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def truncate_hostname(hostname, max_width):
    """Truncate hostname if it exceeds the maximum width."""
    if len(hostname) > max_width:
        return hostname[:max_width - 3] + '...'
    return hostname


def print_table(leases, file_mtime=None, filepath=None):
    """Print the lease data in a formatted table."""
    if file_mtime and filepath:
        print(f"File {filepath}: modified {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    if not leases:
        print("No leases found.")
        return

    # Calculate column widths
    max_ip_len = max(len(l['ip']) for l in leases) + 2
    max_mac_len = max(len(l['mac']) for l in leases) + 2
    max_hostname_len = 20  # Fixed width for hostname

    # Print header
    print(f"{'Expiry':<22} {'MAC':<{max_mac_len}} {'IP':<{max_ip_len}} {'Hostname':<{max_hostname_len}}")
    print("-" * (22 + max_mac_len + max_ip_len + max_hostname_len))

    # Print data rows (sorted by expiry in reverse order)
    for lease in leases:
        expiry_str = format_expiry(lease['expiry_epoch'])
        hostname = truncate_hostname(lease['hostname'], max_hostname_len)
        print(f"{expiry_str:<22} {lease['mac']:<{max_mac_len}} {lease['ip']:<{max_ip_len}} {hostname:<{max_hostname_len}}")


def main():
    parser = argparse.ArgumentParser(description='Display dnsmasq lease data in a table')
    parser.add_argument('file', nargs='?', default='/var/lib/misc/dnsmasq.leases',
                        help='Path to the dnsmasq leases file (default: /var/lib/misc/dnsmasq.leases)')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    leases, file_mtime = parse_lease_file(args.file)
    leases.sort(key=lambda x: x['expiry_epoch'], reverse=True)
    print_table(leases, file_mtime, args.file)


if __name__ == '__main__':
    main()
