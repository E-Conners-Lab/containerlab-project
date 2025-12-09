#!/usr/bin/env python3
"""
Apply configuration files to network devices for a specific phase.

Usage:
    python scripts/apply_configs.py --phase 1
    python scripts/apply_configs.py --phase 1 --device core1
"""
import argparse
import os
import sys
from pathlib import Path
from genie.testbed import load

# Phase to directory mapping
PHASE_DIRS = {
    1: 'phase1_core_ospf',
    2: 'phase2_mpls_ldp',
    3: 'phase3_mpbgp_rr',
    4: 'phase4_inet_gw',
    5: 'phase5_main_campus',
    6: 'phase6_medical_campus',
    7: 'phase7_research_campus',
    8: 'phase8_vrfs_l3vpn',
    9: 'phase9_hsrp',
}


def get_config_files(phase: int, device: str = None) -> dict:
    """Get config files for a phase, optionally filtered by device."""
    phase_dir = PHASE_DIRS.get(phase)
    if not phase_dir:
        print(f"Error: Unknown phase {phase}")
        sys.exit(1)

    config_path = Path('configs') / phase_dir
    if not config_path.exists():
        print(f"Error: Config directory {config_path} does not exist")
        sys.exit(1)

    configs = {}
    for cfg_file in config_path.glob('*.cfg'):
        device_name = cfg_file.stem
        if device and device_name != device:
            continue
        configs[device_name] = cfg_file.read_text()

    return configs


def apply_config(device, config: str, device_name: str) -> bool:
    """Apply configuration to a device."""
    try:
        print(f"  Connecting to {device_name}...")
        device.connect(log_stdout=False)

        print(f"  Applying configuration...")
        device.configure(config)

        print(f"  Saving configuration...")
        device.execute('write memory')

        device.disconnect()
        return True

    except Exception as e:
        print(f"  Error: {e}")
        try:
            device.disconnect()
        except:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description='Apply phase configurations to devices')
    parser.add_argument('--phase', '-p', type=int, required=True,
                        help='Phase number (1-9)')
    parser.add_argument('--device', '-d', type=str,
                        help='Specific device to configure (optional)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be configured without applying')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Phase {args.phase}: {PHASE_DIRS.get(args.phase, 'Unknown')}")
    print(f"{'='*60}\n")

    # Load testbed
    testbed = load('testbed.yml')

    # Get configs for this phase
    configs = get_config_files(args.phase, args.device)

    if not configs:
        print("No configuration files found")
        sys.exit(1)

    print(f"Found {len(configs)} configuration file(s):\n")
    for device_name in sorted(configs.keys()):
        print(f"  - {device_name}.cfg")
    print()

    if args.dry_run:
        print("DRY RUN - Configurations that would be applied:\n")
        for device_name, config in sorted(configs.items()):
            print(f"{'='*40}")
            print(f"Device: {device_name}")
            print(f"{'='*40}")
            print(config)
            print()
        return

    # Apply configurations
    success = 0
    failed = 0

    for device_name, config in sorted(configs.items()):
        print(f"\n[{device_name}]")

        if device_name not in testbed.devices:
            print(f"  Warning: Device {device_name} not in testbed, skipping")
            failed += 1
            continue

        device = testbed.devices[device_name]
        if apply_config(device, config, device_name):
            print(f"  Success!")
            success += 1
        else:
            print(f"  Failed!")
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary: {success} succeeded, {failed} failed")
    print(f"{'='*60}\n")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
