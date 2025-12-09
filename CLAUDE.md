# E-University ContainerLab MPLS Lab - Claude Context

## Current Status
- **Phase:** Phase 6 Complete - Ready for Phase 7
- **Lab Status:** All 19 routers healthy on clab-host
- **Phases Completed:** 1 (Core Ring OSPF), 2 (MPLS LDP), 3 (MP-BGP Route Reflectors), 4 (Internet Gateways), 5 (Main Campus), 6 (Medical Campus)
- **NetBox:** See .env file for URL and credentials

## Next Steps
1. Populate NetBox with lab data: `python scripts/netbox_populate.py`
2. Create Phase 7 tests and configs (Research Campus: res-agg1, res-edge1, res-edge2)

## Infrastructure
| Resource | Details |
|----------|---------|
| ContainerLab Host | See CLAB_HOST in .env |
| NetBox | See NETBOX_URL in .env |
| NetBox API Token | See NETBOX_TOKEN in .env |
| Router Image | vrnetlab/cisco_c8000v:17.13.01a |
| Router Credentials | See ROUTER_USERNAME/ROUTER_PASSWORD in .env |
| SSH Access | See CLAB_SSH_USER/CLAB_SSH_PASSWORD in .env |

**Note:** All credentials are stored in `.env` (not committed to git). Copy `.env.example` to `.env` and configure.

## Topology Overview
19 C8000v routers + 3 Alpine Linux hosts

```
                    [inet-gw1]     [inet-gw2]
                         |              |
                      (Gi4)          (Gi4)
                         |              |
    [core5]---(Gi3)---[core1]---(Gi2)---[core2]---(Gi3)---[core3]
       |                 |              |   |              |
    (Gi2)             (Gi5)          (Gi5) (Gi6)        (Gi4)
       |                 |              |   |              |
    [core4]----------[main-agg1]--------+   +--------[med-agg1]
       |                 |                              |
    (Gi4)             (Gi4,5)                       (Gi4,5)
       |                 |                              |
    [res-agg1]    [main-edge1,2]                [med-edge1,2]
       |
    (Gi4,5)
       |
    [res-edge1,2]
```

## IP Addressing

### Loopbacks (Router-IDs)
| Device | Loopback0 | Mgmt IP |
|--------|-----------|---------|
| core1 | 10.255.1.1 | 192.168.68.200 |
| core2 | 10.255.1.2 | 192.168.68.202 |
| core3 | 10.255.1.3 | 192.168.68.203 |
| core4 | 10.255.1.4 | 192.168.68.204 |
| core5 | 10.255.1.5 | 192.168.68.205 |
| inet-gw1 | 10.255.0.1 | 192.168.68.206 |
| inet-gw2 | 10.255.0.2 | 192.168.68.251 |
| main-agg1 | 10.255.10.1 | 192.168.68.208 |
| main-edge1 | 10.255.10.2 | 192.168.68.209 |
| main-edge2 | 10.255.10.3 | 192.168.68.210 |
| med-agg1 | 10.255.20.1 | 192.168.68.211 |
| med-edge1 | 10.255.20.2 | 192.168.68.212 |
| med-edge2 | 10.255.20.3 | 192.168.68.213 |
| res-agg1 | 10.255.30.1 | 192.168.68.214 |
| res-edge1 | 10.255.30.2 | 192.168.68.215 |
| res-edge2 | 10.255.30.3 | 192.168.68.216 |

### Point-to-Point Links (/31)

**Core Ring:**
| Link | Network | A-side | B-side |
|------|---------|--------|--------|
| core1-core2 | 10.0.0.0/31 | core1 Gi2 (.0) | core2 Gi2 (.1) |
| core2-core3 | 10.0.0.2/31 | core2 Gi3 (.2) | core3 Gi2 (.3) |
| core3-core4 | 10.0.0.4/31 | core3 Gi3 (.4) | core4 Gi2 (.5) |
| core4-core5 | 10.0.0.6/31 | core4 Gi3 (.6) | core5 Gi2 (.7) |
| core5-core1 | 10.0.0.8/31 | core5 Gi3 (.8) | core1 Gi3 (.9) |

**Internet Gateways:**
| Link | Network | A-side | B-side |
|------|---------|--------|--------|
| core1-inet-gw1 | 10.0.0.10/31 | core1 Gi4 (.10) | inet-gw1 Gi2 (.11) |
| core2-inet-gw2 | 10.0.0.12/31 | core2 Gi4 (.12) | inet-gw2 Gi2 (.13) |

**Main Campus (10.0.1.x):**
| Link | Network | A-side | B-side |
|------|---------|--------|--------|
| core1-main-agg1 | 10.0.1.0/31 | core1 Gi5 (.0) | main-agg1 Gi2 (.1) |
| core2-main-agg1 | 10.0.1.2/31 | core2 Gi5 (.2) | main-agg1 Gi3 (.3) |
| main-agg1-edge1 | 10.0.1.4/31 | main-agg1 Gi4 (.4) | main-edge1 Gi2 (.5) |
| main-agg1-edge2 | 10.0.1.6/31 | main-agg1 Gi5 (.6) | main-edge2 Gi2 (.7) |
| edge1-edge2 | 10.0.1.8/31 | main-edge1 Gi3 (.8) | main-edge2 Gi3 (.9) |

**Medical Campus (10.0.2.x):**
| Link | Network | A-side | B-side |
|------|---------|--------|--------|
| core2-med-agg1 | 10.0.2.0/31 | core2 Gi6 (.0) | med-agg1 Gi2 (.1) |
| core3-med-agg1 | 10.0.2.2/31 | core3 Gi4 (.2) | med-agg1 Gi3 (.3) |
| med-agg1-edge1 | 10.0.2.4/31 | med-agg1 Gi4 (.4) | med-edge1 Gi2 (.5) |
| med-agg1-edge2 | 10.0.2.6/31 | med-agg1 Gi5 (.6) | med-edge2 Gi2 (.7) |
| edge1-edge2 | 10.0.2.8/31 | med-edge1 Gi3 (.8) | med-edge2 Gi3 (.9) |

**Research Campus (10.0.3.x):**
| Link | Network | A-side | B-side |
|------|---------|--------|--------|
| core4-res-agg1 | 10.0.3.0/31 | core4 Gi4 (.0) | res-agg1 Gi2 (.1) |
| core5-res-agg1 | 10.0.3.2/31 | core5 Gi4 (.2) | res-agg1 Gi3 (.3) |
| res-agg1-edge1 | 10.0.3.4/31 | res-agg1 Gi4 (.4) | res-edge1 Gi2 (.5) |
| res-agg1-edge2 | 10.0.3.6/31 | res-agg1 Gi5 (.6) | res-edge2 Gi2 (.7) |
| edge1-edge2 | 10.0.3.8/31 | res-edge1 Gi3 (.8) | res-edge2 Gi3 (.9) |

## Implementation Phases

| Phase | Feature | Devices | Status |
|-------|---------|---------|--------|
| 1 | Core Ring OSPF | core1-5 | COMPLETE |
| 2 | MPLS LDP | core1-5 | COMPLETE |
| 3 | MP-BGP Route Reflectors | core1-5 (RR: 1,2,5) | COMPLETE |
| 4 | Internet Gateways | inet-gw1/2, core1/2 | COMPLETE |
| 5 | Main Campus | main-agg1, edge1/2 | COMPLETE |
| 6 | Medical Campus | med-agg1, edge1/2 | COMPLETE |
| 7 | Research Campus | res-agg1, edge1/2 | Pending |
| 8 | VRFs and L3VPN | PE routers | Pending |
| 9 | HSRP | edge pairs | Pending |

## BGP Design
- **AS:** 65001 (iBGP)
- **Route Reflectors:** core1, core2, core5
- **RR Clients:** core3, core4, inet-gw1/2, campus agg routers
- **Address Family:** VPNv4 unicast

## NetBox Integration (Source of Truth)

```
NetBox (IPAM/DCIM)
       ↓
   API Queries
       ↓
┌──────────────────────────────┐
│  netbox_generate_testbed.py  │ → testbed.yml
│  netbox_generate_configs.py  │ → configs/*.cfg
└──────────────────────────────┘
       ↓
   apply_configs.py → Routers
       ↓
   pytest (validate)
```

### NetBox Commands
```bash
# Generate testbed.yml from NetBox
python scripts/netbox_generate_testbed.py

# Generate phase configs from NetBox
python scripts/netbox_generate_configs.py --phase 1
python scripts/netbox_generate_configs.py --phase 1 --dry-run

# Populate NetBox with lab data (one-time)
python scripts/netbox_populate.py
```

## TDD Workflow
```bash
# 1. Create tests
vim tests/test_phaseX.py

# 2. Run tests (expect FAIL)
pytest tests/test_phaseX.py -v

# 3. Generate configs from NetBox (or create manually)
python scripts/netbox_generate_configs.py --phase X

# 4. Apply configs
python scripts/apply_configs.py --phase X

# 5. Run tests (expect PASS)
pytest tests/test_phaseX.py -v
```

## Quick Commands
```bash
# SSH to clab-host (use credentials from .env)
ssh $CLAB_SSH_USER@$CLAB_HOST

# Check router health
docker ps --format "table {{.Names}}\t{{.Status}}" | grep healthy

# Clear SSH keys (Mac) - update IPs as needed
for ip in 192.168.68.{200,202,203,204,205,206,208,209,210,211,212,213,214,215,216,251}; do ssh-keygen -R $ip; done

# Run all tests
pytest tests/ -v

# Apply specific phase
python scripts/apply_configs.py --phase 1

# Dry run (preview)
python scripts/apply_configs.py --phase 1 --dry-run
```
