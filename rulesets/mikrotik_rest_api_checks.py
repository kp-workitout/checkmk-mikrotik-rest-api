"""CheckMK check parameter rule specs for MikroTik checks.

Replaces the legacy wato/mikrotik.py using the cmk.rulesets.v1 API, which is
required for CheckMK 2.4+ (the legacy cmk.gui.plugins.wato API was removed in
2.5).

Each rule_spec_* variable is auto-discovered by CheckMK via entry_point_prefixes().
"""

# DefaultValue(False/True) are positional arguments required by CheckMK's
# form spec API — suppressing FBT003 (boolean positional value) project-wide.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    Float,
    Percentage,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    List,
    ServiceState,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    migrate_to_integer_simple_levels,
    migrate_to_upper_integer_levels,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)

# ---------------------------------------------------------------------------
# Migration helpers — strip keys removed in v4.0.0
# ---------------------------------------------------------------------------

def _migrate_fan_params(value: object) -> dict[str, object]:
    """Remove 'output_metrics' stored by the legacy WATO fan rule."""
    if not isinstance(value, dict):
        return {}
    result = dict(value)
    result.pop("output_metrics", None)
    return result


def _migrate_power_params(value: object) -> dict[str, object]:
    """Remove 'psu_count' stored by the legacy WATO power rule.

    Power monitoring was redesigned in v4.0.0 to create one service per PSU,
    so the expected-PSU-count check no longer makes sense.
    """
    if not isinstance(value, dict):
        return {}
    result = dict(value)
    result.pop("psu_count", None)
    return result


# ---------------------------------------------------------------------------
# Fan speed
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_fan = CheckParameters(
    name="mikrotik_rest_api_fan",
    title=Title("MikroTik REST API: Fan"),
    topic=Topic.ENVIRONMENTAL,
    # One service per fan — the item is the fan name reported by the agent.
    condition=HostAndItemCondition(item_title=Title("Fan name")),
    parameter_form=lambda: Dictionary(
        migrate=_migrate_fan_params,
        help_text=Help("Activate special agent MikroTik RouterOS (mikrotik-rest-api) to use this."),
        elements={
            "lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower fan speed thresholds"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="rpm"),
                    prefill_fixed_levels=DefaultValue((2000, 1000)),
                    # Converts data stored by the legacy Tuple valuespec so
                    # existing rules survive the upgrade to 2.5.
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    ),
)

# ---------------------------------------------------------------------------
# RouterOS board / version
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_board = CheckParameters(
    name="mikrotik_rest_api_board",
    title=Title("MikroTik REST API: RouterOS Info"),
    topic=Topic.NETWORKING,
    # Single service per host — no item.
    condition=HostCondition(),
    parameter_form=lambda: Dictionary(
        help_text=Help("Activate special agent MikroTik RouterOS (mikrotik-rest-api) to use this."),
        elements={
            "min_version": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Minimum version"),
                    help_text=Help(
                        "Check goes WARN if the installed RouterOS version is "
                        "lower than this value. Format: Major.Minor or "
                        "Major.Minor.Patch (e.g. 7.14).",
                    ),
                    prefill=DefaultValue("0.0"),
                ),
            ),
            "firmware_upgrade_pending": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State if RouterBOOT firmware upgrade is pending"),
                    help_text=Help(
                        "Applies when /system/routerboard reports an "
                        "upgrade-firmware higher than current-firmware. "
                        "Apply with /system/routerboard upgrade and a reboot. "
                        "Requires agent module 'RouterOS Board Info'.",
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    ),
)

# ---------------------------------------------------------------------------
# File age
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_file = CheckParameters(
    name="mikrotik_rest_api_file",
    title=Title("MikroTik REST API: File Age"),
    topic=Topic.NETWORKING,
    # One service per monitored file — the item is the file name.
    condition=HostAndItemCondition(item_title=Title("File name")),
    parameter_form=lambda: Dictionary(
        help_text=Help("Activate special agent MikroTik RouterOS (mikrotik-rest-api) to use this."),
        elements={
            "file_age": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximum age of file"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ],
                    ),
                    # Defaults: warn after 25 h (90000 s), crit after 49 h (176400 s).
                    prefill_fixed_levels=DefaultValue((90000.0, 176400.0)),
                    # Converts data stored by the legacy Age Tuple valuespec.
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "pattern": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Time pattern for creation-time field"),
                    help_text=Help(
                        "strptime format code matching the creation-time string "
                        "returned by the API. "
                        "RouterOS v7: %%b/%%d/%%Y %%H:%%M:%%S  "
                        "RouterOS v8: %%Y-%%m-%%d %%H:%%M:%%S  "
                        "Leave empty for autodetection.",
                    ),
                    prefill=DefaultValue(""),
                ),
            ),
        },
    ),
)

# ---------------------------------------------------------------------------
# Power supply metrics (per PSU)
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_power = CheckParameters(
    name="mikrotik_rest_api_power",
    title=Title("MikroTik REST API: Power Supply Metrics"),
    topic=Topic.ENVIRONMENTAL,
    # One service per PSU — the item is the PSU name (e.g. PSU1, PSU2).
    condition=HostAndItemCondition(item_title=Title("PSU name")),
    parameter_form=lambda: Dictionary(
        migrate=_migrate_power_params,
        help_text=Help("Activate special agent MikroTik RouterOS (mikrotik-rest-api) to use this."),
        elements={
            "crit_voltage": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Critical voltage threshold"),
                    help_text=Help(
                        "Go CRIT if measured voltage drops below this value. "
                        "Typical MikroTik supply voltages are 12V, 24V, or 48V.",
                    ),
                    unit_symbol="V",
                    prefill=DefaultValue(10),
                ),
            ),
        },
    ),
)

# ---------------------------------------------------------------------------
# PSU state (presence / ok / fail)
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_psu = CheckParameters(
    name="mikrotik_rest_api_psu",
    title=Title("MikroTik REST API: PSU State"),
    topic=Topic.ENVIRONMENTAL,
    # One service per PSU — the item is the PSU name reported by the agent.
    condition=HostAndItemCondition(item_title=Title("PSU name")),
    parameter_form=lambda: Dictionary(
        help_text=Help("Activate special agent MikroTik RouterOS (mikrotik-rest-api) to use this."),
        elements={
            "ok_states": DictElement(
                required=False,
                parameter_form=List(
                    title=Title("States considered OK"),
                    help_text=Help(
                        "RouterOS reports PSU state as a string such as 'ok'. "
                        "Any state not in this list results in CRIT.",
                    ),
                    element_template=String(),
                ),
            ),
        },
    ),
)

# ---------------------------------------------------------------------------
# IPsec tunnels
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_ipsec = CheckParameters(
    name="mikrotik_rest_api_ipsec",
    title=Title("MikroTik REST API: IPsec"),
    topic=Topic.NETWORKING,
    # One service per IPsec peer — the item is the tunnel identifier.
    condition=HostAndItemCondition(item_title=Title("IPsec tunnel")),
    parameter_form=lambda: Dictionary(
        help_text=Help("Activate special agent MikroTik RouterOS (mikrotik-rest-api) to use this."),
        elements={
            "ok_states": DictElement(
                required=False,
                parameter_form=List(
                    title=Title("Security Association states considered OK"),
                    help_text=Help(
                        "Any SA state not in this list will result in a WARN. "
                        "RouterOS reports states such as: mature, dying, dead, larval.",
                    ),
                    element_template=String(),
                ),
            ),
        },
    ),
)

# ---------------------------------------------------------------------------
# WiFi per SSID
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_wifi = CheckParameters(
    name="mikrotik_rest_api_wifi",
    title=Title("MikroTik REST API: WiFi"),
    topic=Topic.NETWORKING,
    # One service per SSID - on a CAPsMAN controller over all managed CAPs.
    condition=HostAndItemCondition(item_title=Title("SSID")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "Activate special agent MikroTik RouterOS (mikrotik-rest-api) with the module 'WiFi' to use this.",
        ),
        elements={
            "clients_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for connected clients"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((50, 100)),
                ),
            ),
            "clients_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for connected clients"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((1, 0)),
                ),
            ),
            "signal_avg_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for the average client signal"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="dBm"),
                    prefill_fixed_levels=DefaultValue((-70, -80)),
                ),
            ),
            "signal_min_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for the weakest client signal"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="dBm"),
                    prefill_fixed_levels=DefaultValue((-80, -90)),
                ),
            ),
            "interface_down_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State if a radio of the SSID is down"),
                    help_text=Help(
                        "On a CAPsMAN controller a radio is down when its access "
                        "point lost the connection to the controller.",
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    ),
)


# ---------------------------------------------------------------------------
# mikrotik-rest-api 1.1.0 (Klaus Paulitsch): UPS, IP pools, NTP, WireGuard
# ---------------------------------------------------------------------------

def _state(title: str, default: ServiceState, help_text: str | None = None) -> DictElement:
    return DictElement(
        required=False,
        parameter_form=ServiceState(
            title=Title(title),
            help_text=Help(help_text) if help_text else None,
            prefill=DefaultValue(default),
        ),
    )


def _minutes_levels(title: str, warn: float, crit: float, direction: LevelDirection) -> DictElement:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=Title(title),
            level_direction=direction,
            form_spec_template=TimeSpan(
                displayed_magnitudes=[
                    TimeMagnitude.HOUR, TimeMagnitude.MINUTE, TimeMagnitude.SECOND,
                ],
            ),
            prefill_fixed_levels=DefaultValue((warn, crit)),
        ),
    )


rule_spec_mikrotik_rest_api_ups = CheckParameters(
    name="mikrotik_rest_api_ups",
    title=Title("MikroTik REST API: UPS"),
    topic=Topic.ENVIRONMENTAL,
    condition=HostAndItemCondition(item_title=Title("UPS name")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "UPS connected to the MikroTik router (/system/ups, package ups.npk). "
            "Activate the module 'UPS' in the special agent rule.",
        ),
        elements={
            "on_battery_state": _state("State when running on battery", ServiceState.CRIT),
            "low_battery_state": _state("State when the battery is low", ServiceState.CRIT),
            "replace_battery_state": _state("State when the battery needs replacement", ServiceState.WARN),
            "overload_state": _state("State when the output is overloaded", ServiceState.WARN),
            "no_data_state": _state("State when the UPS delivers no data", ServiceState.CRIT),
            "battery_charge_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for the battery charge"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((50.0, 25.0)),
                ),
            ),
            "runtime_lower": _minutes_levels(
                "Lower levels for the remaining runtime", 600.0, 300.0, LevelDirection.LOWER,
            ),
            "load_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the output load"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                ),
            ),
            "temperature_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the temperature"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="°C"),
                    prefill_fixed_levels=DefaultValue((40.0, 50.0)),
                ),
            ),
        },
    ),
)


rule_spec_mikrotik_rest_api_pool = CheckParameters(
    name="mikrotik_rest_api_pool",
    title=Title("MikroTik REST API: IP pools"),
    topic=Topic.NETWORKING,
    condition=HostAndItemCondition(item_title=Title("Pool name")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "Usage of the IP pools (/ip/pool, /ip/pool/used) used by DHCP, PPP "
            "or hotspot. Activate the module 'IP pools' in the special agent rule.",
        ),
        elements={
            "used_percent_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for used addresses in percent"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                ),
            ),
            "free_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for free addresses"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((10, 5)),
                ),
            ),
        },
    ),
)


rule_spec_mikrotik_rest_api_ntp = CheckParameters(
    name="mikrotik_rest_api_ntp",
    title=Title("MikroTik REST API: NTP client"),
    topic=Topic.OPERATING_SYSTEM,
    condition=HostCondition(),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "NTP client of the MikroTik router (/system/ntp/client). Activate "
            "the module 'NTP client' in the special agent rule.",
        ),
        elements={
            "not_synced_state": _state("State if not synchronized", ServiceState.WARN),
            "disabled_state": _state("State if the NTP client is disabled", ServiceState.WARN),
            "offset_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the absolute time offset"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND],
                    ),
                    prefill_fixed_levels=DefaultValue((0.2, 0.5)),
                ),
            ),
            "stratum_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the stratum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((10, 15)),
                ),
            ),
        },
    ),
)


rule_spec_mikrotik_rest_api_wireguard = CheckParameters(
    name="mikrotik_rest_api_wireguard",
    title=Title("MikroTik REST API: WireGuard peers"),
    topic=Topic.NETWORKING,
    condition=HostAndItemCondition(item_title=Title("Interface and peer")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "WireGuard peers (/interface/wireguard/peers). A peer counts as "
            "site-to-site when endpoint address and persistent keepalive are "
            "configured and it is not a responder - its handshake is renewed "
            "about every 2 minutes. All other peers count as dial-in (road "
            "warriors), their handshake legitimately gets old when idle. "
            "Activate the module 'WireGuard peers' in the special agent rule.",
        ),
        elements={
            "handshake_initiator": _minutes_levels(
                "Site-to-site peers: upper levels for the time since the last handshake",
                300.0, 900.0, LevelDirection.UPPER,
            ),
            "handshake_responder": _minutes_levels(
                "Dial-in peers: upper levels for the time since the last handshake",
                86400.0, 604800.0, LevelDirection.UPPER,
            ),
            "never_state_initiator": _state(
                "Site-to-site peers: state if there was no handshake yet", ServiceState.CRIT,
            ),
            "never_state_responder": _state(
                "Dial-in peers: state if there was no handshake yet", ServiceState.OK,
            ),
            "disabled_state": _state("State if the peer is disabled", ServiceState.WARN),
        },
    ),
)


# ---------------------------------------------------------------------------
# OSPF neighbors and CHR license (rule sets the check plugins referenced but
# the original package never defined)
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_ospf = CheckParameters(
    name="mikrotik_rest_api_ospf",
    title=Title("MikroTik REST API: OSPF neighbors"),
    topic=Topic.NETWORKING,
    condition=HostAndItemCondition(item_title=Title("Router ID of the neighbor")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "OSPF neighbor states (/routing/ospf/neighbor). A neighbor in one of "
            "the listed states is OK, Down is CRIT, any other state WARN. "
            "Activate the module 'OSPF Neighbors' in the special agent rule.",
        ),
        elements={
            "ok_states": DictElement(
                required=False,
                parameter_form=List(
                    title=Title("States considered OK"),
                    help_text=Help(
                        "Default without this option: Full, TwoWay, 2-Way.",
                    ),
                    element_template=String(),
                ),
            ),
        },
    ),
)


rule_spec_mikrotik_rest_api_license = CheckParameters(
    name="mikrotik_rest_api_license",
    title=Title("MikroTik REST API: License (CHR)"),
    topic=Topic.OPERATING_SYSTEM,
    condition=HostCondition(),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "License expiry of a Cloud Hosted Router (/system/license). Activate "
            "the module 'License Key (CHR)' in the special agent rule.",
        ),
        elements={
            "time_remaining": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for the time until the license expires"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR],
                    ),
                    prefill_fixed_levels=DefaultValue((1209600.0, 259200.0)),
                ),
            ),
            "pattern": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Time pattern of deadline-at / next-renewal-at"),
                    help_text=Help(
                        "Python strptime pattern. Leave empty to detect "
                        "'%b/%d/%Y %H:%M:%S' or '%Y-%m-%d %H:%M:%S' automatically.",
                    ),
                ),
            ),
        },
    ),
)


rule_spec_mikrotik_rest_api_bad_blocks = CheckParameters(
    name="mikrotik_rest_api_bad_blocks",
    title=Title("MikroTik REST API: NAND bad blocks"),
    topic=Topic.OPERATING_SYSTEM,
    condition=HostCondition(),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "Share of bad blocks of the NAND flash (bad-blocks of /system/resource). "
            "A small share is normal for NAND flash. Module 'RouterOS Info, CPU, "
            "memory, system disk, uptime' of the special agent rule.",
        ),
        elements={
            "levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for bad blocks"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((2.0, 5.0)),
                ),
            ),
        },
    ),
)


# ---------------------------------------------------------------------------
# MLAG (mikrotik-rest-api 1.3.0)
# ---------------------------------------------------------------------------

rule_spec_mikrotik_rest_api_mlag = CheckParameters(
    name="mikrotik_rest_api_mlag",
    title=Title("MikroTik REST API: MLAG peer"),
    topic=Topic.NETWORKING,
    condition=HostAndItemCondition(item_title=Title("Bridge name")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "State of the MLAG peer connection (ICCP) of a bridge with an MLAG "
            "peer port, and the role of this node. Activate the module 'MLAG' "
            "in the special agent rule.",
        ),
        elements={
            "connecting_state": _state(
                "State while connecting to the peer (peer link down)", ServiceState.CRIT,
            ),
            "error_state": _state(
                "State for any other MLAG state (error text, no state)", ServiceState.CRIT,
            ),
            "expected_role": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Expected role of this node"),
                    help_text=Help(
                        "Set primary or secondary to be alerted when the roles "
                        "changed, e.g. after a reboot or failure of the primary.",
                    ),
                    prefill=DefaultValue("any"),
                    elements=[
                        SingleChoiceElement(name="any", title=Title("Any role")),
                        SingleChoiceElement(name="primary", title=Title("Primary")),
                        SingleChoiceElement(name="secondary", title=Title("Secondary")),
                    ],
                ),
            ),
            "role_mismatch_state": _state(
                "State if the role differs from the expected role", ServiceState.WARN,
            ),
        },
    ),
)


rule_spec_mikrotik_rest_api_mlag_bond = CheckParameters(
    name="mikrotik_rest_api_mlag_bond",
    title=Title("MikroTik REST API: MLAG bonds"),
    topic=Topic.NETWORKING,
    condition=HostAndItemCondition(item_title=Title("Bond name")),
    parameter_form=lambda: Dictionary(
        help_text=Help(
            "Member ports and LACP partner of bonds with an mlag-id. Activate "
            "the module 'MLAG' in the special agent rule.",
        ),
        elements={
            "no_active_state": _state(
                "State if no member port is active", ServiceState.CRIT,
            ),
            "inactive_state": _state(
                "State if member ports are inactive", ServiceState.WARN,
            ),
            "no_partner_state": _state(
                "State if no LACP partner is seen (802.3ad)", ServiceState.WARN,
            ),
        },
    ),
)
