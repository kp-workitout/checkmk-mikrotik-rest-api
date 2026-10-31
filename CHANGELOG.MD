# Changelog - mikrotik-rest-api (MikroTik Monitoring Plugin for Checkmk)

## [1.2.4] - 2026-10-31
### Changed
- Published on GitHub: kp-workitout/checkmk-mikrotik-rest-api. Download
  URL in the package, README and Exchange description point there.
- Agent version string updated to 1.2.4

## [1.2.3] - 2026-10-26
### Fixed
- Filesystem system disk was WARN as soon as the device reported any bad
  blocks (e.g. 0.1 percent, normal for NAND flash), without a way to
  change it. Bad blocks are now only shown in the details there.

### Added
- New service NAND bad blocks (from /system/resource, module RouterOS
  Info) with configurable levels, default WARN at 2 percent and CRIT at 5
  percent, rule MikroTik REST API: NAND bad blocks. Written sectors are
  shown in the details. Perf-O-Meter and metric included.

### Changed
- Agent version string updated to 1.2.3

### Upgrade notes
- Run a service discovery on the MikroTik hosts to get the new service.

## [1.2.2] - 2026-10-24
### Fixed
- Interfaces had no Perf-O-Meter and no standard interface graphs: the
  metric names of the interface library (in, out, ...) are now translated
  for the MikroTik interface check the same way Checkmk does it for its own
  interface checks (input/output bandwidth etc.). Existing interface
  graphs start anew, as the metric names change.
- IP pools had no Perf-O-Meter: metric definitions, Perf-O-Meter (used in
  percent) and graphs for IP pools added.

### Added
- Metric definitions for WireGuard handshake age and WiFi (clients,
  signal), Perf-O-Meter for WiFi clients and a WiFi signal graph.

### Changed
- Agent version string updated to 1.2.2

## [1.2.1] - 2026-10-24
### Changed
- Author contact address changed to kp@workitout.at
- Agent version string updated to 1.2.1

## [1.2.0] - 2026-10-24
Changes by Klaus Paulitsch (kp@workitout.at).

### Fixed
- Check plugins referenced rule sets that did not exist (inherited from
  the original package): BGP, VRRP and Firewall Filter have no parameters
  and no longer reference a rule set.
- New rule MikroTik REST API: OSPF neighbors (states considered OK) and
  MikroTik REST API: License (CHR) (levels for the time until expiry,
  time pattern). Their defaults are unchanged.
- Man pages for License (CHR) and PoE Consumption added, every check
  plugin now has one.

### Changed
- Agent version string updated to 1.2.0

## [1.1.0] - 2026-10-24
Changes by Klaus Paulitsch (kp@workitout.at).

### Added
- **UPS** (module ups, /system/ups and monitor once, needs package
  ups.npk): one service per UPS with power source, battery low, replace
  battery, overload, battery charge, runtime left, load, temperature,
  voltages and frequency; UPS in the HW/SW inventory. Rule MikroTik REST
  API: UPS.
- **IP pools** (module pools, /ip/pool and /ip/pool/used): one service per
  pool with used and free addresses, levels in percent and absolute. The
  agent only transfers the count, not the leases. Rule MikroTik REST API:
  IP pools.
- **NTP client** (module ntp, /system/ntp/client): service NTP Time with
  synchronisation status, offset and stratum. Rule MikroTik REST API: NTP
  client.
- **WireGuard peers** (module wireguard, /interface/wireguard/peers): one
  service per peer with time since the last handshake, current endpoint
  and traffic. Site-to-site peers (endpoint and keepalive configured) get
  levels on the handshake age, dial-in peers none by default. Private and
  preshared keys are never collected. Rule MikroTik REST API: WireGuard
  peers.

### Changed
- Agent version string updated to 1.1.0

### Upgrade notes
- The new modules are off in existing rules: enable UPS, IP pools, NTP
  client and/or WireGuard peers in the special agent rule and run a
  service discovery.

## [1.0.0] - 2026-10-23
First release of mikrotik-rest-api by Klaus Paulitsch
(kp@workitout.at), based on mikrotik 4.2.0 by Tony Boston.

### Changed
- **REST API only**: the agent talks exclusively to the RouterOS REST API
  over HTTPS (service www-ssl, default port 443) or HTTP (service www,
  RouterOS 7.9 or later, port 80). The binary RouterOS API (ports
  8728/8729) and its client code were removed. Requires RouterOS 7.1 or
  later.
- One HTTP session for all requests, timeout per request (default 15 s,
  configurable), clear error messages for connection, certificate and
  authentication problems. The protocol setting is now honoured (the
  original REST mode always used HTTP).
- Special agent rule: Protocol (HTTPS with or without certificate check,
  HTTP), optional TCP port and timeout. The switch between RouterOS API
  and REST API is gone.
- **Renamed to mikrotik-rest-api** so it can be installed next to the
  original mikrotik package. All names Checkmk registers globally are new:
  package, plugin directory, special agent, agent sections, check and
  inventory plugins, check parameter rule sets, man pages and the WiFi
  metrics (table in the README). Rule titles read MikroTik RouterOS
  (mikrotik-rest-api) and MikroTik REST API: ...

### Added
- **Network interfaces**: agent module interfaces (rule option Network
  interfaces). Traffic, packets, errors, discards, state and speed via the
  standard Checkmk interface check and its rules (Network interface and
  switch port discovery, Network interfaces and switch ports), plus the
  interface table in the HW/SW inventory. RouterOS interface types are
  mapped to IANA ifTypes, so by default only ethernet ports that are up
  are discovered, as with SNMP. The index is the RouterOS internal id,
  description the name, alias the comment. Speed is the negotiated rate of
  ethernet and SFP ports.
- **System services** from /system/resource (module RouterOS Info, CPU,
  memory, system disk, uptime) with the standard Checkmk checks and rules:
  CPU utilization, Memory, Filesystem system disk and Uptime.
- **RouterOS Info** shows board, architecture, platform, CPU, RouterOS
  build time and factory software in the details; the HW/SW inventory
  additionally gets CPU and total memory.

### Notes
- On the device: enable www-ssl (with a certificate) or www, and create a
  user whose group has the policies read and api.
- Rules of the original mikrotik package are not taken over. Assign each
  host to only one of the two special agents, the service names are the
  same.
- The modules interfaces and wifi are opt-in and not part of the agent
  default all.
- If a host is also polled via SNMP, the interface section of this agent
  supersedes the SNMP interface sections; disable the SNMP services CPU
  utilization, Memory and Uptime there to avoid duplicates.

## [4.2.0] - 2026-10-16 - original mikrotik package by Tony Boston, all
entries from here on refer to it
### Added
- **WiFi service per SSID**: new agent module `wifi` (rule option "WiFi
  clients and radios"). Reports connected clients, average and weakest
  client signal (dBm) and the radios that broadcast the SSID. Works with
  the new `wifi` driver (RouterOS 7.13+), the legacy `wireless` driver and
  the legacy CAPsMAN. On a CAPsMAN controller one host covers all managed
  access points; a radio that is not running (access point lost the
  controller) makes the service WARN by default.
- New check rule "MikroTik WiFi": levels for clients and signal, state for
  radios that are down.
- **HW/SW inventory of managed access points**: on a CAPsMAN controller
  the `wifi` module also lists every managed access point (new CAPsMAN
  and legacy `/caps-man`) under `networking.wlan.controller.accesspoints`
  (same table as Aruba/Cisco WLC): identity, model, serial, RouterOS
  version, base MAC, state.

### Changed
- Agent version string updated to 4.2.0

### Upgrade notes
- The module is off in existing rules. Enable "WiFi clients and radios"
  in the special agent rule of the CAPsMAN controller (or standalone access
  point) and run a service discovery.
- `wifi` is opt-in: the agent default "all" (a rule with no module ticked)
  does not include it, it only runs when selected explicitly.
- The new `wifi` driver does not report clients via SNMP, so this is the
  only way to monitor clients of WiFi 6 (ax) MikroTik access points.

## [4.1.0] - 2026-10-13
### Added
- **RouterOS Info**: the agent module `board` now also queries
  `/system/routerboard` and reports serial number and RouterBOOT firmware
  (`current-firmware`, `upgrade-firmware`). Keys are emitted with an `rb-`
  prefix in the board agent section.
- **Firmware upgrade pending**: if `upgrade-firmware` is higher than
  `current-firmware`, RouterOS Info reports the pending RouterBOOT upgrade.
  New rule parameter "State if RouterBOOT firmware upgrade is pending"
  (default WARN).
- **HW/SW inventory plugin**: `hardware.system`
  (manufacturer, model, serial), `software.os` (vendor, name, version),
  `software.firmware` (vendor, version). Needs the "Do HW/SW Inventory" rule.

### Changed
- Agent version string updated to 4.1.0

### Upgrade notes
- No rule changes needed. Serial and firmware appear in `RouterOS Info` once
  the special agent runs with the module "RouterOS Board Info" enabled.
- The inventory data needs the "Do HW/SW Inventory" rule on the MikroTik hosts.

## [4.0.3] - 2026-05-26
### Fixed
- Agent version string updated to `4.0.3-mikrotik_agent`
- Removed inaccurate V×I power calculation from `Power PSU` services;
  power is now exclusively reported by the dedicated `PoE Consumption` service

## [4.0.2] - 2026-05-26
### Added
- **PoE Consumption service**: RouterOS health field `poe-out-consumption` is now
  emitted as a dedicated `<<<mikrotik_poe>>>` section and monitored as a separate
  "PoE Consumption" service showing output watts and a `poe_consumption` metric.
- **FAN Status service**: the `fan-state` field (overall fan health reported by RouterOS)
  was previously silently dropped by the fan parser. It is now discovered as a
  "FAN Status" service item alongside the per-fan speed services.

## [4.0.1] - 2026-05-26
### Fixed
- **Power calculation**: currents of exactly 100 mA were not converted to amps
  because the boundary check used `>` instead of `>=`. This caused a current of
  100 mA to be treated as 100 A, producing absurd wattage readings (e.g. 5430 W
  instead of 5.4 W) on switches whose PSU current sits at that exact threshold.
- **Agent version string**: the `<<<check_mk>>>` header still reported
  `3.3.x-mikrotik_agent`; updated to `4.0.1-mikrotik_agent`.

## [4.0.0] - 2026-05-13
### Changed
- **Requires CheckMK 2.4 or later.** The `cmk.gui.plugins.wato` API was
  removed in CheckMK 2.5. The plugin now uses the `cmk.rulesets.v1` and
  `cmk.server_side_calls.v1` APIs, replacing the `wato/` directory with
  `rulesets/` and `server_side_calls/`.
- The two separate SSL/TLS dropdowns (`Use SSL` and `Validate certificate`)
  have been replaced by a single **Connection security** dropdown with three
  mutually exclusive options: SSL (verify certificate), SSL (skip certificate
  verification), and Plain TCP.
- Power monitoring redesigned: one service per PSU (`Power PSU1`,
  `Power PSU2`, …) instead of a single aggregated `Power Usage` service,
  fixing doubled readings on dual-PSU devices. RouterOS's own
  `power-consumption` field is now captured directly.
- Fan check: the `output_metrics` toggle has been removed; performance
  metrics are always emitted.
- Password store lookup now uses `cmk.utils.password_store.lookup()`,
  correctly handling CheckMK's binary password store format. Previously,
  using the CheckMK password store caused login failures.
- Stored rules are automatically migrated on MKP install — no manual
  reconfiguration needed. Hyphenated keys (`no-ssl`, `skip-cert-check`,
  `show-disabled`) are renamed transparently, and obsolete keys
  (`output_metrics`, `psu_count`) are stripped silently.

### Migration notes (v3.x → v4.0.0)
- **Special agent and check parameter rules**: migrated automatically on
  MKP install. No action required.
- **Power services**: the old `Power Usage` service is incompatible with
  the new per-PSU check. After installing the MKP, run **Update service
  configuration** on any MikroTik host that had health monitoring enabled.
  The old service will be removed and replaced by `Power PSU1` / `Power PSU2`
  (or however many PSUs the device reports).

## [3.3.0] - 2026-02-18
### Changed
- Add the option to show the disabled firewall rules that is discovery by the plugin (Thanks to Marcel Eckert for the suggestion)
- Completely rewritten the configuration section on WATO
- ⚠️ You must remove any previous rules based on this plugin and reconfigure from scratch

## [3.2.2] - 2025-08-06
### Fixed
- Resolved an issue that not correctly load the enabled firewall rules (Thanks to Marcel Eckert for the suggestion)

## [3.2.2] - 2025-08-06
### Fixed
- Resolved an issue that not show section "Mikrotik RouterOS" on WATO to set plugin (Thanks to Hugo for the suggestion)

## [3.2.1] - 2025-08-04
### Changed
- Set state to CRITICAL from UNKNOWN when BGP neighbor peer or OSPF neighbor peer is not found

## [3.2.0] - 2025-08-01
### Changed
- Complete rewrite of the plugin to support new version of CheckMK API v2.
- Incompatible with previous versions of Checkmk: use version 3.0.5 or earlier.
- ⚠️ You must remove any previous version of this plugin before installing.

### Added
- Compatibility with CheckMK 2.4

## [3.0.5] - 2025-06-05
### Fixed
- Changed shebang to use `/usr/bin/env python3` in all scripts and agents. (Thanks to Bernhard Petschowitsch for the suggestion)

## [3.0.4] - 2025-05-27
### Fixed
- Python3 environment issues in agent-based scripts.

## [3.0.3] - 2024-04-30
### Fixed
- Resolved regex warning during Checkmk updates.

## [3.0.2] - 2025-04-22
### Changed
- Reworked agent that connects to MikroTik.
- SSL connection is now enabled by default.
- Option added to skip certificate validation.
- Rewritten WATO configuration plugin.
- ⚠️ You must reconfigure the datasource rule in Checkmk after installing.

## [2.6.5] - 2025-04-07
### Fixed
- Documentation updated.

## [2.6.4] - 2025-04-07
### Fixed
- Fixed MikroTik API connection issue when result is empty.

## [2.6.3] - 2025-03-30
### Fixed
- Fixed a bug introduced in previous bugfix.

## [2.6.2] - 2025-03-30
### Fixed
- Bug in watchdog file detection via RESTful API.
- Minor improvements in `mikrotik_file`.

## [2.6.1] - 2025-03-24
### Fixed
- Crash when running `cmk -R` after upgrading from 2.5.x.
- Added check for `requests` module on import.
- Improved IPsec failure detection logic.

## [2.6.0] - 2025-03-24
### Added
- Option to use RESTful API for data collection.
- ⚠️ Requires rule reconfiguration.

## [2.5.7] - 2024-12-23
### Added
- License checking on CHR.

## [2.5.6] - 2024-10-21
### Fixed
- `mikrotik_file` works with RouterOS 7.16.1.

## [2.5.5] - 2024-04-04
### Fixed
- Bug in non-established BGP sessions (RouterOS v7).

## [2.5.4] - 2024-02-16
### Changed
- Reworked power section.

## [2.5.3] - 2024-02-16
### Added
- OSPF support for RouterOS v7 and IPv6.
- BGP support for recent v7 builds.
- Reworked special agent.

## [2.5.2] - 2024-02-01
### Fixed
- Bug with multibyte characters in API call.

## [2.5.1] - 2024-02-01
### Fixed
- Crash in power consumption calculation on new OS.
- Added handling of `autosupout.rif`.

## [2.5.0] - 2024-01-19
### Fixed
- Crash on CHR.
- Adjusted board section (requires `cmk -R`).

## [2.4.1] - 2023-11-03
### Fixed
- Crash in BGP when information is missing.

## [2.4.0] - 2023-09-26
### Changed
- BGP and file age support for RouterOS v7.

## [2.3.4] - 2023-08-09
### Added
- Compatibility with Checkmk 2.1 and 2.2.

## [2.3.3] - 2023-04-04
### Fixed
- Crash on multiple IPsec connections.

## [2.3.2] - 2023-03-08
### Added
- GPL headers.

## [2.3.1] - 2023-03-06
### Fixed
- PSU discovery issue.

## [2.3.0] - 2023-03-06
### Changed
- Complete rewrite for Checkmk 2.x.
- Changed versioning scheme.
- Switched to `os-python3` and modern SSL ciphers.
- Multiple improvements in summaries and plugin logic.

## [2.2] - 2022-05-11
### Fixed
- Handled orphaned IPsec SAs.
- Increased SA count now gives WARN instead of CRIT.

## [2.1] - 2021-01-19
### Added
- File age check.
- Minor firewall bugfix.

## [2.0a] - 2020-10-28
### Fixed
- PSU bugfix.

## [2.0] - 2020-10-28
### Changed
- Major rewrite of special agent to Python 3.
- Added firewall filter rule checks.

## [1.2a] - 2020-09-21
### Fixed
- Wrong header info.

## [1.2] / [1.1] - 2020-09
### Changed
- Major rewrite for Checkmk 1.6.

## [1.0] - 2020-01-20
### Added
- Major rewrite for RouterOS switches.
- Added PSU and IPsec info.
- Inventory ignores disabled VRRP.

## [0.4a] - 2019-07-23
### Fixed
- Bug in electrical current calculation.

## [0.4] - 2019-04-23
### Added
- Power info on dual-PSU devices.
- Power-loss detection.
### Fixed
- Board info bug for AP devices.

## [0.3] - 2019-04-23

## [0.2] - 2018-10-17

## [0.1] - 2018-10-12
### Initial release by ttr
