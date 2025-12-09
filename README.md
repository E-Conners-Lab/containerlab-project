# E-University MPLS Lab

A test-driven network automation project for deploying an enterprise MPLS/VPN network using ContainerLab and Cisco C8000v routers.

## Overview

This project implements a multi-campus university network with:
- 5-node MPLS core ring
- 2 internet gateway routers
- 3 campus networks (Main, Medical, Research)
- L3VPN services with HSRP redundancy

## Architecture

```
                [Internet]
                    |
            [inet-gw1] [inet-gw2]
                 \       /
                  \     /
    [core5]----[core1]----[core2]----[core3]
       |           |          |          |
       |        [Main]     [Main]    [Medical]
       |        Campus     Campus     Campus
       |
    [core4]----[Research Campus]
```

## Prerequisites

- Python 3.10+
- Access to ContainerLab host (192.168.68.53)
- SSH connectivity to lab devices

## Installation

```bash
# Clone repository
git clone <repo-url>
cd containerlab-project

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
containerlab-project/
├── CLAUDE.md                  # Detailed topology and IP addressing
├── README.md                  # This file
├── testbed.yml                # pyATS device inventory
├── pytest.ini                 # pytest configuration
├── requirements.txt           # Python dependencies
├── topology.html              # Visual topology diagram
├── tests/
│   ├── test_phase1_core_ospf.py
│   ├── test_phase2_mpls_ldp.py
│   ├── test_phase3_mpbgp_rr.py
│   ├── test_phase4_inet_gw.py
│   ├── test_phase5_main_campus.py
│   ├── test_phase6_med_campus.py
│   ├── test_phase7_res_campus.py
│   └── test_phase8_l3vpn.py
├── configs/
│   ├── phase1_core_ospf/
│   ├── phase2_mpls_ldp/
│   ├── phase3_mpbgp_rr/
│   ├── phase4_inet_gw/
│   ├── phase5_main_campus/
│   ├── phase6_medical_campus/
│   ├── phase7_research_campus/
│   └── phase8_vrfs_l3vpn/
├── templates/                 # Jinja2 config templates
│   ├── phase1_ospf.j2
│   ├── phase2_mpls.j2
│   └── phase3_bgp.j2
├── scripts/
│   ├── apply_configs.py
│   ├── netbox_populate.py     # Populate NetBox with lab data
│   ├── netbox_generate_testbed.py
│   └── netbox_generate_configs.py
└── netbox/
    ├── docker-compose.yml     # NetBox deployment
    ├── setup.sh
    └── env/
```

## Usage

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific phase
pytest tests/test_phase1_core_ospf.py -v
```

### Applying Configurations

```bash
# Apply phase 1 configs
python scripts/apply_configs.py --phase 1

# Preview configs without applying
python scripts/apply_configs.py --phase 1 --dry-run

# Apply to specific device
python scripts/apply_configs.py --phase 1 --device core1
```

## Implementation Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Core Ring OSPF | Complete |
| 2 | MPLS LDP | Complete |
| 3 | MP-BGP Route Reflectors | Complete |
| 4 | Internet Gateways | Complete |
| 5 | Main Campus | Complete |
| 6 | Medical Campus | Complete |
| 7 | Research Campus | Complete |
| 8 | VRFs and L3VPN | Complete |
| 9 | HSRP | Pending |

## Test-Driven Development

This project follows TDD methodology:

1. **Write tests first** - Define expected behavior
2. **Run tests (RED)** - Confirm tests fail
3. **Write configs** - Implement the feature
4. **Apply configs** - Push to devices
5. **Run tests (GREEN)** - Verify implementation

## Technologies

- **ContainerLab** - Network topology orchestration
- **Cisco C8000v** - Virtual routers (IOS-XE 17.13)
- **pyATS/Genie** - Network testing framework
- **pytest** - Test runner
- **Netmiko** - Device configuration
- **NetBox** - IPAM/DCIM Source of Truth
- **Jinja2** - Configuration templating

## Credentials Setup

Credentials are managed via environment variables. Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

See `.env.example` for required variables.

## NetBox Integration

NetBox serves as the Source of Truth for this lab.

```bash
# Populate NetBox with lab data (one-time)
python scripts/netbox_populate.py

# Generate testbed.yml from NetBox
python scripts/netbox_generate_testbed.py

# Generate phase configs from NetBox
python scripts/netbox_generate_configs.py --phase 1
```

## License

MIT
