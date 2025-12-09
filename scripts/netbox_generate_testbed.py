#!/usr/bin/env python3
"""
Generate pyATS testbed.yml from NetBox.

This script queries NetBox and generates a pyATS-compatible testbed file.

Usage:
    python scripts/netbox_generate_testbed.py
    python scripts/netbox_generate_testbed.py --output custom_testbed.yml
"""
import argparse
import pynetbox
import yaml
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETBOX_URL = "http://192.168.68.53:8000"
NETBOX_TOKEN = "0123456789abcdef0123456789abcdef01234567"


def get_loopback_ip(device, nb):
    """Get Loopback0 IP for a device."""
    interfaces = nb.dcim.interfaces.filter(device_id=device.id, name='Loopback0')
    for intf in interfaces:
        ips = nb.ipam.ip_addresses.filter(interface_id=intf.id)
        for ip in ips:
            return str(ip.address).split('/')[0]
    return None


def main():
    parser = argparse.ArgumentParser(description='Generate testbed.yml from NetBox')
    parser.add_argument('--output', '-o', default='testbed.yml', help='Output file')
    args = parser.parse_args()

    print(f"Connecting to NetBox at {NETBOX_URL}...")
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    nb.http_session.verify = False

    # Get all devices from E-University Lab site
    site = nb.dcim.sites.get(slug='euniv-lab')
    if not site:
        print("Error: Site 'euniv-lab' not found in NetBox")
        return

    devices = nb.dcim.devices.filter(site_id=site.id)

    testbed = {
        'testbed': {
            'name': 'E-University MPLS Lab (from NetBox)',
            'credentials': {
                'default': {
                    'username': 'admin',
                    'password': 'admin'
                }
            }
        },
        'devices': {}
    }

    print(f"\nGenerating testbed for site: {site.name}")
    print("-" * 50)

    for device in devices:
        if not device.primary_ip4:
            print(f"  Skipping {device.name} - no primary IP")
            continue

        mgmt_ip = str(device.primary_ip4.address).split('/')[0]
        loopback = get_loopback_ip(device, nb)

        testbed['devices'][device.name] = {
            'os': 'iosxe',
            'type': 'router',
            'connections': {
                'cli': {
                    'protocol': 'ssh',
                    'ip': mgmt_ip,
                    'port': 22
                }
            }
        }

        if loopback:
            testbed['devices'][device.name]['custom'] = {'loopback0': loopback}

        print(f"  {device.name}: {mgmt_ip} (Lo0: {loopback})")

    # Write testbed file
    with open(args.output, 'w') as f:
        yaml.dump(testbed, f, default_flow_style=False, sort_keys=False)

    print("-" * 50)
    print(f"\nTestbed written to: {args.output}")
    print(f"Devices: {len(testbed['devices'])}")


if __name__ == '__main__':
    main()
