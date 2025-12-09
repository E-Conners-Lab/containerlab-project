#!/usr/bin/env python3
"""
Generate device configurations from NetBox using Jinja2 templates.

This script queries NetBox for device/interface/IP data and renders
configuration templates for each phase.

Usage:
    python scripts/netbox_generate_configs.py --phase 1
    python scripts/netbox_generate_configs.py --phase 1 --device core1
    python scripts/netbox_generate_configs.py --phase 1 --dry-run

Environment variables (set in .env file):
    NETBOX_URL - NetBox server URL
    NETBOX_TOKEN - NetBox API token
"""
import argparse
import os
from pathlib import Path
import pynetbox
from jinja2 import Environment, FileSystemLoader
import urllib3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETBOX_URL = os.environ.get("NETBOX_URL")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

if not NETBOX_URL or not NETBOX_TOKEN:
    raise ValueError("NETBOX_URL and NETBOX_TOKEN must be set in .env file")

BGP_AS = 65001
ROUTE_REFLECTORS = ['core1', 'core2', 'core5']
RR_CLIENTS = ['core3', 'core4']

# Phase configuration
PHASE_CONFIG = {
    1: {
        'name': 'phase1_core_ospf',
        'template': 'phase1_ospf.j2',
        'devices': ['core1', 'core2', 'core3', 'core4', 'core5'],
        'description': 'Core Ring OSPF'
    },
    2: {
        'name': 'phase2_mpls_ldp',
        'template': 'phase2_mpls.j2',
        'devices': ['core1', 'core2', 'core3', 'core4', 'core5'],
        'description': 'MPLS LDP'
    },
    3: {
        'name': 'phase3_mpbgp_rr',
        'template': 'phase3_bgp.j2',
        'devices': ['core1', 'core2', 'core3', 'core4', 'core5'],
        'description': 'MP-BGP Route Reflectors'
    },
}


def get_device_data(nb, device_name):
    """Get all relevant data for a device from NetBox."""
    device = nb.dcim.devices.get(name=device_name)
    if not device:
        return None

    # Get all interfaces
    interfaces = list(nb.dcim.interfaces.filter(device_id=device.id))

    # Get loopback IP
    loopback_ip = None
    for intf in interfaces:
        if intf.name == 'Loopback0':
            ips = list(nb.ipam.ip_addresses.filter(interface_id=intf.id))
            if ips:
                loopback_ip = str(ips[0].address).split('/')[0]

    # Get interface IPs and connected devices
    interface_data = []
    for intf in interfaces:
        if intf.name.startswith('GigabitEthernet') and intf.name != 'GigabitEthernet1':
            ips = list(nb.ipam.ip_addresses.filter(interface_id=intf.id))
            if ips:
                ip_addr = str(ips[0].address)
                ip_only = ip_addr.split('/')[0]
                prefix_len = int(ip_addr.split('/')[1])
                # Convert prefix to netmask
                mask = '.'.join([str((0xffffffff << (32 - prefix_len) >> i) & 0xff)
                                for i in [24, 16, 8, 0]])

                # Get connected device via cable
                description = f"to {intf.connected_endpoints[0].device.name}" if intf.connected_endpoints else ""

                interface_data.append({
                    'name': intf.name,
                    'ip': ip_only,
                    'mask': mask,
                    'prefix': ip_addr,
                    'description': description
                })

    return {
        'device': device,
        'loopback_ip': loopback_ip,
        'interfaces': interface_data
    }


def get_bgp_neighbors(device_name, all_devices):
    """Determine BGP neighbors based on RR topology."""
    neighbors = []

    if device_name in ROUTE_REFLECTORS:
        # RRs peer with all other routers
        for other in all_devices:
            if other != device_name:
                is_client = other in RR_CLIENTS
                neighbors.append({
                    'ip': all_devices[other],
                    'description': f"{other}{'-RR-client' if is_client else ''}",
                    'is_client': is_client
                })
    else:
        # Clients only peer with RRs
        for rr in ROUTE_REFLECTORS:
            neighbors.append({
                'ip': all_devices[rr],
                'description': f"{rr}-RR",
                'is_client': False
            })

    return neighbors


def generate_phase_configs(nb, phase, device_filter=None, dry_run=False):
    """Generate configurations for a phase."""
    phase_info = PHASE_CONFIG.get(phase)
    if not phase_info:
        print(f"Error: Unknown phase {phase}")
        return

    print(f"\n{'='*60}")
    print(f"Phase {phase}: {phase_info['description']}")
    print(f"{'='*60}\n")

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template(phase_info['template'])

    # Output directory
    output_dir = Path(f"configs/{phase_info['name']}")
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Get all device loopbacks for BGP neighbor calculation
    all_loopbacks = {}
    for device_name in phase_info['devices']:
        data = get_device_data(nb, device_name)
        if data:
            all_loopbacks[device_name] = data['loopback_ip']

    # Generate configs
    devices_to_process = [device_filter] if device_filter else phase_info['devices']

    for device_name in devices_to_process:
        if device_name not in phase_info['devices']:
            print(f"Warning: {device_name} not in phase {phase} device list")
            continue

        print(f"[{device_name}]")
        data = get_device_data(nb, device_name)
        if not data:
            print(f"  Error: Device not found in NetBox")
            continue

        # Prepare template context
        context = {
            'device': data['device'],
            'loopback_ip': data['loopback_ip'],
        }

        if phase == 1:
            # OSPF - need interfaces with IPs
            context['ospf_interfaces'] = data['interfaces']
        elif phase == 2:
            # MPLS - same interfaces as OSPF
            context['mpls_interfaces'] = data['interfaces']
        elif phase == 3:
            # BGP - need neighbor info
            context['bgp_as'] = BGP_AS
            context['is_route_reflector'] = device_name in ROUTE_REFLECTORS
            context['bgp_neighbors'] = get_bgp_neighbors(device_name, all_loopbacks)

        # Render template
        config = template.render(**context)

        if dry_run:
            print(f"  --- Config Preview ---")
            for line in config.split('\n')[:15]:
                print(f"  {line}")
            print(f"  ... (truncated)")
        else:
            output_file = output_dir / f"{device_name}.cfg"
            with open(output_file, 'w') as f:
                f.write(config)
            print(f"  Written: {output_file}")

    print(f"\n{'='*60}")
    if dry_run:
        print("DRY RUN - No files written")
    else:
        print(f"Configs written to: configs/{phase_info['name']}/")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Generate configs from NetBox')
    parser.add_argument('--phase', '-p', type=int, required=True, help='Phase number (1-3)')
    parser.add_argument('--device', '-d', type=str, help='Specific device (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing files')
    args = parser.parse_args()

    print(f"Connecting to NetBox at {NETBOX_URL}...")
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    nb.http_session.verify = False

    generate_phase_configs(nb, args.phase, args.device, args.dry_run)


if __name__ == '__main__':
    main()
