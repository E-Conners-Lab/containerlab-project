#!/usr/bin/env python3
"""
Populate NetBox with E-University Lab data.

This script creates all devices, interfaces, IP addresses, and connections
in NetBox based on the lab topology.

Usage:
    python scripts/netbox_populate.py

Environment variables (set in .env file):
    NETBOX_URL - NetBox server URL
    NETBOX_TOKEN - NetBox API token
"""
import os
import pynetbox
import urllib3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Disable SSL warnings for lab environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETBOX_URL = os.environ.get("NETBOX_URL")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

if not NETBOX_URL or not NETBOX_TOKEN:
    raise ValueError("NETBOX_URL and NETBOX_TOKEN must be set in .env file")

# Lab data
SITE_NAME = "E-University Lab"

DEVICES = {
    # Core routers
    'core1': {'role': 'core', 'loopback': '10.255.1.1', 'mgmt': '192.168.68.200'},
    'core2': {'role': 'core', 'loopback': '10.255.1.2', 'mgmt': '192.168.68.202'},
    'core3': {'role': 'core', 'loopback': '10.255.1.3', 'mgmt': '192.168.68.203'},
    'core4': {'role': 'core', 'loopback': '10.255.1.4', 'mgmt': '192.168.68.204'},
    'core5': {'role': 'core', 'loopback': '10.255.1.5', 'mgmt': '192.168.68.205'},
    # Internet gateways
    'inet-gw1': {'role': 'gateway', 'loopback': '10.255.0.1', 'mgmt': '192.168.68.206'},
    'inet-gw2': {'role': 'gateway', 'loopback': '10.255.0.2', 'mgmt': '192.168.68.251'},
    # Main campus
    'main-agg1': {'role': 'aggregation', 'loopback': '10.255.10.1', 'mgmt': '192.168.68.208'},
    'main-edge1': {'role': 'edge', 'loopback': '10.255.10.2', 'mgmt': '192.168.68.209'},
    'main-edge2': {'role': 'edge', 'loopback': '10.255.10.3', 'mgmt': '192.168.68.210'},
    'main-asw1': {'role': 'access', 'loopback': '10.255.10.4', 'mgmt': '192.168.68.253'},
    # Medical campus
    'med-agg1': {'role': 'aggregation', 'loopback': '10.255.20.1', 'mgmt': '192.168.68.211'},
    'med-edge1': {'role': 'edge', 'loopback': '10.255.20.2', 'mgmt': '192.168.68.212'},
    'med-edge2': {'role': 'edge', 'loopback': '10.255.20.3', 'mgmt': '192.168.68.213'},
    'med-asw1': {'role': 'access', 'loopback': '10.255.20.4', 'mgmt': '192.168.68.252'},
    # Research campus
    'res-agg1': {'role': 'aggregation', 'loopback': '10.255.30.1', 'mgmt': '192.168.68.214'},
    'res-edge1': {'role': 'edge', 'loopback': '10.255.30.2', 'mgmt': '192.168.68.215'},
    'res-edge2': {'role': 'edge', 'loopback': '10.255.30.3', 'mgmt': '192.168.68.216'},
    'res-asw1': {'role': 'access', 'loopback': '10.255.30.4', 'mgmt': '192.168.68.254'},
}

# Point-to-point links: (device_a, intf_a, ip_a, device_b, intf_b, ip_b)
LINKS = [
    # Core ring
    ('core1', 'GigabitEthernet2', '10.0.0.0/31', 'core2', 'GigabitEthernet2', '10.0.0.1/31'),
    ('core2', 'GigabitEthernet3', '10.0.0.2/31', 'core3', 'GigabitEthernet2', '10.0.0.3/31'),
    ('core3', 'GigabitEthernet3', '10.0.0.4/31', 'core4', 'GigabitEthernet2', '10.0.0.5/31'),
    ('core4', 'GigabitEthernet3', '10.0.0.6/31', 'core5', 'GigabitEthernet2', '10.0.0.7/31'),
    ('core5', 'GigabitEthernet3', '10.0.0.8/31', 'core1', 'GigabitEthernet3', '10.0.0.9/31'),
    # Internet gateways
    ('core1', 'GigabitEthernet4', '10.0.0.10/31', 'inet-gw1', 'GigabitEthernet2', '10.0.0.11/31'),
    ('core2', 'GigabitEthernet4', '10.0.0.12/31', 'inet-gw2', 'GigabitEthernet2', '10.0.0.13/31'),
    # Main campus
    ('core1', 'GigabitEthernet5', '10.0.1.0/31', 'main-agg1', 'GigabitEthernet2', '10.0.1.1/31'),
    ('core2', 'GigabitEthernet5', '10.0.1.2/31', 'main-agg1', 'GigabitEthernet3', '10.0.1.3/31'),
    ('main-agg1', 'GigabitEthernet4', '10.0.1.4/31', 'main-edge1', 'GigabitEthernet2', '10.0.1.5/31'),
    ('main-agg1', 'GigabitEthernet5', '10.0.1.6/31', 'main-edge2', 'GigabitEthernet2', '10.0.1.7/31'),
    ('main-edge1', 'GigabitEthernet3', '10.0.1.8/31', 'main-edge2', 'GigabitEthernet3', '10.0.1.9/31'),
    # Medical campus
    ('core2', 'GigabitEthernet6', '10.0.2.0/31', 'med-agg1', 'GigabitEthernet2', '10.0.2.1/31'),
    ('core3', 'GigabitEthernet4', '10.0.2.2/31', 'med-agg1', 'GigabitEthernet3', '10.0.2.3/31'),
    ('med-agg1', 'GigabitEthernet4', '10.0.2.4/31', 'med-edge1', 'GigabitEthernet2', '10.0.2.5/31'),
    ('med-agg1', 'GigabitEthernet5', '10.0.2.6/31', 'med-edge2', 'GigabitEthernet2', '10.0.2.7/31'),
    ('med-edge1', 'GigabitEthernet3', '10.0.2.8/31', 'med-edge2', 'GigabitEthernet3', '10.0.2.9/31'),
    # Research campus
    ('core4', 'GigabitEthernet4', '10.0.3.0/31', 'res-agg1', 'GigabitEthernet2', '10.0.3.1/31'),
    ('core5', 'GigabitEthernet4', '10.0.3.2/31', 'res-agg1', 'GigabitEthernet3', '10.0.3.3/31'),
    ('res-agg1', 'GigabitEthernet4', '10.0.3.4/31', 'res-edge1', 'GigabitEthernet2', '10.0.3.5/31'),
    ('res-agg1', 'GigabitEthernet5', '10.0.3.6/31', 'res-edge2', 'GigabitEthernet2', '10.0.3.7/31'),
    ('res-edge1', 'GigabitEthernet3', '10.0.3.8/31', 'res-edge2', 'GigabitEthernet3', '10.0.3.9/31'),
    # Edge to ASW links
    ('main-edge1', 'GigabitEthernet4', '10.0.1.10/31', 'main-asw1', 'GigabitEthernet2', '10.0.1.11/31'),
    ('main-edge2', 'GigabitEthernet4', '10.0.1.12/31', 'main-asw1', 'GigabitEthernet3', '10.0.1.13/31'),
    ('med-edge1', 'GigabitEthernet4', '10.0.2.10/31', 'med-asw1', 'GigabitEthernet2', '10.0.2.11/31'),
    ('med-edge2', 'GigabitEthernet4', '10.0.2.12/31', 'med-asw1', 'GigabitEthernet3', '10.0.2.13/31'),
    ('res-edge1', 'GigabitEthernet4', '10.0.3.10/31', 'res-asw1', 'GigabitEthernet2', '10.0.3.11/31'),
    ('res-edge2', 'GigabitEthernet4', '10.0.3.12/31', 'res-asw1', 'GigabitEthernet3', '10.0.3.13/31'),
]


def get_or_create(nb_obj, search_params=None, **kwargs):
    """Get existing object or create new one."""
    if search_params is None:
        search_params = {k: v for k, v in kwargs.items() if k not in ['slug']}
    existing = list(nb_obj.filter(**search_params))
    if existing:
        return existing[0]
    return nb_obj.create(**kwargs)


def main():
    print("Connecting to NetBox...")
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    nb.http_session.verify = False

    # Create site
    print("\nCreating site...")
    site = get_or_create(nb.dcim.sites, name=SITE_NAME, slug='euniv-lab', status='active')
    print(f"  Site: {site.name}")

    # Create manufacturer
    print("\nCreating manufacturer...")
    manufacturer = get_or_create(nb.dcim.manufacturers, name='Cisco', slug='cisco')
    print(f"  Manufacturer: {manufacturer.name}")

    # Create device type
    print("\nCreating device type...")
    device_type = get_or_create(
        nb.dcim.device_types,
        search_params={'model': 'C8000v'},
        manufacturer=manufacturer.id,
        model='C8000v',
        slug='c8000v'
    )
    print(f"  Device type: {device_type.model}")

    # Create device roles
    print("\nCreating device roles...")
    roles = {}
    role_colors = {'core': 'ff0000', 'gateway': 'ff9800', 'aggregation': '2196f3', 'edge': '4caf50', 'access': '9c27b0'}
    for role_name, color in role_colors.items():
        roles[role_name] = get_or_create(
            nb.dcim.device_roles,
            name=role_name.capitalize(),
            slug=role_name,
            color=color
        )
        print(f"  Role: {roles[role_name].name}")

    # Create devices
    print("\nCreating devices...")
    devices = {}
    for device_name, info in DEVICES.items():
        device = get_or_create(
            nb.dcim.devices,
            search_params={'name': device_name},
            name=device_name,
            device_type=device_type.id,
            role=roles[info['role']].id,
            site=site.id,
            status='active'
        )
        devices[device_name] = device
        print(f"  Device: {device.name}")

        # Create Loopback0 interface
        lo0 = get_or_create(
            nb.dcim.interfaces,
            search_params={'device_id': device.id, 'name': 'Loopback0'},
            device=device.id,
            name='Loopback0',
            type='virtual'
        )

        # Assign loopback IP
        lo_ip = get_or_create(
            nb.ipam.ip_addresses,
            search_params={'address': f"{info['loopback']}/32"},
            address=f"{info['loopback']}/32",
            assigned_object_type='dcim.interface',
            assigned_object_id=lo0.id
        )

        # Create GigabitEthernet1 (management)
        gi1 = get_or_create(
            nb.dcim.interfaces,
            search_params={'device_id': device.id, 'name': 'GigabitEthernet1'},
            device=device.id,
            name='GigabitEthernet1',
            type='1000base-t'
        )

        # Assign management IP
        mgmt_ip = get_or_create(
            nb.ipam.ip_addresses,
            search_params={'address': f"{info['mgmt']}/24"},
            address=f"{info['mgmt']}/24",
            assigned_object_type='dcim.interface',
            assigned_object_id=gi1.id
        )

        # Set primary IP
        device.primary_ip4 = mgmt_ip.id
        device.save()

    # Create interfaces and links
    print("\nCreating interfaces and links...")
    for link in LINKS:
        dev_a, intf_a, ip_a, dev_b, intf_b, ip_b = link

        # Create interfaces
        int_a = get_or_create(
            nb.dcim.interfaces,
            search_params={'device_id': devices[dev_a].id, 'name': intf_a},
            device=devices[dev_a].id,
            name=intf_a,
            type='1000base-t'
        )
        int_b = get_or_create(
            nb.dcim.interfaces,
            search_params={'device_id': devices[dev_b].id, 'name': intf_b},
            device=devices[dev_b].id,
            name=intf_b,
            type='1000base-t'
        )

        # Assign IPs
        get_or_create(
            nb.ipam.ip_addresses,
            search_params={'address': ip_a},
            address=ip_a,
            assigned_object_type='dcim.interface',
            assigned_object_id=int_a.id
        )
        get_or_create(
            nb.ipam.ip_addresses,
            search_params={'address': ip_b},
            address=ip_b,
            assigned_object_type='dcim.interface',
            assigned_object_id=int_b.id
        )

        # Create cable
        existing_cables = list(nb.dcim.cables.filter(
            termination_a_type='dcim.interface',
            termination_a_id=int_a.id
        ))
        if not existing_cables:
            try:
                nb.dcim.cables.create(
                    a_terminations=[{'object_type': 'dcim.interface', 'object_id': int_a.id}],
                    b_terminations=[{'object_type': 'dcim.interface', 'object_id': int_b.id}],
                    status='connected'
                )
            except Exception as e:
                print(f"  Warning: Could not create cable {dev_a}:{intf_a} <-> {dev_b}:{intf_b}: {e}")

        print(f"  Link: {dev_a}:{intf_a} <-> {dev_b}:{intf_b}")

    print("\n" + "="*60)
    print("NetBox population complete!")
    print("="*60)
    print(f"\nAccess NetBox at: {NETBOX_URL}")
    print(f"Devices created: {len(DEVICES)}")
    print(f"Links created: {len(LINKS)}")


if __name__ == '__main__':
    main()
