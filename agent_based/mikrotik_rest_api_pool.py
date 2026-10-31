"""CheckMK check plugin for MikroTik IP pools (DHCP, PPP, hotspot).

Data: /ip/pool (ranges) and /ip/pool/used (counted by the agent), agent
module "pools". One service per pool with used and free addresses.

Section (one JSON object per line):
    {"name": "dhcp_pool0", "ranges": "192.168.88.10-192.168.88.254",
     "next-pool": "none", "used": 42}

Added in mikrotik-rest-api 1.1.0 by Klaus Paulitsch <kp@workitout.at>.
"""

import ipaddress
import json
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

Section = Mapping[str, Mapping[str, Any]]


def parse_mikrotik_rest_api_pool(string_table: StringTable) -> Section:
    section = {}
    for line in string_table:
        try:
            row = json.loads(line[0])
        except (ValueError, IndexError):
            continue
        if isinstance(row, dict) and row.get("name"):
            section[row["name"]] = row
    return section


def pool_size(ranges: str) -> int | None:
    """Number of addresses in a RouterOS ranges string.

    '10.0.0.10-10.0.0.20,10.0.1.0/24,10.0.2.5' -> 11 + 256 + 1
    """
    total = 0
    for part in (p.strip() for p in str(ranges).split(",")):
        if not part:
            continue
        try:
            if "-" in part:
                first, last = (ipaddress.ip_address(x.strip()) for x in part.split("-", 1))
                total += int(last) - int(first) + 1
            elif "/" in part:
                total += ipaddress.ip_network(part, strict=False).num_addresses
            else:
                ipaddress.ip_address(part)
                total += 1
        except ValueError:
            return None
    return total or None


def discover_mikrotik_rest_api_pool(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_mikrotik_rest_api_pool(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (row := section.get(item)) is None:
        return
    used = int(row.get("used", 0))
    size = pool_size(row.get("ranges", ""))
    if not size:
        yield Result(state=State.UNKNOWN, summary=f"Cannot parse ranges {row.get('ranges')!r}")
        return
    free = max(size - used, 0)

    yield from check_levels(
        100.0 * used / size,
        levels_upper=params.get("used_percent_upper"),
        metric_name="mikrotik_rest_api_pool_used_percent",
        render_func=render.percent,
        label="Used",
        boundaries=(0, 100),
    )
    yield Result(state=State.OK, summary=f"{used} of {size} addresses")
    yield from check_levels(
        free,
        levels_lower=params.get("free_lower"),
        metric_name="mikrotik_rest_api_pool_free",
        render_func=lambda v: f"{int(v)}",
        label="Free",
    )
    yield Metric("mikrotik_rest_api_pool_used", used, boundaries=(0, size))
    next_pool = row.get("next-pool")
    if next_pool and next_pool != "none":
        yield Result(state=State.OK, summary=f"Next pool: {next_pool}")
    yield Result(state=State.OK, notice=f"Ranges: {row.get('ranges')}")


agent_section_mikrotik_rest_api_pool = AgentSection(
    name="mikrotik_rest_api_pool",
    parse_function=parse_mikrotik_rest_api_pool,
)

check_plugin_mikrotik_rest_api_pool = CheckPlugin(
    name="mikrotik_rest_api_pool",
    service_name="IP Pool %s",
    discovery_function=discover_mikrotik_rest_api_pool,
    check_function=check_mikrotik_rest_api_pool,
    check_ruleset_name="mikrotik_rest_api_pool",
    check_default_parameters={"used_percent_upper": ("fixed", (80.0, 90.0))},
)
