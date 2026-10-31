"""CheckMK check plugin for UPS devices connected to a MikroTik router.

Data: /system/ups and "/system/ups/monitor once" (needs the RouterOS
package ups.npk), agent module "ups". One service per UPS.

Section (one JSON object per line):
    {".id": "*1", "name": "ups", "model": ..., "serial": ...,
     "monitor": {"on-line": "true", "battery-charge": "100", ...}}

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
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
    check_levels,
    render,
)

Section = Mapping[str, Mapping[str, Any]]


def parse_mikrotik_rest_api_ups(string_table: StringTable) -> Section:
    section = {}
    for line in string_table:
        try:
            row = json.loads(line[0])
        except (ValueError, IndexError):
            continue
        if isinstance(row, dict) and (row.get("name") or row.get(".id")):
            section[row.get("name") or row[".id"]] = row
    return section


def _num(value: Any) -> float | None:
    """'100' / '100%' / '27V' / '27.3 V' / '50Hz' -> float."""
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(value or ""))
    return float(match.group(1)) if match else None


def _flag(value: Any) -> bool:
    return str(value).lower() in ("true", "yes")


_UNITS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}


def _seconds(value: Any) -> float | None:
    """'20m' / '1h5m30s' / '00:20:00' -> seconds."""
    text = str(value or "").strip()
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
        return None
    seconds += sum(int(n) * _UNITS[u] for n, u in parts if u != "ms")
    return seconds


def discover_mikrotik_rest_api_ups(section: Section) -> DiscoveryResult:
    for name, row in section.items():
        if not _flag(row.get("disabled")):
            yield Service(item=name)


def check_mikrotik_rest_api_ups(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (row := section.get(item)) is None:
        return
    mon = row.get("monitor") or {}
    if not mon:
        yield Result(
            state=State(params.get("no_data_state", 2)),
            summary="No monitoring data from the UPS (not connected or not supported)",
        )
        return

    # power source
    if _flag(mon.get("on-battery")) or (
        "on-line" in mon and not _flag(mon.get("on-line"))
    ):
        cause = mon.get("transfer-cause")
        yield Result(
            state=State(params.get("on_battery_state", 2)),
            summary="On battery" + (f" ({cause})" if cause else ""),
        )
    else:
        yield Result(state=State.OK, summary="On line power")

    for key, label, param in (
        ("low-battery", "Battery low", "low_battery_state"),
        ("replace-battery", "Replace battery", "replace_battery_state"),
        ("overload", "Output overloaded", "overload_state"),
        ("overloaded-output", "Output overloaded", "overload_state"),
    ):
        if _flag(mon.get(key)):
            default = 2 if key == "low-battery" else 1
            yield Result(state=State(params.get(param, default)), summary=label)

    if (charge := _num(mon.get("battery-charge"))) is not None:
        yield from check_levels(
            charge,
            levels_lower=params.get("battery_charge_lower"),
            metric_name="battery_capacity",
            render_func=render.percent,
            label="Battery charge",
            boundaries=(0, 100),
        )
    if (runtime := _seconds(mon.get("runtime-left"))) is not None:
        yield from check_levels(
            runtime,
            levels_lower=params.get("runtime_lower"),
            metric_name="battery_seconds_remaining",
            render_func=render.timespan,
            label="Runtime left",
        )
    if (load := _num(mon.get("load"))) is not None:
        yield from check_levels(
            load,
            levels_upper=params.get("load_upper"),
            metric_name="output_load",
            render_func=render.percent,
            label="Load",
            boundaries=(0, 100),
        )
    if (temp := _num(mon.get("temperature"))) is not None:
        yield from check_levels(
            temp,
            levels_upper=params.get("temperature_upper"),
            metric_name="temp",
            render_func=lambda v: f"{v:.1f} °C",
            label="Temperature",
        )
    for key, metric, label in (
        ("line-voltage", "in_voltage", "Input voltage"),
        ("output-voltage", "out_voltage", "Output voltage"),
        ("battery-voltage", "battery_voltage", "Battery voltage"),
    ):
        if (volt := _num(mon.get(key))) is not None:
            yield from check_levels(
                volt, metric_name=metric, render_func=lambda v: f"{v:.1f} V",
                label=label, notice_only=True,
            )
    if (freq := _num(mon.get("frequency"))) is not None:
        yield from check_levels(
            freq, metric_name="in_freq", render_func=lambda v: f"{v:.1f} Hz",
            label="Frequency", notice_only=True,
        )
    details = [f"{k}: {row[k]}" for k in ("model", "serial", "version") if row.get(k)]
    if details:
        yield Result(state=State.OK, notice=", ".join(details))


agent_section_mikrotik_rest_api_ups = AgentSection(
    name="mikrotik_rest_api_ups",
    parse_function=parse_mikrotik_rest_api_ups,
)

check_plugin_mikrotik_rest_api_ups = CheckPlugin(
    name="mikrotik_rest_api_ups",
    service_name="UPS %s",
    discovery_function=discover_mikrotik_rest_api_ups,
    check_function=check_mikrotik_rest_api_ups,
    check_ruleset_name="mikrotik_rest_api_ups",
    check_default_parameters={
        "on_battery_state": 2,
        "low_battery_state": 2,
        "replace_battery_state": 1,
        "overload_state": 1,
        "no_data_state": 2,
        "battery_charge_lower": ("fixed", (50.0, 25.0)),
        "runtime_lower": ("fixed", (600.0, 300.0)),
        "load_upper": ("fixed", (80.0, 90.0)),
    },
)


def inventory_mikrotik_rest_api_ups(section: Section) -> InventoryResult:
    for name, row in section.items():
        yield TableRow(
            path=["hardware", "components", "psus"],
            key_columns={"index": name},
            inventory_columns={
                "name": name,
                "description": "UPS",
                "manufacturer": "",
                "model": row.get("model", ""),
                "serial": row.get("serial", ""),
                "software": row.get("version", ""),
            },
        )


inventory_plugin_mikrotik_rest_api_ups = InventoryPlugin(
    name="mikrotik_rest_api_ups",
    inventory_function=inventory_mikrotik_rest_api_ups,
)
