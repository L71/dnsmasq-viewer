# dnsmasq Leases Viewer

A Python script to display dnsmasq DHCP lease data in a formatted table.

Run it via `watch` to see updates continuously.

## Features

- Parses dnsmasq lease files (space-separated format)
- Converts Unix epoch timestamps to human-readable local time
- Displays fixed-width columns for MAC address, IP address, and hostname
- Sorts leases by expiry time in reverse order
- Shows lease file modification time and path

## Usage

```bash
./dnsmasq_leases.py [file]
```

### Arguments

- `file` (optional): Path to the dnsmasq leases file
  - Default: `/var/lib/misc/dnsmasq.leases`

### Examples

```bash
# Use default path
./dnsmasq_leases.py

# Specify custom path
./dnsmasq_leases.py /etc/dnsmasq.leases
./dnsmasq_leases.py ./dnsmasq.leases
```

## Output Format

The script outputs a table with the following columns:

1. **Expiry** - DHCP lease expiry time (Unix epoch converted to YYYY-MM-DD HH:MM:SS)
2. **MAC** - Client MAC address
3. **IP** - Assigned IP address
4. **Hostname** - Client hostname

## Example Output

```
File dnsmasq.leases: modified 2026-03-27 17:47:34
Expiry                 MAC                 IP               Hostname
-----------------------------------------------------------------------------
2026-03-05 23:03:47    bc:24:11:08:39:24   192.168.0.215    some-computer
2026-03-05 23:03:04    14:98:77:81:05:c4   192.168.10.150   another-computer
...
```
