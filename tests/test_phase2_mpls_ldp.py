"""
Phase 2: MPLS LDP Tests
Tests MPLS and LDP configuration across the core ring (core1-5)
"""
import pytest
from genie.testbed import load

CORE_ROUTERS = ['core1', 'core2', 'core3', 'core4', 'core5']

LOOPBACKS = {
    'core1': '10.255.1.1',
    'core2': '10.255.1.2',
    'core3': '10.255.1.3',
    'core4': '10.255.1.4',
    'core5': '10.255.1.5',
}

# Expected LDP neighbors (by router-id/loopback)
EXPECTED_LDP_NEIGHBORS = {
    'core1': ['10.255.1.2', '10.255.1.5'],
    'core2': ['10.255.1.1', '10.255.1.3'],
    'core3': ['10.255.1.2', '10.255.1.4'],
    'core4': ['10.255.1.3', '10.255.1.5'],
    'core5': ['10.255.1.4', '10.255.1.1'],
}

# Core ring interfaces that should have MPLS enabled
MPLS_INTERFACES = {
    'core1': ['GigabitEthernet2', 'GigabitEthernet3'],
    'core2': ['GigabitEthernet2', 'GigabitEthernet3'],
    'core3': ['GigabitEthernet2', 'GigabitEthernet3'],
    'core4': ['GigabitEthernet2', 'GigabitEthernet3'],
    'core5': ['GigabitEthernet2', 'GigabitEthernet3'],
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


class TestMPLSConfiguration:
    """Test MPLS is enabled on core routers."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_mpls_interfaces_enabled(self, connected_devices, router):
        """Verify MPLS is enabled on core ring interfaces."""
        device = connected_devices[router]
        output = device.parse('show mpls interfaces')

        # Parser returns: {'vrf': {'default': {'interfaces': {...}}}}
        interfaces = output.get('vrf', {}).get('default', {}).get('interfaces', {})

        expected_interfaces = MPLS_INTERFACES[router]
        for intf in expected_interfaces:
            assert intf in interfaces, \
                f"{router}: MPLS not enabled on {intf}"

            intf_data = interfaces[intf]
            assert intf_data.get('ip') == 'yes', \
                f"{router}: MPLS IP not enabled on {intf}"


class TestLDPConfiguration:
    """Test LDP is configured correctly."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ldp_router_id(self, connected_devices, router):
        """Verify LDP router-id is set to loopback address."""
        device = connected_devices[router]
        output = device.execute('show mpls ldp discovery')

        expected_rid = LOOPBACKS[router]
        assert f"Local LDP Identifier" in output, \
            f"{router}: LDP not running"
        assert expected_rid in output, \
            f"{router}: LDP router-id should be {expected_rid}"


class TestLDPNeighbors:
    """Test LDP neighbor relationships."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ldp_neighbor_count(self, connected_devices, router):
        """Verify each core router has at least 2 LDP neighbors (core ring)."""
        device = connected_devices[router]
        output = device.execute('show mpls ldp neighbor')

        # Count "Peer LDP Ident" occurrences
        neighbor_count = output.count('Peer LDP Ident')
        assert neighbor_count >= 2, \
            f"{router}: Expected at least 2 LDP neighbors, got {neighbor_count}"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_ldp_neighbors_operational(self, connected_devices, router):
        """Verify LDP neighbors are in operational state."""
        device = connected_devices[router]
        output = device.execute('show mpls ldp neighbor')

        # Check for operational state
        assert 'State: Oper' in output, \
            f"{router}: LDP neighbors not in operational state"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_correct_ldp_neighbors(self, connected_devices, router):
        """Verify LDP neighbors are the expected routers."""
        device = connected_devices[router]
        output = device.execute('show mpls ldp neighbor')

        expected = EXPECTED_LDP_NEIGHBORS[router]
        for neighbor_id in expected:
            assert neighbor_id in output, \
                f"{router}: Missing LDP neighbor {neighbor_id}"


class TestMPLSLabels:
    """Test MPLS label distribution."""

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_labels_for_loopbacks(self, connected_devices, router):
        """Verify MPLS labels exist for all core loopbacks."""
        device = connected_devices[router]
        output = device.execute('show mpls forwarding-table')

        for target_router, loopback_ip in LOOPBACKS.items():
            if target_router == router:
                continue

            # Check for label binding to remote loopback
            assert loopback_ip in output, \
                f"{router}: No MPLS label for {target_router} ({loopback_ip}/32)"

    @pytest.mark.parametrize('router', CORE_ROUTERS)
    def test_label_switched_path(self, connected_devices, router):
        """Verify LSP exists to remote loopbacks via traceroute."""
        device = connected_devices[router]

        # Pick a remote loopback to test
        if router == 'core1':
            target = '10.255.1.3'  # core3 (2 hops away)
        elif router == 'core3':
            target = '10.255.1.5'  # core5 (2 hops away)
        else:
            target = '10.255.1.1'  # core1

        output = device.execute(f'traceroute mpls ipv4 {target}/32 source {LOOPBACKS[router]}', timeout=30)

        # Should see MPLS labels in traceroute
        assert 'MPLS Label' in output or 'Label' in output or target in output, \
            f"{router}: No MPLS LSP to {target}"
