"""CheckMK agent-based check plugin for MikroTik network interfaces.

Feeds the RouterOS interface list into Checkmk's standard interface check,
so all the usual rules apply: "Network interface and switch port discovery"
(inventory_if_rules) and "Network interfaces and switch ports" (interfaces) -
bandwidth, errors, discards, speed, state, averaging, interface groups.

Agent section (pipe separated, written by agent module "interfaces"):
    <index>|<name>|<type>|<disabled>|<running>|<dynamic>|<mac>|<speed bit/s>|
    <rx-byte>|<tx-byte>|<rx-packet>|<tx-packet>|<rx-error>|<tx-error>|
    <rx-drop>|<tx-drop>|<comment>

The RouterOS interface type is mapped to the IANA ifType, so the default
discovery behaves like SNMP: ethernet ports that are up are discovered,
VLANs, bridges, bondings, PPP and tunnel interfaces only if their port type
is added to the discovery rule.

Added in mikrotik-rest-api 1.0.0 by Klaus Paulitsch <kp@workitout.at>.
"""

import time
from collections.abc import Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.inventory_interfaces import Interface as InterfaceInv
from cmk.plugins.lib.inventory_interfaces import inventorize_interfaces

Section = Sequence[interfaces.InterfaceWithCounters]

# RouterOS interface type -> IANA ifType. ether, vlan, bridge, loopback and
# WireGuard are verified against the ifType RouterOS reports via SNMP
# (loopback and WireGuard: other(1)), so the same interface discovery rule
# finds the same interfaces as with SNMP.
_IF_TYPES = {
    "ether": "6",           # ethernetCsmacd
    "vlan": "135",          # l2vlan
    "bridge": "209",        # bridge
    "bond": "161",          # ieee8023adLag
    "wlan": "71",           # ieee80211 (legacy wireless driver)
    "wifi": "71",           # new wifi driver
    "wifiwave2": "71",
    "cap": "71",            # CAPsMAN managed radio
    "loopback": "1",        # SNMP reports other(1), not softwareLoopback(24)
    "wg": "1",              # SNMP reports other(1) for WireGuard
    "vrrp": "112",          # virtualIpAddress
    "lte": "1",
    "veth": "1",            # container interface
    "macvlan": "1",
}
_PPP_PREFIXES = ("pppoe-", "pptp-", "l2tp-", "sstp-", "ovpn-", "ppp-")
_TUNNEL_TYPES = ("gre", "ipip", "eoip", "6to4", "vxlan", "vpls", "ipsec")

_FIELDS = 17


def _if_type(ros_type: str) -> str:
    if ros_type in _IF_TYPES:
        return _IF_TYPES[ros_type]
    if ros_type.startswith(_PPP_PREFIXES):
        return "23"  # ppp
    if ros_type.startswith(_TUNNEL_TYPES):
        return "131"  # tunnel
    return "1"  # other


def _int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def parse_mikrotik_rest_api_if(string_table: StringTable) -> Section:
    timestamp = time.time()
    section = []
    for line in string_table:
        if len(line) < _FIELDS:
            continue
        (
            index, name, ros_type, disabled, running, _dynamic, mac, speed,
            rx_byte, tx_byte, rx_packet, tx_packet, rx_error, tx_error,
            rx_drop, tx_drop,
        ) = line[:16]
        comment = "|".join(line[16:])  # in case the agent did not escape
        # admin state only for disabled interfaces: via SNMP Checkmk shows no
        # admin state, so enabled interfaces look exactly the same
        if disabled == "true":
            admin, oper = "2", "2"
        else:
            admin, oper = None, ("1" if running == "true" else "2")
        section.append(
            interfaces.InterfaceWithCounters(
                interfaces.Attributes(
                    index=index,
                    descr=name,
                    # like SNMP ifAlias: the comment, empty without one
                    alias=comment,
                    type=_if_type(ros_type),
                    speed=_int(speed),
                    oper_status=oper,
                    admin_status=admin,
                    phys_address=(
                        interfaces.mac_address_from_hexstring(mac) if ":" in mac else ""
                    ),
                ),
                interfaces.Counters(
                    in_octets=_int(rx_byte),
                    in_ucast=_int(rx_packet),
                    in_err=_int(rx_error),
                    in_disc=_int(rx_drop),
                    out_octets=_int(tx_byte),
                    out_ucast=_int(tx_packet),
                    out_err=_int(tx_error),
                    out_disc=_int(tx_drop),
                ),
                timestamp,
            )
        )
    return section


agent_section_mikrotik_rest_api_if = AgentSection(
    name="mikrotik_rest_api_if",
    parse_function=parse_mikrotik_rest_api_if,
    # a MikroTik host that is also polled via SNMP would otherwise get
    # every "Interface" service twice
    supersedes=["if", "if64"],
)


def discover_mikrotik_rest_api_if(params: Sequence[dict], section: Section) -> DiscoveryResult:
    yield from interfaces.discover_interfaces(params, section)


def check_mikrotik_rest_api_if(item: str, params: dict, section: Section) -> CheckResult:
    yield from interfaces.check_multiple_interfaces(item, params, section)


check_plugin_mikrotik_rest_api_if = CheckPlugin(
    name="mikrotik_rest_api_if",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_mikrotik_rest_api_if,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_mikrotik_rest_api_if,
)


def inventory_mikrotik_rest_api_if(section: Section) -> InventoryResult:
    yield from inventorize_interfaces(
        {},
        (
            InterfaceInv(
                index=iface.attributes.index,
                descr=iface.attributes.descr,
                alias=iface.attributes.alias,
                type=iface.attributes.type,
                speed=int(iface.attributes.speed),
                oper_status=int(iface.attributes.oper_status),
                admin_status=int(iface.attributes.admin_status or 0) or None,
                phys_address=interfaces.render_mac_address(iface.attributes.phys_address),
            )
            for iface in section
        ),
        len(section),
    )


inventory_plugin_mikrotik_rest_api_if = InventoryPlugin(
    name="mikrotik_rest_api_if",
    inventory_function=inventory_mikrotik_rest_api_if,
)
