"""Metric definitions, graphs, Perf-O-Meters and translations.

- Interfaces: the standard interface library reports in/out/inucast/...;
  Checkmk translates these names only for its own interface checks (if64,
  lnx_if, ...). The translation below does the same for
  mikrotik_rest_api_if, so the usual interface graphs and the bandwidth
  Perf-O-Meter appear.
- IP pools, WireGuard handshake age and WiFi: own metrics of this package.

mikrotik-rest-api 1.2.2 by Klaus Paulitsch <kp@workitout.at>.
"""

from cmk.graphing.v1 import Title, graphs, metrics, perfometers, translations

# ---------------------------------------------------------------------------
# Interfaces: same translation as Checkmk uses for if64 / lnx_if
# ---------------------------------------------------------------------------

translation_mikrotik_rest_api_if = translations.Translation(
    name="mikrotik_rest_api_if",
    check_commands=[translations.PassiveCheck("mikrotik_rest_api_if")],
    translations={
        "in": translations.RenameToAndScaleBy("if_in_bps", 8),
        "inbcast": translations.RenameTo("if_in_bcast"),
        "indisc": translations.RenameTo("if_in_discards"),
        "inerr": translations.RenameTo("if_in_errors"),
        "inmcast": translations.RenameTo("if_in_mcast"),
        "innucast": translations.RenameTo("if_in_non_unicast"),
        "inucast": translations.RenameTo("if_in_unicast"),
        "out": translations.RenameToAndScaleBy("if_out_bps", 8),
        "outbcast": translations.RenameTo("if_out_bcast"),
        "outdisc": translations.RenameTo("if_out_discards"),
        "outerr": translations.RenameTo("if_out_errors"),
        "outmcast": translations.RenameTo("if_out_mcast"),
        "outnucast": translations.RenameTo("if_out_non_unicast"),
        "outucast": translations.RenameTo("if_out_unicast"),
        "total": translations.RenameToAndScaleBy("if_total_bps", 8),
    },
)

# ---------------------------------------------------------------------------
# IP pools
# ---------------------------------------------------------------------------

UNIT_PERCENT = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(0))

metric_mikrotik_rest_api_pool_used_percent = metrics.Metric(
    name="mikrotik_rest_api_pool_used_percent",
    title=Title("Used addresses (percent)"),
    unit=UNIT_PERCENT,
    color=metrics.Color.BLUE,
)
metric_mikrotik_rest_api_pool_used = metrics.Metric(
    name="mikrotik_rest_api_pool_used",
    title=Title("Used addresses"),
    unit=UNIT_COUNT,
    color=metrics.Color.ORANGE,
)
metric_mikrotik_rest_api_pool_free = metrics.Metric(
    name="mikrotik_rest_api_pool_free",
    title=Title("Free addresses"),
    unit=UNIT_COUNT,
    color=metrics.Color.GREEN,
)

perfometer_mikrotik_rest_api_pool = perfometers.Perfometer(
    name="mikrotik_rest_api_pool",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["mikrotik_rest_api_pool_used_percent"],
)

graph_mikrotik_rest_api_pool = graphs.Graph(
    name="mikrotik_rest_api_pool",
    title=Title("IP pool addresses"),
    compound_lines=["mikrotik_rest_api_pool_used", "mikrotik_rest_api_pool_free"],
)

graph_mikrotik_rest_api_pool_percent = graphs.Graph(
    name="mikrotik_rest_api_pool_percent",
    title=Title("IP pool usage"),
    minimal_range=graphs.MinimalRange(0, 100),
    simple_lines=[
        "mikrotik_rest_api_pool_used_percent",
        metrics.WarningOf("mikrotik_rest_api_pool_used_percent"),
        metrics.CriticalOf("mikrotik_rest_api_pool_used_percent"),
    ],
)

# ---------------------------------------------------------------------------
# NAND bad blocks
# ---------------------------------------------------------------------------

metric_mikrotik_rest_api_bad_blocks = metrics.Metric(
    name="mikrotik_rest_api_bad_blocks",
    title=Title("NAND bad blocks"),
    unit=UNIT_PERCENT,
    color=metrics.Color.BROWN,
)

perfometer_mikrotik_rest_api_bad_blocks = perfometers.Perfometer(
    name="mikrotik_rest_api_bad_blocks",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(10)),
    segments=["mikrotik_rest_api_bad_blocks"],
)

# ---------------------------------------------------------------------------
# MLAG
# ---------------------------------------------------------------------------

metric_mikrotik_rest_api_mlag_bond_active = metrics.Metric(
    name="mikrotik_rest_api_mlag_bond_active",
    title=Title("Active member ports"),
    unit=UNIT_COUNT,
    color=metrics.Color.GREEN,
)

# ---------------------------------------------------------------------------
# WireGuard
# ---------------------------------------------------------------------------

metric_mikrotik_rest_api_wg_handshake_age = metrics.Metric(
    name="mikrotik_rest_api_wg_handshake_age",
    title=Title("Time since last handshake"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.PURPLE,
)

# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------

UNIT_DBM = metrics.Unit(metrics.DecimalNotation("dBm"))

metric_mikrotik_rest_api_wifi_clients = metrics.Metric(
    name="mikrotik_rest_api_wifi_clients",
    title=Title("Connected clients"),
    unit=UNIT_COUNT,
    color=metrics.Color.BLUE,
)
metric_mikrotik_rest_api_wifi_signal_avg = metrics.Metric(
    name="mikrotik_rest_api_wifi_signal_avg",
    title=Title("Average client signal"),
    unit=UNIT_DBM,
    color=metrics.Color.GREEN,
)
metric_mikrotik_rest_api_wifi_signal_min = metrics.Metric(
    name="mikrotik_rest_api_wifi_signal_min",
    title=Title("Weakest client signal"),
    unit=UNIT_DBM,
    color=metrics.Color.RED,
)

perfometer_mikrotik_rest_api_wifi_clients = perfometers.Perfometer(
    name="mikrotik_rest_api_wifi_clients",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(50)),
    segments=["mikrotik_rest_api_wifi_clients"],
)

graph_mikrotik_rest_api_wifi_signal = graphs.Graph(
    name="mikrotik_rest_api_wifi_signal",
    title=Title("WiFi client signal"),
    simple_lines=["mikrotik_rest_api_wifi_signal_avg", "mikrotik_rest_api_wifi_signal_min"],
)
