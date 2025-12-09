"""
Phase 4: Internet Gateway Tests
Tests OSPF, MPLS LDP, and MP-BGP configuration for inet-gw1 and inet-gw2

inet-gw1: connects to core1 via Gi2 (10.0.0.10/31)
inet-gw2: connects to core2 via Gi2 (10.0.0.12/31)
Both are BGP RR clients peering with core1, core2, core5
"""
import pytest
from genie.testbed import load

INET_GW_ROUTERS = ['inet-gw1', 'inet-gw2']
CORE_ROUTERS_PHASE4 = ['core1', 'core2']
ALL_PHASE4_ROUTERS = INET_GW_ROUTERS + CORE_ROUTERS_PHASE4

BGP_AS = 65001
ROUTE_REFLECTORS = ['10.255.1.1', '10.255.1.2', '10.255.1.5']  # core1, core2, core5

LOOPBACKS = {
    'inet-gw1': '10.255.0.1',
    'inet-gw2': '10.255.0.2',
    'core1': '10.255.1.1',
    'core2': '10.255.1.2',
}

# Point-to-point links
P2P_LINKS = {
    'inet-gw1': {'interface': 'GigabitEthernet2', 'ip': '10.0.0.11', 'peer': 'core1'},
    'inet-gw2': {'interface': 'GigabitEthernet2', 'ip': '10.0.0.13', 'peer': 'core2'},
    'core1-inet': {'interface': 'GigabitEthernet4', 'ip': '10.0.0.10', 'peer': 'inet-gw1'},
    'core2-inet': {'interface': 'GigabitEthernet4', 'ip': '10.0.0.12', 'peer': 'inet-gw2'},
}

# BGP neighbors for inet-gw routers (they peer with all RRs)
BGP_NEIGHBORS = {
    'inet-gw1': ['10.255.1.1', '10.255.1.2', '10.255.1.5'],
    'inet-gw2': ['10.255.1.1', '10.255.1.2', '10.255.1.5'],
}


@pytest.fixture(scope='module')
def testbed():
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    devices = {}
    for name in ALL_PHASE4_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    yield devices
    for device in devices.values():
        device.disconnect()


class TestInetGwInterfaces:
    """Test inet-gw interface configuration."""

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_loopback0_configured(self, connected_devices, router):
        """Verify Loopback0 is configured with correct IP."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        expected_ip = LOOPBACKS[router]
        assert f'ip address {expected_ip} 255.255.255.255' in output, \
            f"{router}: Loopback0 should have IP {expected_ip}"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_uplink_interface_configured(self, connected_devices, router):
        """Verify uplink interface to core is configured."""
        device = connected_devices[router]
        link_info = P2P_LINKS[router]
        output = device.execute(f"show running-config interface {link_info['interface']}")

        assert f"ip address {link_info['ip']} 255.255.255.254" in output, \
            f"{router}: {link_info['interface']} should have IP {link_info['ip']}"


class TestInetGwOSPF:
    """Test OSPF configuration on inet-gw routers."""

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_ospf_process_running(self, connected_devices, router):
        """Verify OSPF process 1 is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        assert 'router ospf 1' in output, \
            f"{router}: OSPF process 1 not configured"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_ospf_router_id(self, connected_devices, router):
        """Verify OSPF router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router ospf')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output, \
            f"{router}: OSPF router-id should be {expected_rid}"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_ospf_neighbor_established(self, connected_devices, router):
        """Verify OSPF neighbor is established with core router."""
        device = connected_devices[router]
        output = device.execute('show ip ospf neighbor')

        peer = P2P_LINKS[router]['peer']
        peer_rid = LOOPBACKS[peer]
        assert peer_rid in output and 'FULL' in output, \
            f"{router}: OSPF neighbor {peer} ({peer_rid}) not in FULL state"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_loopback_in_ospf(self, connected_devices, router):
        """Verify Loopback0 is advertised in OSPF."""
        device = connected_devices[router]
        output = device.execute('show running-config interface Loopback0')

        assert 'ip ospf 1 area 0' in output, \
            f"{router}: Loopback0 not in OSPF area 0"


class TestCoreToInetGwLinks:
    """Test core router links to inet-gw routers."""

    def test_core1_inet_gw1_link(self, connected_devices):
        """Verify core1 Gi4 is configured for inet-gw1 link."""
        device = connected_devices['core1']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'ip address 10.0.0.10 255.255.255.254' in output, \
            "core1: Gi4 should have IP 10.0.0.10/31 for inet-gw1 link"
        assert 'ip ospf 1 area 0' in output, \
            "core1: Gi4 should be in OSPF area 0"

    def test_core2_inet_gw2_link(self, connected_devices):
        """Verify core2 Gi4 is configured for inet-gw2 link."""
        device = connected_devices['core2']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'ip address 10.0.0.12 255.255.255.254' in output, \
            "core2: Gi4 should have IP 10.0.0.12/31 for inet-gw2 link"
        assert 'ip ospf 1 area 0' in output, \
            "core2: Gi4 should be in OSPF area 0"


class TestInetGwMPLS:
    """Test MPLS LDP configuration on inet-gw routers."""

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_mpls_ldp_configured(self, connected_devices, router):
        """Verify MPLS LDP router-id is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section mpls ldp')

        expected_rid = LOOPBACKS[router]
        assert f'router-id {expected_rid}' in output or 'mpls ldp router-id Loopback0' in output, \
            f"{router}: MPLS LDP router-id not configured"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_mpls_on_uplink(self, connected_devices, router):
        """Verify MPLS is enabled on uplink interface."""
        device = connected_devices[router]
        link_info = P2P_LINKS[router]
        output = device.execute(f"show running-config interface {link_info['interface']}")

        assert 'mpls ip' in output, \
            f"{router}: MPLS not enabled on {link_info['interface']}"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_ldp_neighbor_established(self, connected_devices, router):
        """Verify LDP neighbor is established."""
        device = connected_devices[router]
        output = device.execute('show mpls ldp neighbor')

        peer = P2P_LINKS[router]['peer']
        peer_rid = LOOPBACKS[peer]
        assert peer_rid in output, \
            f"{router}: LDP neighbor {peer} ({peer_rid}) not found"


class TestCoreToInetGwMPLS:
    """Test MPLS is enabled on core links to inet-gw."""

    def test_core1_gi4_mpls(self, connected_devices):
        """Verify MPLS enabled on core1 Gi4."""
        device = connected_devices['core1']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'mpls ip' in output, \
            "core1: MPLS not enabled on Gi4 (inet-gw1 link)"

    def test_core2_gi4_mpls(self, connected_devices):
        """Verify MPLS enabled on core2 Gi4."""
        device = connected_devices['core2']
        output = device.execute('show running-config interface GigabitEthernet4')

        assert 'mpls ip' in output, \
            "core2: MPLS not enabled on Gi4 (inet-gw2 link)"


class TestInetGwBGP:
    """Test MP-BGP configuration on inet-gw routers."""

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_bgp_process_configured(self, connected_devices, router):
        """Verify BGP process is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        assert f'router bgp {BGP_AS}' in output, \
            f"{router}: BGP AS {BGP_AS} not configured"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_bgp_router_id(self, connected_devices, router):
        """Verify BGP router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        expected_rid = LOOPBACKS[router]
        assert f'bgp router-id {expected_rid}' in output, \
            f"{router}: BGP router-id should be {expected_rid}"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_bgp_peers_with_rrs(self, connected_devices, router):
        """Verify inet-gw peers with all route reflectors."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} remote-as {BGP_AS}' in output, \
                f"{router}: Not configured to peer with RR {rr_ip}"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_vpnv4_configured(self, connected_devices, router):
        """Verify VPNv4 address family is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        assert 'address-family vpnv4' in output, \
            f"{router}: VPNv4 address family not configured"

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_vpnv4_neighbors_activated(self, connected_devices, router):
        """Verify RR neighbors are activated under VPNv4."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        for rr_ip in ROUTE_REFLECTORS:
            assert f'neighbor {rr_ip} activate' in output, \
                f"{router}: Neighbor {rr_ip} not activated under VPNv4"


class TestRRClientConfig:
    """Test that RRs have inet-gw routers as clients."""

    def test_core1_has_inet_gw_clients(self, connected_devices):
        """Verify core1 has inet-gw routers as RR clients."""
        device = connected_devices['core1']
        output = device.execute('show running-config | section router bgp')

        for gw in INET_GW_ROUTERS:
            gw_ip = LOOPBACKS[gw]
            assert f'neighbor {gw_ip} route-reflector-client' in output, \
                f"core1: {gw} ({gw_ip}) not configured as RR client"

    def test_core2_has_inet_gw_clients(self, connected_devices):
        """Verify core2 has inet-gw routers as RR clients."""
        device = connected_devices['core2']
        output = device.execute('show running-config | section router bgp')

        for gw in INET_GW_ROUTERS:
            gw_ip = LOOPBACKS[gw]
            assert f'neighbor {gw_ip} route-reflector-client' in output, \
                f"core2: {gw} ({gw_ip}) not configured as RR client"


class TestBGPSessionState:
    """Test actual BGP session states."""

    @pytest.mark.parametrize('router', INET_GW_ROUTERS)
    def test_bgp_sessions_established(self, connected_devices, router):
        """Verify BGP sessions are established with RRs."""
        device = connected_devices[router]
        output = device.execute('show bgp vpnv4 unicast all summary')

        for rr_ip in ROUTE_REFLECTORS:
            assert rr_ip in output, \
                f"{router}: BGP neighbor {rr_ip} not in summary"
            # Check neighbor line doesn't show Idle/Active
            for line in output.split('\n'):
                if rr_ip in line:
                    assert 'Idle' not in line and 'Active' not in line, \
                        f"{router}: BGP session with {rr_ip} not established"
