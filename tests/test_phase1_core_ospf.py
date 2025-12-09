"""
Phase 1: Core Ring OSPF Tests
Tests OSPF adjacencies and reachability across the core ring (core1-5)
"""
import pytest
from genie.testbed import load

# Core router details
CORE_ROUTERS = ['core1', 'core2', 'core3', 'core4', 'core5']

LOOPBACKS = {
    'core1': '10.255.1.1',
    'core2': '10.255.1.2',
    'core3': '10.255.1.3',
    'core4': '10.255.1.4',
    'core5': '10.255.1.5',
}

# Expected OSPF neighbors for each core router (ring topology)
EXPECTED_NEIGHBORS = {
    'core1': ['10.255.1.2', '10.255.1.5'],  # core2, core5
    'core2': ['10.255.1.1', '10.255.1.3'],  # core1, core3
    'core3': ['10.255.1.2', '10.255.1.4'],  # core2, core4
    'core4': ['10.255.1.3', '10.255.1.5'],  # core3, core5
    'core5': ['10.255.1.4', '10.255.1.1'],  # core4, core1
}


@pytest.fixture(scope='module')
def testbed():
    """Load the testbed file."""
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    """Connect to all core routers."""
    devices = {}
    for name in CORE_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    # Disconnect after tests
    for device in devices.values():
        device.disconnect()


class TestCoreLoopbacks:
    """Test that loopback interfaces are configured correctly."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_loopback_exists(self, connected_devices, router):
        """Verify Loopback0 interface exists with correct IP."""
        device = connected_devices[router]
        output = device.parse('show ip interface brief')

        assert 'Loopback0' in output['interface'], \
            f"{router}: Loopback0 interface not found"

        loopback = output['interface']['Loopback0']
        expected_ip = LOOPBACKS[router]
        assert loopback['ip_address'] == expected_ip, \
            f"{router}: Expected Loopback0 IP {expected_ip}, got {loopback['ip_address']}"


class TestOSPFConfiguration:
    """Test that OSPF is configured correctly on core routers."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ospf_process_running(self, connected_devices, router):
        """Verify OSPF process 1 is running."""
        device = connected_devices[router]
        try:
            output = device.parse('show ip ospf')
            assert '1' in output['vrf']['default']['address_family']['ipv4']['instance'], \
                f"{router}: OSPF process 1 not found"
        except Exception as e:
            pytest.fail(f"{router}: OSPF not configured - {e}")

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ospf_router_id(self, connected_devices, router):
        """Verify OSPF router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.parse('show ip ospf')
        ospf_instance = output['vrf']['default']['address_family']['ipv4']['instance']['1']
        expected_rid = LOOPBACKS[router]
        assert ospf_instance['router_id'] == expected_rid, \
            f"{router}: Expected router-id {expected_rid}, got {ospf_instance['router_id']}"


class TestOSPFNeighbors:
    """Test OSPF neighbor adjacencies."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ospf_neighbor_count(self, connected_devices, router):
        """Verify each core router has exactly 2 OSPF neighbors."""
        device = connected_devices[router]
        try:
            output = device.parse('show ip ospf neighbor')
            neighbors = list(output.get('interfaces', {}).keys())
            neighbor_count = sum(
                len(output['interfaces'][intf].get('neighbors', {}))
                for intf in neighbors
            )
            assert neighbor_count == 2, \
                f"{router}: Expected 2 OSPF neighbors, got {neighbor_count}"
        except Exception as e:
            pytest.fail(f"{router}: No OSPF neighbors found - {e}")

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ospf_neighbors_full(self, connected_devices, router):
        """Verify all OSPF neighbors are in FULL state."""
        device = connected_devices[router]
        output = device.parse('show ip ospf neighbor')

        for intf in output.get('interfaces', {}):
            for neighbor_id, neighbor_data in output['interfaces'][intf].get('neighbors', {}).items():
                state = neighbor_data.get('state', '')
                assert 'FULL' in state, \
                    f"{router}: Neighbor {neighbor_id} on {intf} is {state}, expected FULL"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_correct_ospf_neighbors(self, connected_devices, router):
        """Verify OSPF neighbors are the expected routers."""
        device = connected_devices[router]
        output = device.parse('show ip ospf neighbor')

        found_neighbors = set()
        for intf in output.get('interfaces', {}):
            for neighbor_id in output['interfaces'][intf].get('neighbors', {}):
                found_neighbors.add(neighbor_id)

        expected = set(EXPECTED_NEIGHBORS[router])
        assert found_neighbors == expected, \
            f"{router}: Expected neighbors {expected}, got {found_neighbors}"


class TestOSPFRouting:
    """Test OSPF routing table entries."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_all_loopbacks_in_routing_table(self, connected_devices, router):
        """Verify all core loopbacks are reachable via OSPF."""
        device = connected_devices[router]
        output = device.parse('show ip route')

        for target_router, loopback_ip in LOOPBACKS.items():
            if target_router == router:
                continue  # Skip self

            route_prefix = f"{loopback_ip}/32"
            # Check if route exists in OSPF routes
            ospf_routes = output.get('vrf', {}).get('default', {}).get('address_family', {}).get('ipv4', {}).get('routes', {})

            assert route_prefix in ospf_routes, \
                f"{router}: Route to {target_router} ({route_prefix}) not found"

            route = ospf_routes[route_prefix]
            assert route.get('source_protocol') == 'ospf', \
                f"{router}: Route to {route_prefix} is not via OSPF"


class TestConnectivity:
    """Test actual connectivity between core routers."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ping_all_loopbacks(self, connected_devices, router):
        """Verify ping connectivity to all other core loopbacks."""
        device = connected_devices[router]

        for target_router, loopback_ip in LOOPBACKS.items():
            if target_router == router:
                continue  # Skip self

            # Use source loopback for ping
            output = device.execute(f'ping {loopback_ip} source Loopback0 repeat 3')
            assert 'Success rate is 100' in output or '!!!' in output, \
                f"{router}: Cannot ping {target_router} ({loopback_ip})"
