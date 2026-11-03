"""CheckMK rule spec for the MikroTik RouterOS special agent (REST API only).

mikrotik-rest-api 1.0.0 by Klaus Paulitsch, based on mikrotik 4.2.0 by
Tony Boston. Uses the cmk.rulesets.v1 API (CheckMK 2.4+).
"""

# DefaultValue(False/True) are positional arguments required by CheckMK's
# form spec API — suppressing FBT003 (boolean positional value) project-wide.
# ruff: noqa: FBT003

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    """Build the configuration form shown in CheckMK's Setup UI for this agent."""
    return Dictionary(
        help_text=Help(
            "Collects data from a MikroTik RouterOS device via the RouterOS REST "
            "API (RouterOS 7.1 or later). On the device the service www-ssl "
            "(HTTPS) or www (HTTP, RouterOS 7.9 or later) must be enabled, the "
            "user needs a group with the policies read and api.",
        ),
        elements={
            # ------------------------------------------------------------------
            # Credentials
            # ------------------------------------------------------------------
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(title=Title("Password")),
            ),
            # ------------------------------------------------------------------
            # Connection options
            # ------------------------------------------------------------------
            "ssl_mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    prefill=DefaultValue("ssl"),
                    elements=[
                        SingleChoiceElement(
                            name="ssl",
                            title=Title("HTTPS — verify server certificate"),
                        ),
                        SingleChoiceElement(
                            name="ssl_skip",
                            title=Title("HTTPS — do not validate certificate (self-signed)"),
                        ),
                        SingleChoiceElement(
                            name="no_ssl",
                            title=Title("HTTP — unencrypted, RouterOS 7.9+ (not recommended)"),
                        ),
                    ],
                ),
            ),
            "connect": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("TCP port"),
                    help_text=Help(
                        "Port of the www-ssl or www service. Without this option "
                        "443 (HTTPS) or 80 (HTTP) is used.",
                    ),
                    prefill=DefaultValue(443),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=65535),
                    ),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Timeout per request"),
                    unit_symbol="s",
                    prefill=DefaultValue(15),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=120),
                    ),
                ),
            ),
            # ------------------------------------------------------------------
            # Modules — each bool maps to a --modules argument in the agent
            # ------------------------------------------------------------------
            "infos": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Retrieve information about"),
                    elements={
                        "bgp": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("BGP Sessions"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "ospf": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("OSPF Neighbors"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "vrrp": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("VRRP Info"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "health": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("RouterOS Health"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "board": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("RouterOS Info, CPU, memory, system disk, uptime"),
                                help_text=Help(
                                    "RouterOS version, board, serial and firmware (service "
                                    "RouterOS Info, HW/SW inventory) plus the services CPU "
                                    "utilization, Memory, Filesystem system disk and Uptime. "
                                    "Levels via the standard rules \"CPU utilization for simple "
                                    "devices\", \"Main memory usage (Unix / other devices)\", "
                                    "\"File systems (used space and growth)\" and \"Uptime "
                                    "since last reboot\". Memory and Uptime are Checkmk's own "
                                    "checks, the same as via SNMP; these services take "
                                    "precedence over the SNMP ones on hosts polled via both.",
                                ),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "ipsec": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("IPsec"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "file": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("Local File Age"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "license": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("License Key (CHR)"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        # required=False: rules stored before 4.2.0 lack it
                        "wifi": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("WiFi clients and radios (also CAPsMAN)"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "ups": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("UPS (/system/ups, needs package ups.npk)"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "pools": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("IP pools (usage of DHCP/PPP pools)"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "ntp": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("NTP client"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "wireguard": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("WireGuard peers"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "mlag": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("MLAG (peer status of the bridge, MLAG bonds)"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        # optional module
                        "interfaces": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("Network interfaces (traffic, errors, state, speed)"),
                                help_text=Help(
                                    "Creates the standard Interface services. Discovery "
                                    "and levels use the rules \"Network interface and "
                                    "switch port discovery\" and \"Network interfaces and "
                                    "switch ports\". By default only ethernet ports that "
                                    "are up are discovered; add port types there for "
                                    "VLAN, bridge, bonding, PPP or tunnel interfaces.",
                                ),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        # Firewall is a nested dict because it has a sub-option
                        # (show-disabled) beyond a simple enabled/disabled flag.
                        "firewall": DictElement(
                            required=False,
                            parameter_form=Dictionary(
                                title=Title("Firewall Rules"),
                                elements={
                                    "enabled": DictElement(
                                        required=False,
                                        parameter_form=BooleanChoice(
                                            title=Title("Enable firewall monitoring"),
                                            prefill=DefaultValue(False),
                                        ),
                                    ),
                                    "show_disabled": DictElement(
                                        required=False,
                                        parameter_form=BooleanChoice(
                                            title=Title("Show disabled rules"),
                                            prefill=DefaultValue(False),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
        },
    )


# Prefix rule_spec_ is required so CheckMK auto-discovers this via
# entry_point_prefixes() at package load time.
rule_spec_special_agent_mikrotik_rest_api = SpecialAgent(
    name="mikrotik_rest_api",
    title=Title("MikroTik RouterOS (mikrotik-rest-api)"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
)
