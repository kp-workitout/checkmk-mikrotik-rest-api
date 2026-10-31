"""CheckMK check plugin for MikroTik WireGuard peers.

Data: /interface/wireguard/peers, agent module "wireguard" (private and
preshared keys are never collected). One service per peer: time since the
last handshake, current endpoint and traffic.

Peers are told apart by their role:
- site-to-site: endpoint-address and persistent-keepalive configured and
  not "responder". The keepalive renews the handshake about every 2
  minutes, so levels on the handshake age apply (default WARN 5 min,
  CRIT 15 min).
- dial-in: everything else (road warriors, peers without keepalive whose
  handshake legitimately gets old when idle). No levels by default.

Section (one JSON object per line):
    {"interface": "wg1", "name": "peer1", "comment": "Filiale Graz",
     "public-key": "...", "endpoint-address": "...", "last-handshake": "1m5s",
     "rx": "123", "tx": "456", "disabled": "false", ...}

Added in mikrotik-rest-api 1.1.0 by Klaus Paulitsch <kp@workitout.at>.
"""

import json
import re
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    GetRateError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    get_rate,
    get_value_store,
    render,
)

Section = Mapping[str, Mapping[str, Any]]

_UNITS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}


def peer_item(row: Mapping[str, Any]) -> str:
    """'<interface> <comment | name | first 8 chars of the public key>'."""
    label = (
        row.get("comment")
        or row.get("name")
        or (row.get("public-key") or "")[:8]
        or row.get(".id", "?")
    )
    return f"{row.get('interface', '?')} {label}".strip()


def parse_mikrotik_rest_api_wireguard(string_table: StringTable) -> Section:
    section: dict[str, Mapping[str, Any]] = {}
    for line in string_table:
        try:
            row = json.loads(line[0])
        except (ValueError, IndexError):
            continue
        if not isinstance(row, dict):
            continue
        item = peer_item(row)
        if item in section:  # same comment twice: make it unique
            item = f"{item} {(row.get('public-key') or row.get('.id', ''))[:8]}"
        section[item] = row
    return section


def handshake_age(text: Any) -> float | None:
    """'1m5s' / '2h3m' / '1d02:03:04' / '00:01:05' -> seconds, None if never."""
    text = str(text or "").strip()
    if not text:
        return None
    seconds = 0.0
    clock = re.search(r"(\d+):(\d{2}):(\d{2})$", text)
    if clock:
        h, m, s = (int(x) for x in clock.groups())
        seconds += h * 3600 + m * 60 + s
        text = text[: clock.start()]
    parts = re.findall(r"(\d+)(ms|[wdhms])", text)
    if not parts and not clock:
        try:
            return float(text)  # plain seconds
        except ValueError:
            return None
    seconds += sum(int(n) * _UNITS[u] for n, u in parts if u != "ms")
    return seconds


def is_initiator(row: Mapping[str, Any]) -> bool:
    """Site-to-site peer: endpoint and keepalive configured, not a responder."""
    keepalive = handshake_age(row.get("persistent-keepalive"))
    return (
        bool(row.get("endpoint-address"))
        and bool(keepalive)
        and str(row.get("responder", "false")).lower() not in ("true", "yes")
    )


def discover_mikrotik_rest_api_wireguard(section: Section) -> DiscoveryResult:
    for item, row in section.items():
        if str(row.get("disabled", "false")).lower() not in ("true", "yes"):
            yield Service(item=item)


def check_mikrotik_rest_api_wireguard(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (row := section.get(item)) is None:
        return
    if str(row.get("disabled", "false")).lower() in ("true", "yes"):
        yield Result(state=State(params.get("disabled_state", 1)), summary="Peer disabled")
        return

    initiator = is_initiator(row)
    levels = params.get("handshake_initiator" if initiator else "handshake_responder")
    age = handshake_age(row.get("last-handshake"))

    if age is None:
        state = State(
            params.get("never_state_initiator", 2) if initiator
            else params.get("never_state_responder", 0)
        )
        yield Result(state=state, summary="No handshake yet")
    else:
        yield from check_levels(
            age,
            levels_upper=levels,
            metric_name="mikrotik_rest_api_wg_handshake_age",
            render_func=render.timespan,
            label="Last handshake",
        )

    endpoint = row.get("current-endpoint-address")
    if endpoint:
        port = row.get("current-endpoint-port")
        yield Result(state=State.OK, summary=f"Endpoint: {endpoint}" + (f":{port}" if port else ""))

    now = time.time()
    value_store = get_value_store()
    for key, metric, label in (("rx", "if_in_bps", "In"), ("tx", "if_out_bps", "Out")):
        try:
            counter = int(row.get(key, ""))
        except ValueError:
            continue
        try:
            rate = get_rate(value_store, f"wg.{key}", now, counter, raise_overflow=True)
        except GetRateError:
            continue
        yield Result(state=State.OK, notice=f"{label}: {render.networkbandwidth(rate)}")
        yield Metric(metric, rate * 8)

    details = [
        f"Role: {'site-to-site (levels for site-to-site peers)' if initiator else 'dial-in (levels for dial-in peers)'}",
    ] + [
        f"{label}: {row[key]}"
        for key, label in (
            ("name", "Name"),
            ("endpoint-address", "Configured endpoint"),
            ("allowed-address", "Allowed addresses"),
            ("persistent-keepalive", "Persistent keepalive"),
            ("public-key", "Public key"),
        )
        if row.get(key)
    ]
    yield Result(state=State.OK, notice="\n".join(details))


agent_section_mikrotik_rest_api_wireguard = AgentSection(
    name="mikrotik_rest_api_wireguard",
    parse_function=parse_mikrotik_rest_api_wireguard,
)

check_plugin_mikrotik_rest_api_wireguard = CheckPlugin(
    name="mikrotik_rest_api_wireguard",
    service_name="WireGuard %s",
    discovery_function=discover_mikrotik_rest_api_wireguard,
    check_function=check_mikrotik_rest_api_wireguard,
    check_ruleset_name="mikrotik_rest_api_wireguard",
    check_default_parameters={
        "handshake_initiator": ("fixed", (300.0, 900.0)),
        "handshake_responder": ("no_levels", None),
        "never_state_initiator": 2,
        "never_state_responder": 0,
        "disabled_state": 1,
    },
)
