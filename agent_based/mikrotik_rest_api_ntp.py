"""CheckMK check plugin for the NTP client of a MikroTik router.

Data: /system/ntp/client, agent module "ntp". Service "NTP Time":
synchronisation status, offset to the server and stratum.

Section (one JSON object):
    {"enabled": "true", "status": "synchronized", "synced-server": "...",
     "synced-stratum": "2", "system-offset": "-0.104ms", "freq-drift": "..."}

Added in mikrotik-rest-api 1.1.0 by Klaus Paulitsch <kp@workitout.at>.
"""

import json
import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    render,
)

Section = Mapping[str, Any]

# unit -> factor to seconds. The REST API returns the offset as a plain
# number in milliseconds (e.g. "-0.578", confirmed on RouterOS 7), the CLI
# shows it with "ms". Values with a unit are accepted as well.
_OFFSET_UNITS = {"ns": 1e-9, "us": 1e-6, "µs": 1e-6, "ms": 1e-3, "s": 1.0, "": 1e-3}


def parse_mikrotik_rest_api_ntp(string_table: StringTable) -> Section | None:
    for line in string_table:
        try:
            row = json.loads(line[0])
        except (ValueError, IndexError):
            continue
        if isinstance(row, dict):
            return row
    return None


def offset_seconds(text: Any) -> float | None:
    """'-0.104ms' / '123us' / '0.5 s' / '-0.104' -> seconds."""
    match = re.match(r"\s*([-+]?\d+(?:\.\d+)?)\s*(ns|us|µs|ms|s)?\s*$", str(text or ""))
    if not match:
        return None
    return float(match.group(1)) * _OFFSET_UNITS[match.group(2) or ""]


def discover_mikrotik_rest_api_ntp(section: Section) -> DiscoveryResult:
    if str(section.get("enabled", "")).lower() in ("true", "yes"):
        yield Service()


def check_mikrotik_rest_api_ntp(params: Mapping[str, Any], section: Section) -> CheckResult:
    if str(section.get("enabled", "")).lower() not in ("true", "yes"):
        yield Result(state=State(params.get("disabled_state", 1)), summary="NTP client disabled")
        return

    status = section.get("status", "unknown")
    server = section.get("synced-server")
    if status == "synchronized":
        yield Result(
            state=State.OK,
            summary="Synchronized" + (f" with {server}" if server else ""),
        )
    else:
        yield Result(
            state=State(params.get("not_synced_state", 1)),
            summary=f"Status: {status}",
        )

    if (offset := offset_seconds(section.get("system-offset"))) is not None:
        levels = params.get("offset_levels")
        yield from check_levels(
            abs(offset),
            levels_upper=levels,
            render_func=render.timespan,
            label="Offset" + (" (negative)" if offset < 0 else ""),
        )
        # signed value for the graph, same metric as the chrony/ntp checks
        yield Metric("time_offset", offset)

    stratum = section.get("synced-stratum")
    if stratum not in (None, "") and str(stratum).isdigit():
        yield from check_levels(
            int(stratum),
            levels_upper=params.get("stratum_upper"),
            render_func=lambda v: f"{int(v)}",
            label="Stratum",
        )

    section = dict(section)
    drift = str(section.get("freq-drift", ""))
    if drift:
        section["freq-drift-ppm"] = drift if "ppm" in drift.lower() else f"{drift} PPM"
    details = [
        f"{label}: {section[key]}"
        for key, label in (
            ("mode", "Mode"),
            ("servers", "Servers"),
            ("server-dns-names", "Server DNS names"),
            ("vrf", "VRF"),
            ("freq-drift-ppm", "Frequency drift"),
            ("system-offset", "System offset (raw)"),
        )
        if section.get(key)
    ]
    if details:
        yield Result(state=State.OK, notice="\n".join(details))


agent_section_mikrotik_rest_api_ntp = AgentSection(
    name="mikrotik_rest_api_ntp",
    parse_function=parse_mikrotik_rest_api_ntp,
)

check_plugin_mikrotik_rest_api_ntp = CheckPlugin(
    name="mikrotik_rest_api_ntp",
    service_name="NTP Time",
    discovery_function=discover_mikrotik_rest_api_ntp,
    check_function=check_mikrotik_rest_api_ntp,
    check_ruleset_name="mikrotik_rest_api_ntp",
    check_default_parameters={
        "not_synced_state": 1,
        "disabled_state": 1,
        "offset_levels": ("fixed", (0.2, 0.5)),
        "stratum_upper": ("fixed", (10, 15)),
    },
)
