## mikrotik-rest-api – MikroTik RouterOS Plugin for CheckMK

Based on the `mikrotik` Checkmk package 4.2.0 (Tony Boston), renamed so that
both packages can be installed at the same time.

This plugin monitors MikroTik RouterOS devices **exclusively via the
RouterOS REST API** (HTTPS or HTTP). The binary RouterOS API (ports
8728/8729) is not used.

It includes checks for:

- BGP and OSPF neighbors
- VRRP status
- PSU, fan, and temperature sensors
- IPsec tunnels
- License expiration (CHR) and file age
- Firewall rules based on comment filters
- System health and crashfile detection
- RouterOS Info: model, serial, RouterOS version, RouterBOOT firmware
  (state if a firmware upgrade is pending) and HW/SW inventory
- WiFi per SSID: clients, signal strength and radio state, for the new
  `wifi` driver, the legacy `wireless` driver and CAPsMAN (one controller
  covers all its access points) and HW/SW inventory of the access points
  managed by a CAPsMAN controller (model, serial, version)
- System: CPU utilization, Memory, Filesystem system disk and Uptime via the
  standard Checkmk checks (module "RouterOS Info, CPU, memory, system disk,
  uptime"); RouterOS Info with board, architecture, CPU and RouterOS build time
- UPS (`/system/ups`, package ups.npk), IP pool usage (`/ip/pool`), NTP
  client (`/system/ntp/client`) and WireGuard peers
  (`/interface/wireguard/peers`, handshake age, endpoint, traffic)
- Network interfaces: traffic, errors, discards, state and speed via the
  standard Checkmk interface check (all rules for interfaces and switch
  ports apply), plus the interface table in the HW/SW inventory

### Requirements

- CheckMK 2.4 or later
- MikroTik RouterOS 7.1 or later (REST API), HTTP needs RouterOS 7.9 or later
- On the device:
  - HTTPS: service `www-ssl` enabled with a certificate
    (`/ip service set www-ssl certificate=<cert> disabled=no`); with a
    self-signed certificate choose *HTTPS — do not validate certificate*
  - or HTTP: service `www` enabled (credentials are sent unencrypted)
  - a user whose group has the policies `read` and `api`, e.g.
    `/user group add name=monitoring policy=read,api` and
    `/user add name=checkmk group=monitoring password=...`
  - optionally restrict the service to the Checkmk server
    (`/ip service set www-ssl address=<checkmk-ip>/32`)

### Installation

Install the `.mkp` file via **Setup → Extension packages** or via the CLI:

```
mkp add mikrotik-rest-api-<version>.mkp
mkp enable mikrotik-rest-api <version>
```

After installation, configure the special agent under
**Setup → Other integrations → MikroTik RouterOS (mikrotik-rest-api)** and assign it to your
MikroTik hosts.

### Parallel installation next to the original `mikrotik` package

Everything Checkmk registers globally has its own name, so both packages
can be installed at the same time:

| | original | this package |
|---|---|---|
| Package | `mikrotik` | `mikrotik-rest-api` |
| Plugin directory | `cmk_addons/plugins/mikrotik` | `cmk_addons/plugins/mikrotik_rest_api` |
| Special agent | `agent_mikrotik` | `agent_mikrotik_rest_api` |
| Sections, check/inventory plugins, rule sets, man pages, WiFi metrics | `mikrotik_*` | `mikrotik_rest_api_*` |
| Rule title (special agent) | MikroTik RouterOS | MikroTik RouterOS (mikrotik-rest-api) |
| Rule titles (check parameters) | MikroTik … | MikroTik REST API: … |

Rules of the original package are not used by this one. Create a new
special agent rule and assign each host to only one of the two agents –
both create services with the same names. When switching a host, run a
service discovery; graphs start anew because the metric names differ.

### Network interfaces

Enable **Network interfaces** in the special agent rule and run a service
discovery. Discovery and levels are controlled by the standard rules
**Network interface and switch port discovery** and **Network interfaces
and switch ports**. By default only ethernet ports that are up are
discovered; add port types (e.g. `135 - l2vlan`, `209 - bridge`,
`161 - ieee8023adLag`, `23 - ppp`, `131 - tunnel`) to monitor other
interfaces. For interface names instead of numbers as service names set
*Appearance of network interface* to *Use description*.

### WireGuard peers

A peer counts as **site-to-site** if endpoint address and persistent
keepalive are configured and it is not a responder. Its handshake is renewed
about every 2 minutes, so the service goes WARN after 5 and CRIT after 15
minutes without handshake. All other peers (road warriors, peers without
keepalive) count as **dial-in** and have no levels by default. Both can be
changed in the rule *MikroTik REST API: WireGuard peers*. Private and
preshared keys are never collected.

### Credits

- Original plugin: Tony Boston (tboston@csitlab.org)
- mikrotik-rest-api 1.0.0/1.1.0 (REST API only, rename, network interfaces,
  CPU/memory/system disk/uptime, UPS, IP pools, NTP, WireGuard): Klaus Paulitsch
  (kp@workitout.at)
