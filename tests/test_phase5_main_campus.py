"""
Phase 5: Main Campus Tests
Tests OSPF, MPLS LDP, and MP-BGP configuration for main-agg1, main-edge1, main-edge2

Main Campus links (10.0.1.x):
- core1 Gi5 (10.0.1.0) <-> main-agg1 Gi2 (10.0.1.1)
- core2 Gi5 (10.0.1.2) <-> main-agg1 Gi3 (10.0.1.3)
- main-agg1 Gi4 (10.0.1.4) <-> main-edge1 Gi2 (10.0.1.5)
- main-agg1 Gi5 (10.0.1.6) <-> main-edge2 Gi2 (10.0.1.7)
- main-edge1 Gi3 (10.0.1.8) <-> main-edge2 Gi3 (10.0.1.9)

main-agg1 is a BGP RR client peering with core1, core2, core5
"""
import pytest
from genie.testbed import load

MAIN_CAMPUS_ROUTERS = ['main-agg1', 'main-edge1', 'main-edge2']
CORE_ROUTERS_PHASE5 = ['core1', 'core2']
ALL_PHASE5_ROUTERS = MAIN_CAMPUS_ROUTERS + CORE_ROUTERS_PHASE5

BGP_AS = 65001
ROUTE_REFLECTORS = ['10.255.1.1', '10.255.1.2', '10.255.1.5']  # core1, core2, core5

LOOPBACKS = {
    'main-agg1': '10.255.10.1',
    'main-edge1': '10.255.10.2',
    'main-edge2': '10.255.10.3',
    'core1': '10.255.1.1',
    'core2': '10.255.1.2',
}

# Point-to-point links for main campus
P2P_LINKS = {
    'main-agg1': {
        'Gi2': {'ip': '10.0.1.1', 'peer': 'core1', 'peer_ip': '10.0.1.0'},
        'Gi3': {'ip': '10.0.1.3', 'peer': 'core2', 'peer_ip': '10.0.1.2'},
        'Gi4': {'ip': '10.0.1.4', 'peer': 'main-edge1', 'peer_ip': '10.0.1.5'},
        'Gi5': {'ip': '10.0.1.6', 'peer': 'main-edge2', 'peer_ip': '10.0.1.7'},
    },
    'main-edge1': {
        'Gi2': {'ip': '10.0.1.5', 'peer': 'main-agg1', 'peer_ip': '10.0.1.4'},
        'Gi3': {'ip': '10.0.1.8', 'peer': 'main-edge2', 'peer_ip': '10.0.1.9'},
    },
    'main-edge2': {
        'Gi2': {'ip': '10.0.1.7', 'peer': 'main-agg1', 'peer_ip': '10.0.1.6'},
        'Gi3': {'ip': '10.0.1.9', 'peer': 'main-edge1', 'peer_ip': '10.0.1.8'},
    },
}

# Core router links to main campus
CORE_LINKS = {
    'core1': {'interface': 'GigabitEthernet5', 'ip': '10.0.1.0', 'peer': 'main-agg1'},
    'core2': {'interface': 'GigabitEthernet5', 'ip': '10.0.1.2', 'peer': 'main-agg1'},
}


@pytest.fixture(scope='module')
def testbed():
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    devices = {}
    for name in ALL_PHASE5_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    yield devices
    for device in devices.values():
        device.disconnect()


class TestMainCampusInterfaces:
    """Test main campus interface configuration."""

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_loopback0_configured(self, connected_devices, router):
        """Verify Loopback0 is configured with correct IP."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        expected_ip = LOOPBACKS[router]
        assert f'ip address {expected_ip} 255.255.255.255' in output, \
            f"{router}: Loopback0 should have IP {expected_ip}"

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_interfaces_configured(self, connected_devices, router):
        """Verify P2P interfaces are configured with correct IPs."""
        device = connected_devices[router]

        for intf, link_info in P2P_LINKS[router].items():
            output = device.execute(f'show running-config interface GigabitEthernet{intf[-1]}')
            assert f"ip address {link_info['ip']} 255.255.255.254" in output, \
                f"{router}: {intf} should have IP {link_info['ip']}"


class TestMainCampusOSPF:
    """Test OSPF configuration on main campus routers."""

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_ospf_process_running(self, connected_devices, router):
        """Verify OSPF process 1 is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        assert 'router ospf 1' in output, \
            f"{router}: OSPF process 1 not configured"

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_ospf_router_id(self, connected_devices, router):
        """Verify OSPF router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output, \
            f"{router}: OSPF router-id should be {expected_rid}"

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_loopback_in_ospf(self, connected_devices, router):
        """Verify Loopback0 is advertised in OSPF."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        assert 'ip ospf 1 area 0' in output, \
            f"{router}: Loopback0 not in OSPF area 0"

    def test_main_agg1_ospf_neighbors(self, connected_devices):
        """Verify main-agg1 has OSPF neighbors with core1, core2, edge1, edge2."""
        device = connected_devices['main-agg1']
        output = device.execute('show ip ospf neighbor')

        # Should have 4 neighbors: core1, core2, main-edge1, main-edge2
        expected_neighbors = [
            LOOPBACKS['core1'],
            LOOPBACKS['core2'],
            LOOPBACKS['main-edge1'],
            LOOPBACKS['main-edge2'],
        ]
        for neighbor in expected_neighbors:
            assert neighbor in output, \
                f"main-agg1: OSPF neighbor {neighbor} not found"

    @pytest.mark.parametrize('router', ['main-edge1', 'main-edge2'])
    def test_edge_ospf_neighbors(self, connected_devices, router):
        """Verify edge routers have OSPF neighbors."""
        device = connected_devices[router]
        output = device.execute('show ip ospf neighbor')

        # Each edge should have main-agg1 and the other edge as neighbors
        assert LOOPBACKS['main-agg1'] in output, \
            f"{router}: OSPF neighbor main-agg1 not found"


class TestCoreToMainCampusLinks:
    """Test core router links to main campus."""

    def test_core1_main_agg1_link(self, connected_devices):
        """Verify core1 Gi5 is configured for main-agg1 link."""
        device = connected_devices['core1']
        output = device.execute('show running-config interface GigabitEthernet5')

        assert 'ip address 10.0.1.0 255.255.255.254' in output, \
            "core1: Gi5 should have IP 10.0.1.0/31 for main-agg1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core1: Gi5 should be in OSPF area 0"

    def test_core2_main_agg1_link(self, connected_devices):
        """Verify core2 Gi5 is configured for main-agg1 link."""
        device = connected_devices['core2']
        output = device.execute('show running-config interface GigabitEthernet5')

        assert 'ip address 10.0.1.2 255.255.255.254' in output, \
            "core2: Gi5 should have IP 10.0.1.2/31 for main-agg1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core2: Gi5 should be in OSPF area 0"


class TestMainCampusMPLS:
    """Test MPLS LDP configuration on main campus routers."""

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_mpls_ldp_configured(self, connected_devices, router):
        """Verify MPLS LDP router-id is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section mpls ldp')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output or 'mpls ldp router-id Loopback0' in output, \
            f"{router}: MPLS LDP router-id not configured"

    @pytest.mark.parametrize('router', MAIN_CAMPUS_ROUTERS)
    def test_mpls_on_interfaces(self, connected_devices, router):
        """Verify MPLS is enabled on P2P interfaces."""
        device = connected_devices[router]

        for intf in P2P_LINKS[router].keys():
            output = device.execute(f'show running-config interface GigabitEthernet{intf[-1]}')
            assert 'mpls ip' in output, \
                f"{router}: MPLS not enabled on {intf}"

    def test_main_agg1_ldp_neighbors(self, connected_devices):
        """Verify main-agg1 has LDP neighbors."""
        device = connected_devices['main-agg1']
        output = device.execute('show mpls ldp neighbor')

        # Should have LDP neighbors with core1 and core2
        assert LOOPBACKS['core1'] in output, \
            "main-agg1: LDP neighbor core1 not found"
        assert LOOPBACKS['core2'] in output, \
            "main-agg1: LDP neighbor core2 not found"


class TestCoreToMainCampusMPLS:
    """Test MPLS is enabled on core links to main campus."""

    def test_core1_gi5_mpls(self, connected_devices):
        """Verify MPLS enabled on core1 Gi5."""
        device = connected_devices['core1']
        output = device.execute('show running-config interface GigabitEthernet5')

        assert 'mpls ip' in output, \
            "core1: MPLS not enabled on Gi5 (main-agg1 link)"

    def test_core2_gi5_mpls(self, connected_devices):
        """Verify MPLS enabled on core2 Gi5."""
        device = connected_devices['core2']
        output = device.execute('show running-config interface GigabitEthernet5')

        assert 'mpls ip' in output, \
            "core2: MPLS not enabled on Gi5 (main-agg1 link)"


class TestMainAgg1BGP:
    """Test MP-BGP configuration on main-agg1 (PE router)."""

    def test_bgp_process_configured(self, connected_devices):
        """Verify BGP process is configured on main-agg1."""
        device = connected_devices['main-agg1']
        output = device.execute('show running-config | section router bgp')

        assert f'router bgp {BGP_AS}' in output, \
            f"main-agg1: BGP AS {BGP_AS} not configured"

    def test_bgp_router_id(self, connected_devices):
        """Verify BGP router-id is set to loopback address."""
        device = connected_devices['main-agg1']
        output = device.execute('show running-config | section router bgp')

        expected_rid = LOOPBACKS['main-agg1']
        assert f'bgp router-id {expected_rid}' in output, \
            f"main-agg1: BGP router-id should be {expected_rid}"

    def test_bgp_peers_with_rrs(self, connected_devices):
        """Verify main-agg1 peers with all route reflectors."""
        device = connected_devices['main-agg1']
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} remote-as {BGP_AS}' in output, \
                f"main-agg1: Not configured to peer with RR {rr_ip}"

    def test_vpnv4_configured(self, connected_devices):
        """Verify VPNv4 address family is configured."""
        device = connected_devices['main-agg1']
        output = device.execute('show running-config | section router bgp')

        assert 'address-family vpnv4' in output, \
            "main-agg1: VPNv4 address family not configured"

    def test_vpnv4_neighbors_activated(self, connected_devices):
        """Verify RR neighbors are activated under VPNv4."""
        device = connected_devices['main-agg1']
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} activate' in output, \
                f"main-agg1: Neighbor {rr_ip} not activated under VPNv4"


class TestRRClientConfig:
    """Test that RRs have main-agg1 as client."""

    def test_core1_has_main_agg1_client(self, connected_devices):
        """Verify core1 has main-agg1 as RR client."""
        device = connected_devices['core1']
        output = device.execute('show running-config | section router bgp')

        agg_ip = LOOPBACKS['main-agg1']
        assert f'neighbor {agg_ip} route-reflector-client' in output, \
            f"core1: main-agg1 ({agg_ip}) not configured as RR client"

    def test_core2_has_main_agg1_client(self, connected_devices):
        """Verify core2 has main-agg1 as RR client."""
        device = connected_devices['core2']
        output = device.execute('show running-config | section router bgp')

        agg_ip = LOOPBACKS['main-agg1']
        assert f'neighbor {agg_ip} route-reflector-client' in output, \
            f"core2: main-agg1 ({agg_ip}) not configured as RR client"


class TestBGPSessionState:
    """Test actual BGP session states."""

    def test_main_agg1_bgp_sessions_established(self, connected_devices):
        """Verify main-agg1 BGP sessions are established with RRs."""
        device = connected_devices['main-agg1']
        output = device.execute('show bgp vpnv4 unicast all summary')

        for rr_ip in ROUTE_REFLECTORS:
            assert rr_ip in output, \
                f"main-agg1: BGP neighbor {rr_ip} not in summary"
            # Check neighbor line doesn't show Idle/Active
            for line in output.split('\n'):
                if rr_ip in line:
                    assert 'Idle' not in line and 'Active' not in line, \
                        f"main-agg1: BGP session with {rr_ip} not established"
