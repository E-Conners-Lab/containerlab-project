"""
Phase 7: Research Campus Tests
Tests OSPF, MPLS LDP, and MP-BGP configuration for res-agg1, res-edge1, res-edge2

Research Campus links (10.0.3.x):
- core4 Gi4 (10.0.3.0) <-> res-agg1 Gi2 (10.0.3.1)
- core5 Gi4 (10.0.3.2) <-> res-agg1 Gi3 (10.0.3.3)
- res-agg1 Gi4 (10.0.3.4) <-> res-edge1 Gi2 (10.0.3.5)
- res-agg1 Gi5 (10.0.3.6) <-> res-edge2 Gi2 (10.0.3.7)
- res-edge1 Gi3 (10.0.3.8) <-> res-edge2 Gi3 (10.0.3.9)

res-agg1 is a BGP RR client peering with core1, core2, core5
"""
import pytest
from genie.testbed import load

RES_CAMPUS_ROUTERS = ['res-agg1', 'res-edge1', 'res-edge2']
CORE_ROUTERS_PHASE7 = ['core4', 'core5']
ALL_PHASE7_ROUTERS = RES_CAMPUS_ROUTERS + CORE_ROUTERS_PHASE7

BGP_AS = 65001
ROUTE_REFLECTORS = ['10.255.1.1', '10.255.1.2', '10.255.1.5']  # core1, core2, core5

LOOPBACKS = {
    'res-agg1': '10.255.30.1',
    'res-edge1': '10.255.30.2',
    'res-edge2': '10.255.30.3',
    'core4': '10.255.1.4',
    'core5': '10.255.1.5',
}

# Point-to-point links for research campus
P2P_LINKS = {
    'res-agg1': {
        'Gi2': {'ip': '10.0.3.1', 'peer': 'core4', 'peer_ip': '10.0.3.0'},
        'Gi3': {'ip': '10.0.3.3', 'peer': 'core5', 'peer_ip': '10.0.3.2'},
        'Gi4': {'ip': '10.0.3.4', 'peer': 'res-edge1', 'peer_ip': '10.0.3.5'},
        'Gi5': {'ip': '10.0.3.6', 'peer': 'res-edge2', 'peer_ip': '10.0.3.7'},
    },
    'res-edge1': {
        'Gi2': {'ip': '10.0.3.5', 'peer': 'res-agg1', 'peer_ip': '10.0.3.4'},
        'Gi3': {'ip': '10.0.3.8', 'peer': 'res-edge2', 'peer_ip': '10.0.3.9'},
    },
    'res-edge2': {
        'Gi2': {'ip': '10.0.3.7', 'peer': 'res-agg1', 'peer_ip': '10.0.3.6'},
        'Gi3': {'ip': '10.0.3.9', 'peer': 'res-edge1', 'peer_ip': '10.0.3.8'},
    },
}

# Core router links to research campus
CORE_LINKS = {
    'core4': {'interface': 'GigabitEthernet4', 'ip': '10.0.3.0', 'peer': 'res-agg1'},
    'core5': {'interface': 'GigabitEthernet4', 'ip': '10.0.3.2', 'peer': 'res-agg1'},
}


@pytest.fixture(scope='module')
def testbed():
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    devices = {}
    for name in ALL_PHASE7_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    yield devices
    for device in devices.values():
        device.disconnect()


class TestResCampusInterfaces:
    """Test research campus interface configuration."""

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_loopback0_configured(self, connected_devices, router):
        """Verify Loopback0 is configured with correct IP."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        expected_ip = LOOPBACKS[router]
        assert f'ip address {expected_ip} 255.255.255.255' in output, \
            f"{router}: Loopback0 should have IP {expected_ip}"

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_interfaces_configured(self, connected_devices, router):
        """Verify P2P interfaces are configured with correct IPs."""
        device = connected_devices[router]

        for intf, link_info in P2P_LINKS[router].items():
            output = device.execute(f'show running-config interface GigabitEthernet{intf[-1]}')
            assert f"ip address {link_info['ip']} 255.255.255.254" in output, \
                f"{router}: {intf} should have IP {link_info['ip']}"


class TestResCampusOSPF:
    """Test OSPF configuration on research campus routers."""

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_ospf_process_running(self, connected_devices, router):
        """Verify OSPF process 1 is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        assert 'router ospf 1' in output, \
            f"{router}: OSPF process 1 not configured"

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_ospf_router_id(self, connected_devices, router):
        """Verify OSPF router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output, \
            f"{router}: OSPF router-id should be {expected_rid}"

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_loopback_in_ospf(self, connected_devices, router):
        """Verify Loopback0 is advertised in OSPF."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        assert 'ip ospf 1 area 0' in output, \
            f"{router}: Loopback0 not in OSPF area 0"

    def test_res_agg1_ospf_neighbors(self, connected_devices):
        """Verify res-agg1 has OSPF neighbors with core4, core5, edge1, edge2."""
        device = connected_devices['res-agg1']
        output = device.execute('show ip ospf neighbor')

        # Should have 4 neighbors: core4, core5, res-edge1, res-edge2
        expected_neighbors = [
            LOOPBACKS['core4'],
            LOOPBACKS['core5'],
            LOOPBACKS['res-edge1'],
            LOOPBACKS['res-edge2'],
        ]
        for neighbor in expected_neighbors:
            assert neighbor in output, \
                f"res-agg1: OSPF neighbor {neighbor} not found"

    @pytest.mark.parametrize('router', ['res-edge1', 'res-edge2'])
    def test_edge_ospf_neighbors(self, connected_devices, router):
        """Verify edge routers have OSPF neighbors."""
        device = connected_devices[router]
        output = device.execute('show ip ospf neighbor')

        # Each edge should have res-agg1 and the other edge as neighbors
        assert LOOPBACKS['res-agg1'] in output, \
            f"{router}: OSPF neighbor res-agg1 not found"


class TestCoreToResCampusLinks:
    """Test core router links to research campus."""

    def test_core4_res_agg1_link(self, connected_devices):
        """Verify core4 Gi4 is configured for res-agg1 link."""
        device = connected_devices['core4']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'ip address 10.0.3.0 255.255.255.254' in output, \
            "core4: Gi4 should have IP 10.0.3.0/31 for res-agg1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core4: Gi4 should be in OSPF area 0"

    def test_core5_res_agg1_link(self, connected_devices):
        """Verify core5 Gi4 is configured for res-agg1 link."""
        device = connected_devices['core5']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'ip address 10.0.3.2 255.255.255.254' in output, \
            "core5: Gi4 should have IP 10.0.3.2/31 for res-agg1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core5: Gi4 should be in OSPF area 0"


class TestResCampusMPLS:
    """Test MPLS LDP configuration on research campus routers."""

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_mpls_ldp_configured(self, connected_devices, router):
        """Verify MPLS LDP router-id is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section mpls ldp')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output or 'mpls ldp router-id Loopback0' in output, \
            f"{router}: MPLS LDP router-id not configured"

    @pytest.mark.parametrize('router', RES_CAMPUS_ROUTERS)
    def test_mpls_on_interfaces(self, connected_devices, router):
        """Verify MPLS is enabled on P2P interfaces."""
        device = connected_devices[router]

        for intf in P2P_LINKS[router].keys():
            output = device.execute(f'show running-config interface GigabitEthernet{intf[-1]}')
            assert 'mpls ip' in output, \
                f"{router}: MPLS not enabled on {intf}"

    def test_res_agg1_ldp_neighbors(self, connected_devices):
        """Verify res-agg1 has LDP neighbors."""
        device = connected_devices['res-agg1']
        output = device.execute('show mpls ldp neighbor')

        # Should have LDP neighbors with core4 and core5
        assert LOOPBACKS['core4'] in output, \
            "res-agg1: LDP neighbor core4 not found"
        assert LOOPBACKS['core5'] in output, \
            "res-agg1: LDP neighbor core5 not found"


class TestCoreToResCampusMPLS:
    """Test MPLS is enabled on core links to research campus."""

    def test_core4_gi4_mpls(self, connected_devices):
        """Verify MPLS enabled on core4 Gi4."""
        device = connected_devices['core4']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'mpls ip' in output, \
            "core4: MPLS not enabled on Gi4 (res-agg1 link)"

    def test_core5_gi4_mpls(self, connected_devices):
        """Verify MPLS enabled on core5 Gi4."""
        device = connected_devices['core5']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'mpls ip' in output, \
            "core5: MPLS not enabled on Gi4 (res-agg1 link)"


class TestResAgg1BGP:
    """Test MP-BGP configuration on res-agg1 (PE router)."""

    def test_bgp_process_configured(self, connected_devices):
        """Verify BGP process is configured on res-agg1."""
        device = connected_devices['res-agg1']
        output = device.execute('show running-config | section router bgp')

        assert f'router bgp {BGP_AS}' in output, \
            f"res-agg1: BGP AS {BGP_AS} not configured"

    def test_bgp_router_id(self, connected_devices):
        """Verify BGP router-id is set to loopback address."""
        device = connected_devices['res-agg1']
        output = device.execute('show running-config | section router bgp')

        expected_rid = LOOPBACKS['res-agg1']
        assert f'bgp router-id {expected_rid}' in output, \
            f"res-agg1: BGP router-id should be {expected_rid}"

    def test_bgp_peers_with_rrs(self, connected_devices):
        """Verify res-agg1 peers with all route reflectors."""
        device = connected_devices['res-agg1']
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} remote-as {BGP_AS}' in output, \
                f"res-agg1: Not configured to peer with RR {rr_ip}"

    def test_vpnv4_configured(self, connected_devices):
        """Verify VPNv4 address family is configured."""
        device = connected_devices['res-agg1']
        output = device.execute('show running-config | section router bgp')

        assert 'address-family vpnv4' in output, \
            "res-agg1: VPNv4 address family not configured"

    def test_vpnv4_neighbors_activated(self, connected_devices):
        """Verify RR neighbors are activated under VPNv4."""
        device = connected_devices['res-agg1']
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} activate' in output, \
                f"res-agg1: Neighbor {rr_ip} not activated under VPNv4"


class TestRRClientConfig:
    """Test that RRs have res-agg1 as client."""

    def test_core5_has_res_agg1_client(self, connected_devices):
        """Verify core5 has res-agg1 as RR client."""
        device = connected_devices['core5']
        output = device.execute('show running-config | section router bgp')

        agg_ip = LOOPBACKS['res-agg1']
        assert f'neighbor {agg_ip} route-reflector-client' in output, \
            f"core5: res-agg1 ({agg_ip}) not configured as RR client"


class TestBGPSessionState:
    """Test actual BGP session states."""

    def test_res_agg1_bgp_sessions_established(self, connected_devices):
        """Verify res-agg1 BGP sessions are established with RRs."""
        device = connected_devices['res-agg1']
        output = device.execute('show bgp vpnv4 unicast all summary')

        for rr_ip in ROUTE_REFLECTORS:
            assert rr_ip in output, \
                f"res-agg1: BGP neighbor {rr_ip} not in summary"
            # Check neighbor line doesn't show Idle/Active
            for line in output.split('\n'):
                if rr_ip in line:
                    assert 'Idle' not in line and 'Active' not in line, \
                        f"res-agg1: BGP session with {rr_ip} not established"
