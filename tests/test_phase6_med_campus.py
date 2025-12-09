"""
Phase 6: Medical Campus Tests
Tests OSPF, MPLS LDP, and MP-BGP configuration for med-agg1, med-edge1, med-edge2

Medical Campus links (10.0.2.x):
- core2 Gi6 (10.0.2.0) <-> med-agg1 Gi2 (10.0.2.1)
- core3 Gi4 (10.0.2.2) <-> med-agg1 Gi3 (10.0.2.3)
- med-agg1 Gi4 (10.0.2.4) <-> med-edge1 Gi2 (10.0.2.5)
- med-agg1 Gi5 (10.0.2.6) <-> med-edge2 Gi2 (10.0.2.7)
- med-edge1 Gi3 (10.0.2.8) <-> med-edge2 Gi3 (10.0.2.9)

med-agg1 is a BGP RR client peering with core1, core2, core5
"""
import pytest
from genie.testbed import load

MED_CAMPUS_ROUTERS = ['med-agg1', 'med-edge1', 'med-edge2']
CORE_ROUTERS_PHASE6 = ['core2', 'core3']
ALL_PHASE6_ROUTERS = MED_CAMPUS_ROUTERS + CORE_ROUTERS_PHASE6

BGP_AS = 65001
ROUTE_REFLECTORS = ['10.255.1.1', '10.255.1.2', '10.255.1.5']  # core1, core2, core5

LOOPBACKS = {
    'med-agg1': '10.255.20.1',
    'med-edge1': '10.255.20.2',
    'med-edge2': '10.255.20.3',
    'core2': '10.255.1.2',
    'core3': '10.255.1.3',
}

# Point-to-point links for medical campus
P2P_LINKS = {
    'med-agg1': {
        'Gi2': {'ip': '10.0.2.1', 'peer': 'core2', 'peer_ip': '10.0.2.0'},
        'Gi3': {'ip': '10.0.2.3', 'peer': 'core3', 'peer_ip': '10.0.2.2'},
        'Gi4': {'ip': '10.0.2.4', 'peer': 'med-edge1', 'peer_ip': '10.0.2.5'},
        'Gi5': {'ip': '10.0.2.6', 'peer': 'med-edge2', 'peer_ip': '10.0.2.7'},
    },
    'med-edge1': {
        'Gi2': {'ip': '10.0.2.5', 'peer': 'med-agg1', 'peer_ip': '10.0.2.4'},
        'Gi3': {'ip': '10.0.2.8', 'peer': 'med-edge2', 'peer_ip': '10.0.2.9'},
    },
    'med-edge2': {
        'Gi2': {'ip': '10.0.2.7', 'peer': 'med-agg1', 'peer_ip': '10.0.2.6'},
        'Gi3': {'ip': '10.0.2.9', 'peer': 'med-edge1', 'peer_ip': '10.0.2.8'},
    },
}

# Core router links to medical campus
CORE_LINKS = {
    'core2': {'interface': 'GigabitEthernet6', 'ip': '10.0.2.0', 'peer': 'med-agg1'},
    'core3': {'interface': 'GigabitEthernet4', 'ip': '10.0.2.2', 'peer': 'med-agg1'},
}


@pytest.fixture(scope='module')
def testbed():
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    devices = {}
    for name in ALL_PHASE6_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    yield devices
    for device in devices.values():
        device.disconnect()


class TestMedCampusInterfaces:
    """Test medical campus interface configuration."""

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_loopback0_configured(self, connected_devices, router):
        """Verify Loopback0 is configured with correct IP."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        expected_ip = LOOPBACKS[router]
        assert f'ip address {expected_ip} 255.255.255.255' in output, \
            f"{router}: Loopback0 should have IP {expected_ip}"

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_interfaces_configured(self, connected_devices, router):
        """Verify P2P interfaces are configured with correct IPs."""
        device = connected_devices[router]

        for intf, link_info in P2P_LINKS[router].items():
            output = device.execute(f'show running-config interface GigabitEthernet{intf[-1]}')
            assert f"ip address {link_info['ip']} 255.255.255.254" in output, \
                f"{router}: {intf} should have IP {link_info['ip']}"


class TestMedCampusOSPF:
    """Test OSPF configuration on medical campus routers."""

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_ospf_process_running(self, connected_devices, router):
        """Verify OSPF process 1 is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        assert 'router ospf 1' in output, \
            f"{router}: OSPF process 1 not configured"

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_ospf_router_id(self, connected_devices, router):
        """Verify OSPF router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output, \
            f"{router}: OSPF router-id should be {expected_rid}"

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_loopback_in_ospf(self, connected_devices, router):
        """Verify Loopback0 is advertised in OSPF."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        assert 'ip ospf 1 area 0' in output, \
            f"{router}: Loopback0 not in OSPF area 0"

    def test_med_agg1_ospf_neighbors(self, connected_devices):
        """Verify med-agg1 has OSPF neighbors with core2, core3, edge1, edge2."""
        device = connected_devices['med-agg1']
        output = device.execute('show ip ospf neighbor')

        # Should have 4 neighbors: core2, core3, med-edge1, med-edge2
        expected_neighbors = [
            LOOPBACKS['core2'],
            LOOPBACKS['core3'],
            LOOPBACKS['med-edge1'],
            LOOPBACKS['med-edge2'],
        ]
        for neighbor in expected_neighbors:
            assert neighbor in output, \
                f"med-agg1: OSPF neighbor {neighbor} not found"

    @pytest.mark.parametrize('router', ['med-edge1', 'med-edge2'])
    def test_edge_ospf_neighbors(self, connected_devices, router):
        """Verify edge routers have OSPF neighbors."""
        device = connected_devices[router]
        output = device.execute('show ip ospf neighbor')

        # Each edge should have med-agg1 and the other edge as neighbors
        assert LOOPBACKS['med-agg1'] in output, \
            f"{router}: OSPF neighbor med-agg1 not found"


class TestCoreToMedCampusLinks:
    """Test core router links to medical campus."""

    def test_core2_med_agg1_link(self, connected_devices):
        """Verify core2 Gi6 is configured for med-agg1 link."""
        device = connected_devices['core2']
        output = device.execute('show running-config interface GigabitEthernet6')

        assert 'ip address 10.0.2.0 255.255.255.254' in output, \
            "core2: Gi6 should have IP 10.0.2.0/31 for med-agg1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core2: Gi6 should be in OSPF area 0"

    def test_core3_med_agg1_link(self, connected_devices):
        """Verify core3 Gi4 is configured for med-agg1 link."""
        device = connected_devices['core3']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'ip address 10.0.2.2 255.255.255.254' in output, \
            "core3: Gi4 should have IP 10.0.2.2/31 for med-agg1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core3: Gi4 should be in OSPF area 0"


class TestMedCampusMPLS:
    """Test MPLS LDP configuration on medical campus routers."""

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_mpls_ldp_configured(self, connected_devices, router):
        """Verify MPLS LDP router-id is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section mpls ldp')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output or 'mpls ldp router-id Loopback0' in output, \
            f"{router}: MPLS LDP router-id not configured"

    @pytest.mark.parametrize('router', MED_CAMPUS_ROUTERS)
    def test_mpls_on_interfaces(self, connected_devices, router):
        """Verify MPLS is enabled on P2P interfaces."""
        device = connected_devices[router]

        for intf in P2P_LINKS[router].keys():
            output = device.execute(f'show running-config interface GigabitEthernet{intf[-1]}')
            assert 'mpls ip' in output, \
                f"{router}: MPLS not enabled on {intf}"

    def test_med_agg1_ldp_neighbors(self, connected_devices):
        """Verify med-agg1 has LDP neighbors."""
        device = connected_devices['med-agg1']
        output = device.execute('show mpls ldp neighbor')

        # Should have LDP neighbors with core2 and core3
        assert LOOPBACKS['core2'] in output, \
            "med-agg1: LDP neighbor core2 not found"
        assert LOOPBACKS['core3'] in output, \
            "med-agg1: LDP neighbor core3 not found"


class TestCoreToMedCampusMPLS:
    """Test MPLS is enabled on core links to medical campus."""

    def test_core2_gi6_mpls(self, connected_devices):
        """Verify MPLS enabled on core2 Gi6."""
        device = connected_devices['core2']
        output = device.execute('show running-config interface GigabitEthernet6')

        assert 'mpls ip' in output, \
            "core2: MPLS not enabled on Gi6 (med-agg1 link)"

    def test_core3_gi4_mpls(self, connected_devices):
        """Verify MPLS enabled on core3 Gi4."""
        device = connected_devices['core3']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'mpls ip' in output, \
            "core3: MPLS not enabled on Gi4 (med-agg1 link)"


class TestMedAgg1BGP:
    """Test MP-BGP configuration on med-agg1 (PE router)."""

    def test_bgp_process_configured(self, connected_devices):
        """Verify BGP process is configured on med-agg1."""
        device = connected_devices['med-agg1']
        output = device.execute('show running-config | section router bgp')

        assert f'router bgp {BGP_AS}' in output, \
            f"med-agg1: BGP AS {BGP_AS} not configured"

    def test_bgp_router_id(self, connected_devices):
        """Verify BGP router-id is set to loopback address."""
        device = connected_devices['med-agg1']
        output = device.execute('show running-config | section router bgp')

        expected_rid = LOOPBACKS['med-agg1']
        assert f'bgp router-id {expected_rid}' in output, \
            f"med-agg1: BGP router-id should be {expected_rid}"

    def test_bgp_peers_with_rrs(self, connected_devices):
        """Verify med-agg1 peers with all route reflectors."""
        device = connected_devices['med-agg1']
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} remote-as {BGP_AS}' in output, \
                f"med-agg1: Not configured to peer with RR {rr_ip}"

    def test_vpnv4_configured(self, connected_devices):
        """Verify VPNv4 address family is configured."""
        device = connected_devices['med-agg1']
        output = device.execute('show running-config | section router bgp')

        assert 'address-family vpnv4' in output, \
            "med-agg1: VPNv4 address family not configured"

    def test_vpnv4_neighbors_activated(self, connected_devices):
        """Verify RR neighbors are activated under VPNv4."""
        device = connected_devices['med-agg1']
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} activate' in output, \
                f"med-agg1: Neighbor {rr_ip} not activated under VPNv4"


class TestRRClientConfig:
    """Test that RRs have med-agg1 as client."""

    def test_core2_has_med_agg1_client(self, connected_devices):
        """Verify core2 has med-agg1 as RR client."""
        device = connected_devices['core2']
        output = device.execute('show running-config | section router bgp')

        agg_ip = LOOPBACKS['med-agg1']
        assert f'neighbor {agg_ip} route-reflector-client' in output, \
            f"core2: med-agg1 ({agg_ip}) not configured as RR client"


class TestBGPSessionState:
    """Test actual BGP session states."""

    def test_med_agg1_bgp_sessions_established(self, connected_devices):
        """Verify med-agg1 BGP sessions are established with RRs."""
        device = connected_devices['med-agg1']
        output = device.execute('show bgp vpnv4 unicast all summary')

        for rr_ip in ROUTE_REFLECTORS:
            assert rr_ip in output, \
                f"med-agg1: BGP neighbor {rr_ip} not in summary"
            # Check neighbor line doesn't show Idle/Active
            for line in output.split('\n'):
                if rr_ip in line:
                    assert 'Idle' not in line and 'Active' not in line, \
                        f"med-agg1: BGP session with {rr_ip} not established"
