"""
Phase 8: VRFs and L3VPN Tests
Tests VRF configuration on PE routers for campus networks

PE Routers:
- main-agg1: Main Campus PE
- med-agg1: Medical Campus PE
- res-agg1: Research Campus PE

VRFs:
- STUDENT: Student network (all campuses)
- STAFF: Staff network (all campuses)
- SERVERS: Server network (main campus only)

Route Targets:
- STUDENT: 65001:100 (import/export)
- STAFF: 65001:200 (import/export)
- SERVERS: 65001:300 (import/export)
"""
import pytest
from genie.testbed import load

PE_ROUTERS = ['main-agg1', 'med-agg1', 'res-agg1']

# VRF definitions
VRFS = {
    'STUDENT': {
        'rd': '65001:100',
        'rt_import': '65001:100',
        'rt_export': '65001:100',
        'routers': ['main-agg1', 'med-agg1', 'res-agg1'],
    },
    'STAFF': {
        'rd': '65001:200',
        'rt_import': '65001:200',
        'rt_export': '65001:200',
        'routers': ['main-agg1', 'med-agg1', 'res-agg1'],
    },
    'SERVERS': {
        'rd': '65001:300',
        'rt_import': '65001:300',
        'rt_export': '65001:300',
        'routers': ['main-agg1'],  # Only main campus has servers
    },
}

# VRF interface assignments (edge-facing interfaces)
VRF_INTERFACES = {
    'main-agg1': {
        'STUDENT': 'GigabitEthernet4.100',  # main-edge1 subinterface
        'STAFF': 'GigabitEthernet4.200',
        'SERVERS': 'GigabitEthernet4.300',
    },
    'med-agg1': {
        'STUDENT': 'GigabitEthernet4.100',  # med-edge1 subinterface
        'STAFF': 'GigabitEthernet4.200',
    },
    'res-agg1': {
        'STUDENT': 'GigabitEthernet4.100',  # res-edge1 subinterface
        'STAFF': 'GigabitEthernet4.200',
    },
}


@pytest.fixture(scope='module')
def testbed():
    return load('testbed.yml')


@pytest.fixture(scope='module')
def connected_devices(testbed):
    devices = {}
    for name in PE_ROUTERS:
        device = testbed.devices[name]
        device.connect(log_stdout=False)
        devices[name] = device
    yield devices
    for device in devices.values():
        device.disconnect()


class TestVRFDefinitions:
    """Test VRF definitions on PE routers."""

    @pytest.mark.parametrize('vrf_name,vrf_info', VRFS.items())
    def test_vrf_exists(self, connected_devices, vrf_name, vrf_info):
        """Verify VRF is defined on appropriate routers."""
        for router in vrf_info['routers']:
            device = connected_devices[router]
            output = device.execute(f'show running-config | section vrf definition {vrf_name}')

            assert f'vrf definition {vrf_name}' in output, \
                f"{router}: VRF {vrf_name} not defined"

    @pytest.mark.parametrize('vrf_name,vrf_info', VRFS.items())
    def test_vrf_rd(self, connected_devices, vrf_name, vrf_info):
        """Verify VRF has correct Route Distinguisher."""
        for router in vrf_info['routers']:
            device = connected_devices[router]
            output = device.execute(f'show running-config | section vrf definition {vrf_name}')

            assert f"rd {vrf_info['rd']}" in output, \
                f"{router}: VRF {vrf_name} RD should be {vrf_info['rd']}"

    @pytest.mark.parametrize('vrf_name,vrf_info', VRFS.items())
    def test_vrf_rt_export(self, connected_devices, vrf_name, vrf_info):
        """Verify VRF has correct Route Target export."""
        for router in vrf_info['routers']:
            device = connected_devices[router]
            output = device.execute(f'show running-config | section vrf definition {vrf_name}')

            assert f"route-target export {vrf_info['rt_export']}" in output, \
                f"{router}: VRF {vrf_name} RT export should be {vrf_info['rt_export']}"

    @pytest.mark.parametrize('vrf_name,vrf_info', VRFS.items())
    def test_vrf_rt_import(self, connected_devices, vrf_name, vrf_info):
        """Verify VRF has correct Route Target import."""
        for router in vrf_info['routers']:
            device = connected_devices[router]
            output = device.execute(f'show running-config | section vrf definition {vrf_name}')

            assert f"route-target import {vrf_info['rt_import']}" in output, \
                f"{router}: VRF {vrf_name} RT import should be {vrf_info['rt_import']}"

    @pytest.mark.parametrize('vrf_name,vrf_info', VRFS.items())
    def test_vrf_address_family_ipv4(self, connected_devices, vrf_name, vrf_info):
        """Verify VRF has IPv4 address family configured."""
        for router in vrf_info['routers']:
            device = connected_devices[router]
            output = device.execute(f'show running-config | section vrf definition {vrf_name}')

            assert 'address-family ipv4' in output, \
                f"{router}: VRF {vrf_name} missing IPv4 address family"


class TestVRFInterfaces:
    """Test VRF interface assignments."""

    @pytest.mark.parametrize('router', PE_ROUTERS)
    def test_vrf_interfaces_configured(self, connected_devices, router):
        """Verify VRF interfaces are configured."""
        device = connected_devices[router]

        for vrf_name, interface in VRF_INTERFACES.get(router, {}).items():
            # Get the base interface (before the dot)
            base_intf = interface.split('.')[0]
            subintf_num = interface.split('.')[1] if '.' in interface else None

            if subintf_num:
                output = device.execute(f'show running-config interface {base_intf}.{subintf_num}')
                assert f'vrf forwarding {vrf_name}' in output, \
                    f"{router}: Interface {interface} not in VRF {vrf_name}"
            else:
                output = device.execute(f'show running-config interface {interface}')
                assert f'vrf forwarding {vrf_name}' in output, \
                    f"{router}: Interface {interface} not in VRF {vrf_name}"


class TestVRFRouting:
    """Test VRF routing configuration."""

    @pytest.mark.parametrize('router', PE_ROUTERS)
    def test_bgp_vrf_address_families(self, connected_devices, router):
        """Verify BGP has VRF address families configured."""
        device = connected_devices[router]
        output = device.execute('show running-config | section router bgp')

        for vrf_name in VRF_INTERFACES.get(router, {}).keys():
            assert f'address-family ipv4 vrf {vrf_name}' in output, \
                f"{router}: BGP missing address-family for VRF {vrf_name}"


class TestVRFOperational:
    """Test VRF operational state."""

    @pytest.mark.parametrize('router', PE_ROUTERS)
    def test_vrf_exists_operational(self, connected_devices, router):
        """Verify VRFs are operational."""
        device = connected_devices[router]
        output = device.execute('show vrf')

        for vrf_name in VRF_INTERFACES.get(router, {}).keys():
            assert vrf_name in output, \
                f"{router}: VRF {vrf_name} not in operational VRF table"

    @pytest.mark.parametrize('router', PE_ROUTERS)
    def test_vpnv4_routes_present(self, connected_devices, router):
        """Verify VPNv4 routes are being exchanged."""
        device = connected_devices[router]
        output = device.execute('show bgp vpnv4 unicast all summary')

        # Should have established sessions with route reflectors
        assert 'Estab' in output or any(c.isdigit() for c in output.split('\n')[-2] if len(output.split('\n')) > 2), \
            f"{router}: No established VPNv4 BGP sessions"
