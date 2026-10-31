"""CheckMK check plugins for MikroTik system resources.

CPU utilization, memory, system disk and uptime, all read from
/system/resource (agent module "board", section mikrotik_rest_api_board).
The checks use the standard Checkmk libraries and rule sets, so they look
and behave like the CPU, memory, filesystem and uptime services of any other
host:

    CPU utilization       -> CPU utilization for simple devices
    Memory                -> Main memory usage of simple devices with single services
    Filesystem system disk -> File systems (used space and growth)
    Uptime                -> Uptime since last reboot

Added in mikrotik-rest-api 1.0.0 by Klaus Paulitsch <kp@workitout.at>.
"""

import re
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    check_levels,
    get_value_store,
    render,
)
from cmk.plugins.lib import uptime
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS, df_check_filesystem_single

Section = Mapping[str, str]

SYSTEM_DISK = "system disk"


def _percent(value: str | None) -> float | None:
    """'0.1' / '0.1%' -> 0.1 (RouterOS reports bad blocks in percent)."""
    match = re.match(r"\s*(\d+(?:\.\d+)?)", str(value or ""))
    return float(match.group(1)) if match else None


def _number(section: Section, key: str) -> float | None:
    """/system/resource values are plain numbers (bytes, percent, MHz)."""
    try:
        return float(section[key])
    except (KeyError, ValueError):
        return None


# ---------------------------------------------------------------------------
# CPU utilization
# ---------------------------------------------------------------------------


def discover_mikrotik_rest_api_cpu(section: Section) -> DiscoveryResult:
    if _number(section, "cpu-load") is not None:
        yield Service()


def check_mikrotik_rest_api_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    if (util := _number(section, "cpu-load")) is None:
        return
    yield from check_cpu_util(
        util=util,
        params=params,
        this_time=time.time(),
        value_store=get_value_store(),
    )
    cores = section.get("cpu-count")
    if section.get("cpu") or cores:
        yield Result(
            state=State.OK,
            notice=f"CPU: {section.get('cpu', 'unknown')}"
            + (f", {cores} cores" if cores else "")
            + (f", {section['cpu-frequency']} MHz" if section.get("cpu-frequency") else ""),
        )


check_plugin_mikrotik_rest_api_cpu = CheckPlugin(
    name="mikrotik_rest_api_cpu",
    sections=["mikrotik_rest_api_board"],
    service_name="CPU utilization",
    discovery_function=discover_mikrotik_rest_api_cpu,
    check_function=check_mikrotik_rest_api_cpu,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={"util": (90.0, 95.0)},
)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


def discover_mikrotik_rest_api_mem(section: Section) -> DiscoveryResult:
    if _number(section, "total-memory") and _number(section, "free-memory") is not None:
        yield Service()


def check_mikrotik_rest_api_mem(params: Mapping[str, Any], section: Section) -> CheckResult:
    total = _number(section, "total-memory")
    free = _number(section, "free-memory")
    if not total or free is None:
        return
    used = total - free
    levels = params.get("levels")

    perc_levels = None
    if isinstance(levels, tuple) and levels[0] == "perc_used":
        perc_levels = ("fixed", tuple(levels[1]))

    yield from check_levels(
        100.0 * used / total,
        levels_upper=perc_levels,
        render_func=render.percent,
        label="RAM used",
        metric_name="mem_used_percent",
        boundaries=(0, 100),
    )
    yield Result(
        state=State.OK,
        summary=f"{render.bytes(used)} of {render.bytes(total)}",
    )
    yield from check_levels(
        free,
        levels_lower=(
            ("fixed", tuple(levels[1]))
            if isinstance(levels, tuple) and levels[0] == "abs_free"
            else None
        ),
        render_func=render.bytes,
        label="Free",
        notice_only=True,
    )
    # standard metric names so the usual memory graphs appear
    yield Metric("mem_used", used, boundaries=(0, total))
    yield Metric("mem_total", total)


check_plugin_mikrotik_rest_api_mem = CheckPlugin(
    name="mikrotik_rest_api_mem",
    sections=["mikrotik_rest_api_board"],
    service_name="Memory",
    discovery_function=discover_mikrotik_rest_api_mem,
    check_function=check_mikrotik_rest_api_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)


# ---------------------------------------------------------------------------
# Filesystem system disk
# ---------------------------------------------------------------------------


def discover_mikrotik_rest_api_fs(section: Section) -> DiscoveryResult:
    if _number(section, "total-hdd-space") and _number(section, "free-hdd-space") is not None:
        yield Service(item=SYSTEM_DISK)


def check_mikrotik_rest_api_fs(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item != SYSTEM_DISK:
        return
    total = _number(section, "total-hdd-space")
    free = _number(section, "free-hdd-space")
    if total is None or free is None:
        return
    mib = 1024.0 * 1024.0
    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=total / mib,
        free_space=free / mib,
        reserved_space=0.0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
        this_time=time.time(),
    )
    # bad blocks have their own service with configurable levels
    # (NAND bad blocks), here only for information
    if (bad := _percent(section.get("bad-blocks"))) is not None:
        yield Result(state=State.OK, notice=f"Bad blocks: {bad:.1f}% (service NAND bad blocks)")


check_plugin_mikrotik_rest_api_fs = CheckPlugin(
    name="mikrotik_rest_api_fs",
    sections=["mikrotik_rest_api_board"],
    service_name="Filesystem %s",
    discovery_function=discover_mikrotik_rest_api_fs,
    check_function=check_mikrotik_rest_api_fs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


# ---------------------------------------------------------------------------
# Uptime
# ---------------------------------------------------------------------------

_UNITS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_routeros_uptime(text: str) -> float | None:
    """'2w3d4h5m6s' (API) or '2w3d04:05:06' (CLI style) -> seconds."""
    text = text.strip()
    if not text:
        return None
    seconds = 0.0
    clock = re.search(r"(\d+):(\d{2}):(\d{2})$", text)
    if clock:
        h, m, s = (int(x) for x in clock.groups())
        seconds += h * 3600 + m * 60 + s
        text = text[: clock.start()]
    parts = re.findall(r"(\d+)([wdhms])", text)
    if not parts and not clock:
        return None
    seconds += sum(int(n) * _UNITS[u] for n, u in parts)
    return seconds


def discover_mikrotik_rest_api_uptime(section: Section) -> DiscoveryResult:
    if parse_routeros_uptime(section.get("uptime", "")) is not None:
        yield Service()


def check_mikrotik_rest_api_uptime(params: Mapping[str, Any], section: Section) -> CheckResult:
    seconds = parse_routeros_uptime(section.get("uptime", ""))
    if seconds is None:
        return
    yield from uptime.check(params, uptime.Section(uptime_sec=seconds, message=None))


check_plugin_mikrotik_rest_api_uptime = CheckPlugin(
    name="mikrotik_rest_api_uptime",
    sections=["mikrotik_rest_api_board"],
    service_name="Uptime",
    discovery_function=discover_mikrotik_rest_api_uptime,
    check_function=check_mikrotik_rest_api_uptime,
    check_ruleset_name="uptime",
    check_default_parameters={},
)


# ---------------------------------------------------------------------------
# NAND bad blocks
# ---------------------------------------------------------------------------
# RouterOS reports "bad-blocks" in percent of the NAND flash. A small share
# of bad blocks is normal for NAND (often already from the factory) and is
# handled by the flash management; it only matters if it grows.


def discover_mikrotik_rest_api_bad_blocks(section: Section) -> DiscoveryResult:
    if _percent(section.get("bad-blocks")) is not None:
        yield Service()


def check_mikrotik_rest_api_bad_blocks(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (bad := _percent(section.get("bad-blocks"))) is None:
        return
    yield from check_levels(
        bad,
        levels_upper=params.get("levels"),
        metric_name="mikrotik_rest_api_bad_blocks",
        render_func=lambda v: f"{v:.1f}%",
        label="Bad blocks",
        boundaries=(0, 100),
    )
    for key, label in (
        ("write-sect-since-reboot", "Sectors written since reboot"),
        ("write-sect-total", "Sectors written in total"),
    ):
        if section.get(key):
            yield Result(state=State.OK, notice=f"{label}: {section[key]}")


check_plugin_mikrotik_rest_api_bad_blocks = CheckPlugin(
    name="mikrotik_rest_api_bad_blocks",
    sections=["mikrotik_rest_api_board"],
    service_name="NAND bad blocks",
    discovery_function=discover_mikrotik_rest_api_bad_blocks,
    check_function=check_mikrotik_rest_api_bad_blocks,
    check_ruleset_name="mikrotik_rest_api_bad_blocks",
    check_default_parameters={"levels": ("fixed", (2.0, 5.0))},
)
