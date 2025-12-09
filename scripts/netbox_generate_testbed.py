#!/usr/bin/env python3
"""
Generate pyATS testbed.yml from NetBox.

This script queries NetBox and generates a pyATS-compatible testbed file.

Usage:
    python scripts/netbox_generate_testbed.py
    python scripts/netbox_generate_testbed.py --output custom_testbed.yml

Environment variables (set in .env file):
    NETBOX_URL - NetBox server URL
    NETBOX_TOKEN - NetBox API token
    ROUTER_USERNAME - Router login username
    ROUTER_PASSWORD - Router login password
"""
import argparse
import os
import pynetbox
import yaml
import urllib3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETBOX_URL = os.environ.get("NETBOX_URL")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")
ROUTER_USERNAME = os.environ.get("ROUTER_USERNAME", "admin")
ROUTER_PASSWORD = os.environ.get("ROUTER_PASSWORD", "admin")

if not NETBOX_URL or not NETBOX_TOKEN:
    raise ValueError("NETBOX_URL and NETBOX_TOKEN must be set in .env file")


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
                    'username': ROUTER_USERNAME,
                    'password': ROUTER_PASSWORD
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
