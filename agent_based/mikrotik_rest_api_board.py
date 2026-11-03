"""CheckMK agent-based check plugin for MikroTik board monitoring."""


from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
)
from packaging import version  # Sostituisce distutils.version che è deprecato


def parse_mikrotik_rest_api_board(string_table: StringTable) -> dict[str, str] | None:
    """Parse MikroTik board information from agent output.

    Keys prefixed with ``rb-`` come from /system/routerboard (agent >= 4.1.0),
    the others from /system/resource. All keys are kept: the system checks
    (CPU, memory, system disk, uptime) in mikrotik_rest_api_system.py use the
    same section.
    """
    section = {
        line[0]: " ".join(line[1:])
        for line in string_table
        if line
    }
    # nothing delivered: None, so the section does not supersede SNMP
    return section or None

def discover_mikrotik_rest_api_board(section: dict[str, str]) -> DiscoveryResult:
    """Discover service if version information is present."""
    if section.get("version"):
        yield Service()

def check_mikrotik_rest_api_board(
    params: dict,
    section: dict[str, str],
) -> CheckResult:
    """Check MikroTik board information and version compliance."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No board information found")
        return

    # Check version compliance if required
    min_version = params.get("min_version", "0.0")
    current_state = State.OK
    summary_parts = []

    if "board-name" in section:
        summary_parts.append(f"Model: {section['board-name']}")

    if "version" in section:
        current_version = section["version"].split(" ")[0]
        summary_parts.append(f"Version: {section['version']}")

        if min_version != "0.0":
            try:
                if version.parse(current_version) < version.parse(min_version):
                    current_state = State.WARN
                    summary_parts.append(
                        f"(below minimum required: {min_version})",
                    )
            except version.InvalidVersion:
                summary_parts.append("(version parsing failed)")
                current_state = State.WARN

    if section.get("rb-serial-number"):
        summary_parts.append(f"Serial: {section['rb-serial-number']}")

    yield Result(
        state=current_state,
        summary=", ".join(summary_parts),
    )

    # hardware details (long output)
    details = [
        ("Board", section.get("rb-model") or section.get("board-name")),
        ("Architecture", section.get("architecture-name")),
        ("Platform", section.get("platform")),
        ("CPU", section.get("cpu")),
        ("CPU cores", section.get("cpu-count")),
        ("CPU frequency", f"{section['cpu-frequency']} MHz" if section.get("cpu-frequency") else None),
        ("RouterOS build time", section.get("build-time")),
        ("Factory software", section.get("factory-software")),
        ("Firmware type", section.get("rb-firmware-type")),
    ]
    for label, value in details:
        if value:
            yield Result(state=State.OK, notice=f"{label}: {value}")

    # RouterBOOT firmware. MikroTik documents: "If upgrade-firmware shows a
    # higher version than current-firmware, a newer version is ready to be
    # applied" (/system/routerboard upgrade, then /system/reboot).
    current_fw = section.get("rb-current-firmware")
    upgrade_fw = section.get("rb-upgrade-firmware")
    if not current_fw:
        return
    if not upgrade_fw:
        yield Result(state=State.OK, summary=f"Firmware: {current_fw}")
        return
    try:
        pending = version.parse(current_fw) < version.parse(upgrade_fw)
    except version.InvalidVersion:
        yield Result(
            state=State.OK,
            summary=f"Firmware: {current_fw} (upgrade firmware {upgrade_fw} not comparable)",
        )
        return
    if pending:
        yield Result(
            state=State(params.get("firmware_upgrade_pending", 1)),
            summary=(
                f"Firmware: {current_fw}, upgrade to {upgrade_fw} pending "
                "(/system/routerboard upgrade + reboot)"
            ),
        )
    else:
        yield Result(state=State.OK, summary=f"Firmware: {current_fw}")

def inventory_mikrotik_rest_api_board(section: dict[str, str]) -> InventoryResult:
    """HW/SW inventory: model, serial, RouterOS version, RouterBOOT firmware."""
    hardware = {"manufacturer": "MikroTik"}
    model = section.get("rb-model") or section.get("board-name")
    if model:
        hardware["model"] = model
    if section.get("rb-serial-number"):
        hardware["serial"] = section["rb-serial-number"]
    yield Attributes(path=["hardware", "system"], inventory_attributes=hardware)

    cpu: dict[str, str | int | float] = {}
    if section.get("cpu"):
        cpu["model"] = section["cpu"]
    if section.get("architecture-name"):
        cpu["arch"] = section["architecture-name"]
    if section.get("cpu-count", "").isdigit():
        cpu["cores"] = int(section["cpu-count"])
    if section.get("cpu-frequency", "").isdigit():
        cpu["max_speed"] = float(section["cpu-frequency"]) * 1_000_000
    if cpu:
        yield Attributes(path=["hardware", "cpu"], inventory_attributes=cpu)

    if section.get("total-memory", "").isdigit():
        yield Attributes(
            path=["hardware", "memory"],
            inventory_attributes={"total_ram_usable": int(section["total-memory"])},
        )

    if section.get("version"):
        yield Attributes(
            path=["software", "os"],
            inventory_attributes={
                "vendor": "MikroTik",
                "name": "RouterOS",
                "version": section["version"].split(" ")[0],
            },
        )

    if section.get("rb-current-firmware"):
        yield Attributes(
            path=["software", "firmware"],
            inventory_attributes={
                "vendor": "MikroTik",
                "version": section["rb-current-firmware"],
            },
        )

# Register agent section
agent_section_mikrotik_rest_api_board = AgentSection(
    name="mikrotik_rest_api_board",
    parse_function=parse_mikrotik_rest_api_board,
    # CPU utilization and Filesystem system disk come from this section; a
    # host that is also polled via SNMP must not get them twice
    supersedes=["hr_cpu", "hr_fs"],
)

# Register check plugin
check_plugin_mikrotik_rest_api_board = CheckPlugin(
    name="mikrotik_rest_api_board",
    service_name="RouterOS Info",
    discovery_function=discover_mikrotik_rest_api_board,
    check_function=check_mikrotik_rest_api_board,
    check_default_parameters={"min_version": "0.0", "firmware_upgrade_pending": 1},
    check_ruleset_name="mikrotik_rest_api_board",
)

# Register inventory plugin (needs the "Do HW/SW Inventory" rule on the host)
inventory_plugin_mikrotik_rest_api_board = InventoryPlugin(
    name="mikrotik_rest_api_board",
    inventory_function=inventory_mikrotik_rest_api_board,
)
