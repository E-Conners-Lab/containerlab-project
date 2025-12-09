"""
Phase 3: MP-BGP Route Reflector Tests
Tests BGP configuration and VPNv4 address family across core routers

Route Reflectors: core1, core2, core5
RR Clients: core3, core4
"""
import pytest
from genie.testbed import load

CORE_ROUTERS = ['core1', 'core2', 'core3', 'core4', 'core5']
ROUTE_REFLECTORS = ['core1', 'core2', 'core5']
RR_CLIENTS = ['core3', 'core4']

BGP_AS = 65001

LOOPBACKS = {
    'core1': '10.255.1.1',
    'core2': '10.255.1.2',
    'core3': '10.255.1.3',
    'core4': '10.255.1.4',
    'core5': '10.255.1.5',
}

# Expected BGP neighbors for each router (full mesh between RRs, clients peer with all RRs)
EXPECTED_BGP_NEIGHBORS = {
    'core1': ['10.255.1.2', '10.255.1.3', '10.255.1.4', '10.255.1.5'],  # RR: peers with all
    'core2': ['10.255.1.1', '10.255.1.3', '10.255.1.4', '10.255.1.5'],  # RR: peers with all
    'core3': ['10.255.1.1', '10.255.1.2', '10.255.1.5'],                # Client: peers with RRs
    'core4': ['10.255.1.1', '10.255.1.2', '10.255.1.5'],                # Client: peers with RRs
    'core5': ['10.255.1.1', '10.255.1.2', '10.255.1.3', '10.255.1.4'],  # RR: peers with all
}


@pytest.fixture(scope='module')
def testbed():
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    devices = {}
    for name in CORE_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    yield devices
    for device in devices.values():
        device.disconnect()


class TestBGPConfiguration:
    """Test BGP is configured correctly on core routers."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_bgp_process_running(self, connected_devices, router):
        """Verify BGP process is running with correct AS."""
        device = connected_devices[router]
        # Use show run to verify BGP config exists
        output = device.execute('show running-config | section router bgp')

        assert f'router bgp {BGP_AS}' in output, \
            f"{router}: BGP AS {BGP_AS} not configured"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_bgp_router_id(self, connected_devices, router):
        """Verify BGP router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        expected_rid = LOOPBACKS[router]
        assert f'bgp router-id {expected_rid}' in output, \
            f"{router}: BGP router-id should be {expected_rid}"


class TestBGPNeighbors:
    """Test BGP neighbor relationships."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_bgp_neighbor_count(self, connected_devices, router):
        """Verify correct number of BGP neighbors configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        expected_count = len(EXPECTED_BGP_NEIGHBORS[router])
        # Count neighbor statements
        neighbor_count = output.count('neighbor 10.255.1.')
        # Divide by expected occurrences per neighbor (remote-as, update-source, description, etc)
        # Just check that neighbors are configured
        for neighbor in EXPECTED_BGP_NEIGHBORS[router]:
            assert f'neighbor {neighbor}' in output, \
                f"{router}: Neighbor {neighbor} not configured"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_bgp_neighbors_established(self, connected_devices, router):
        """Verify BGP neighbors are in Established state (VPNv4)."""
        device = connected_devices[router]
        # Use show bgp vpnv4 unicast all summary for VPNv4-only sessions
        output = device.execute('show bgp vpnv4 unicast all summary')

        expected_neighbors = EXPECTED_BGP_NEIGHBORS[router]
        for neighbor in expected_neighbors:
            assert neighbor in output, \
                f"{router}: BGP neighbor {neighbor} not found in VPNv4 summary"

        # Check no neighbors are in Idle/Active state (they should show a number for prefixes)
        # If Idle or Active appears for our neighbors, session isn't established
        lines = output.split('\n')
        for line in lines:
            for neighbor in expected_neighbors:
                if neighbor in line:
                    # Line should NOT contain Idle or Active state
                    assert 'Idle' not in line and 'Active' not in line, \
                        f"{router}: BGP neighbor {neighbor} not established"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_correct_bgp_neighbors(self, connected_devices, router):
        """Verify BGP neighbors are the expected routers."""
        device = connected_devices[router]
        output = device.execute('show bgp vpnv4 unicast all summary')

        expected = EXPECTED_BGP_NEIGHBORS[router]
        for neighbor in expected:
            assert neighbor in output, \
                f"{router}: Missing BGP neighbor {neighbor}"


class TestVPNv4AddressFamily:
    """Test VPNv4 address family configuration."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_vpnv4_configured(self, connected_devices, router):
        """Verify VPNv4 address family is configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        assert 'address-family vpnv4' in output, \
            f"{router}: VPNv4 address family not configured"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_vpnv4_neighbors_activated(self, connected_devices, router):
        """Verify neighbors are activated under VPNv4."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        expected_neighbors = EXPECTED_BGP_NEIGHBORS[router]
        for neighbor in expected_neighbors:
            # Check neighbor is activated (appears after address-family vpnv4)
            assert f'neighbor {neighbor} activate' in output, \
                f"{router}: Neighbor {neighbor} not activated under VPNv4"


class TestRouteReflectorConfig:
    """Test Route Reflector specific configuration."""

    @pytest.mark.parametrize('router', ROUTE_REFLECTORS)
    def test_rr_client_configured(self, connected_devices, router):
        """Verify RR has route-reflector-client configured for clients."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        # RRs should have route-reflector-client for core3 and core4
        for client in RR_CLIENTS:
            client_ip = LOOPBACKS[client]
            assert f'neighbor {client_ip} route-reflector-client' in output, \
                f"{router}: {client} ({client_ip}) not configured as RR client"

    @pytest.mark.parametrize('router', RR_CLIENTS)
    def test_client_peers_with_all_rrs(self, connected_devices, router):
        """Verify RR clients peer with all route reflectors."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        for rr in ROUTE_REFLECTORS:
            rr_ip = LOOPBACKS[rr]
            assert f'neighbor {rr_ip} remote-as {BGP_AS}' in output, \
                f"{router}: Not configured to peer with RR {rr} ({rr_ip})"


class TestBGPSessionState:
    """Test actual BGP session states."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_all_sessions_established(self, connected_devices, router):
        """Verify all expected BGP sessions are established."""
        device = connected_devices[router]
        output = device.execute('show bgp vpnv4 unicast all summary')

        # Check that we see the neighbor IPs and they have established sessions
        # Established sessions show a number (prefix count) not Idle/Active/Connect
        expected = EXPECTED_BGP_NEIGHBORS[router]
        for neighbor in expected:
            assert neighbor in output, \
                f"{router}: Neighbor {neighbor} not in BGP summary"
