"""CheckMK check plugins for MikroTik MLAG (multi-chassis link aggregation).

Data: agent module "mlag".
- bridges with an MLAG peer port: "/interface/bridge/monitor once"
  -> mlag-state (connected / connecting / error text), mlag-active-role
- bondings with an mlag-id: "/interface/bonding/monitor once"
  -> active-ports, inactive-ports, lacp-partner-system-id

Services:
- "MLAG <bridge>": state of the connection to the MLAG peer (ICCP) and the
  role of this node (primary/secondary, optionally an expected role).
- "MLAG bond <bond>": active/inactive member ports and LACP partner of a
  dual-connected bond.

Section (one JSON object per line):
    {"type": "bridge", "name": "bridge", "mlag-peer-port": "peer-bond",
     "monitor": {"mlag-state": "connected", "mlag-active-role": "primary"}}
    {"type": "bond", "name": "bond10", "mlag-id": "10", "running": "true",
     "monitor": {"active-ports": "sfp1", "inactive-ports": "",
                 "lacp-partner-system-id": "..."}}

Field names follow the MikroTik MLAG documentation (RouterOS 7). Not yet
verified on MLAG hardware.

Added in mikrotik-rest-api 1.3.0 by Klaus Paulitsch <kp@workitout.at>.

SPDX-License-Identifier: GPL-3.0-only
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
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
)


@dataclass
class Section:
    bridges: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    bonds: dict[str, Mapping[str, Any]] = field(default_factory=dict)


def parse_mikrotik_rest_api_mlag(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        try:
            row = json.loads(line[0])
        except (ValueError, IndexError):
            continue
        if not isinstance(row, dict) or not row.get("name"):
            continue
        if row.get("type") == "bridge":
            section.bridges[row["name"]] = row
        elif row.get("type") == "bond":
            section.bonds[row["name"]] = row
    return section


def _ports(value: Any) -> list[str]:
    """'sfp1,sfp2' / ['sfp1', 'sfp2'] / '' -> list of port names."""
    if isinstance(value, list):
        return [str(p) for p in value if p]
    return [p.strip() for p in str(value or "").split(",") if p.strip()]


# ---------------------------------------------------------------------------
# MLAG peer status per bridge
# ---------------------------------------------------------------------------


def discover_mikrotik_rest_api_mlag(section: Section) -> DiscoveryResult:
    for name in section.bridges:
        yield Service(item=name)


def check_mikrotik_rest_api_mlag(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (row := section.bridges.get(item)) is None:
        return
    mon = row.get("monitor") or {}
    mlag_state = str(mon.get("mlag-state") or "").strip()

    if mlag_state == "connected":
        yield Result(state=State.OK, summary="Peer connected")
    elif mlag_state == "connecting":
        yield Result(
            state=State(params.get("connecting_state", 2)),
            summary="Connecting to peer (peer link down or peer not reachable)",
        )
    elif not mlag_state:
        yield Result(
            state=State(params.get("error_state", 2)),
            summary="No MLAG state reported",
        )
    else:
        yield Result(
            state=State(params.get("error_state", 2)),
            summary=f"MLAG state: {mlag_state}",
        )

    role = str(mon.get("mlag-active-role") or "").strip()
    expected = params.get("expected_role", "any")
    if role:
        if expected in ("primary", "secondary") and role != expected:
            yield Result(
                state=State(params.get("role_mismatch_state", 1)),
                summary=f"Role: {role} (expected {expected})",
            )
        else:
            yield Result(state=State.OK, summary=f"Role: {role}")

    details = [
        f"{label}: {row[key]}"
        for key, label in (
            ("mlag-peer-port", "Peer port"),
            ("mlag-priority", "Priority"),
            ("mlag-heartbeat", "Heartbeat"),
        )
        if row.get(key)
    ] + [
        f"{label}: {mon[key]}"
        for key, label in (("state", "Bridge state"), ("bridge-id", "Bridge ID"))
        if mon.get(key)
    ]
    if details:
        yield Result(state=State.OK, notice="\n".join(details))


agent_section_mikrotik_rest_api_mlag = AgentSection(
    name="mikrotik_rest_api_mlag",
    parse_function=parse_mikrotik_rest_api_mlag,
)

check_plugin_mikrotik_rest_api_mlag = CheckPlugin(
    name="mikrotik_rest_api_mlag",
    service_name="MLAG %s",
    discovery_function=discover_mikrotik_rest_api_mlag,
    check_function=check_mikrotik_rest_api_mlag,
    check_ruleset_name="mikrotik_rest_api_mlag",
    check_default_parameters={
        "connecting_state": 2,
        "error_state": 2,
        "expected_role": "any",
        "role_mismatch_state": 1,
    },
)


# ---------------------------------------------------------------------------
# MLAG bonds
# ---------------------------------------------------------------------------


def discover_mikrotik_rest_api_mlag_bond(section: Section) -> DiscoveryResult:
    for name in section.bonds:
        yield Service(item=name)


def check_mikrotik_rest_api_mlag_bond(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (row := section.bonds.get(item)) is None:
        return
    mon = row.get("monitor") or {}
    active = _ports(mon.get("active-ports"))
    inactive = _ports(mon.get("inactive-ports"))
    running = str(row.get("running", "true")).lower() in ("true", "yes")

    if not running or not active:
        yield Result(
            state=State(params.get("no_active_state", 2)),
            summary="No active member port" + ("" if running else " (bond not running)"),
        )
    else:
        yield Result(state=State.OK, summary=f"Active: {', '.join(active)}")

    if inactive:
        yield Result(
            state=State(params.get("inactive_state", 1)),
            summary=f"Inactive: {', '.join(inactive)}",
        )

    partner = str(mon.get("lacp-partner-system-id") or "").strip()
    if partner and partner not in ("00:00:00:00:00:00", "none"):
        yield Result(state=State.OK, notice=f"LACP partner: {partner}")
    elif str(mon.get("mode") or row.get("mode") or "802.3ad") == "802.3ad":
        yield Result(
            state=State(params.get("no_partner_state", 1)),
            summary="No LACP partner",
        )

    yield Metric("mikrotik_rest_api_mlag_bond_active", len(active))
    details = [
        f"{label}: {row[key]}"
        for key, label in (("mlag-id", "MLAG ID"), ("slaves", "Member ports"), ("mode", "Mode"))
        if row.get(key)
    ]
    if mon.get("lacp-system-id"):
        details.append(f"LACP system ID: {mon['lacp-system-id']}")
    if details:
        yield Result(state=State.OK, notice="\n".join(details))


check_plugin_mikrotik_rest_api_mlag_bond = CheckPlugin(
    name="mikrotik_rest_api_mlag_bond",
    sections=["mikrotik_rest_api_mlag"],
    service_name="MLAG bond %s",
    discovery_function=discover_mikrotik_rest_api_mlag_bond,
    check_function=check_mikrotik_rest_api_mlag_bond,
    check_ruleset_name="mikrotik_rest_api_mlag_bond",
    check_default_parameters={
        "no_active_state": 2,
        "inactive_state": 1,
        "no_partner_state": 1,
    },
)
