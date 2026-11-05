
import json
import sqlite3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_DIR / "data" / "netops.db"
INVENTORY_FILE = PROJECT_DIR / "data" / "devices.json"

st.set_page_config(
    page_title="NetOps Automation Platform",
    page_icon="",
    layout="wide"
)

# SNMP ALERT THRESHOLDS
RAM_WARNING_THRESHOLD = 80
RAM_CRITICAL_THRESHOLD = 90


# ==========================================
# DATABASE
# ==========================================

@st.cache_data(ttl=10)
def load_history():
    """Mengambil histori connectivity monitoring."""
    if not DATABASE_FILE.exists():
        return pd.DataFrame(
            columns=[
                "checked_at",
                "device_name",
                "ip_address",
                "status",
                "latency_ms",
                "packet_loss"
            ]
        )

    with sqlite3.connect(DATABASE_FILE) as connection:
        return pd.read_sql_query(
            """
            SELECT checked_at, device_name, ip_address, status, latency_ms, packet_loss
            FROM monitoring_history
            ORDER BY id DESC
            """,
            connection
        )


@st.cache_data(ttl=10)
def load_snmp_history():
    """Mengambil histori metrik SNMP."""
    if not DATABASE_FILE.exists():
        return pd.DataFrame()

    with sqlite3.connect(DATABASE_FILE) as connection:
        return pd.read_sql_query(
            """
            SELECT
                id,
                checked_at,
                device_name,
                ip_address,
                sys_name,
                uptime_ticks,
                cpu_usage,
                memory_total,
                memory_free,
                memory_used,
                memory_usage_percent
            FROM snmp_history
            ORDER BY id DESC
            """,
            connection
        )


def load_inventory():
    """Membaca informasi perangkat dari inventory."""
    with open(INVENTORY_FILE, "r", encoding="utf-8") as file:
        inventory = json.load(file)

    devices = pd.DataFrame(inventory["devices"])

    return devices.rename(
        columns={
            "name": "device_name",
            "ip": "ip_address",
            "type": "device_type"
        }
    )


def convert_to_local_time(dataframe):
    """Mengubah timestamp menjadi waktu Jakarta."""
    if not dataframe.empty:
        dataframe["checked_at"] = pd.to_datetime(
            dataframe["checked_at"],
            errors="coerce",
            utc=True
        )

        dataframe.dropna(
            subset=["checked_at"],
            inplace=True
        )

        dataframe["checked_at"] = (
            dataframe["checked_at"].dt.tz_convert("Asia/Jakarta")
        )

    return dataframe


def format_uptime(ticks):
    """Mengubah SNMP TimeTicks menjadi format hari dan jam."""
    if pd.isna(ticks):
        return "N/A"

    total_seconds = int(ticks) // 100

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return (
        f"{days}d {hours}h "
        f"{minutes}m {seconds}s"
    )


def format_mib(value):
    """Mengubah bytes menjadi MiB."""
    if pd.isna(value):
        return "N/A"

    return f"{value / (1024 * 1024):.2f} MiB"


# ==========================================
# HEADER
# ==========================================

st.title("NetOps Automation Platform")
st.caption("Network Operations & Monitoring Dashboard")

col_refresh, col_time = st.columns([1, 4])

with col_refresh:
    if st.button("Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ==========================================
# LOAD DATA
# ==========================================

history = load_history()
snmp_history = load_snmp_history()

history = convert_to_local_time(history)
snmp_history = convert_to_local_time(snmp_history)

inventory = load_inventory()


# ==========================================
# CONNECTIVITY MONITORING
# ==========================================

st.header("Connectivity Monitoring")

if history.empty:
    st.warning("No connectivity monitoring data available.")
    st.info(
        "Run the monitoring script first: "
        "python src\\connectivity_check.py"
    )

else:
    # ======================================
    # DATA PROCESSING
    # ======================================

    latest = (
        history.sort_values("checked_at", ascending=False)
        .drop_duplicates(
            subset=["device_name", "ip_address"],
            keep="first"
        )
        .copy()
    )

    latest = latest.merge(
        inventory[
            [
                "device_name",
                "ip_address",
                "device_type",
                "location"
            ]
        ],
        on=["device_name", "ip_address"],
        how="left"
    )

    online_count = int(
        (latest["status"] == "ONLINE").sum()
    )

    offline_count = int(
        (latest["status"] == "OFFLINE").sum()
    )

    total_count = len(latest)

    last_check = history["checked_at"].max()

    online_percentage = (
        online_count / total_count * 100
        if total_count > 0 else 0
    )

    # ======================================
    # KPI METRICS
    # ======================================

    st.subheader("Monitoring Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Devices", total_count)
    col2.metric("Online Devices", online_count)
    col3.metric("Offline Devices", offline_count)
    col4.metric(
        "Online Percentage",
        f"{online_percentage:.1f}%"
    )


    # ======================================
    # CURRENT DEVICE STATUS
    # ======================================

    st.subheader("Current Device Status")

    def highlight_status(value):
        if value == "ONLINE":
            return "color: #16A34A; font-weight: bold"

        if value == "OFFLINE":
            return "color: #DC2626; font-weight: bold"

        return ""

    device_table = latest[
        [
            "device_name",
            "ip_address",
            "device_type",
            "location",
            "status",
            "latency_ms",
            "packet_loss",
            "checked_at"
        ]
    ].copy()

    device_table = device_table.rename(
        columns={
            "latency_ms": "Latency (ms)",
            "packet_loss": "Packet Loss (%)"
        }
    )

    device_table["Latency (ms)"] = (
        device_table["Latency (ms)"].round(2)
    )

    device_table["Packet Loss (%)"] = (
        device_table["Packet Loss (%)"].round(2)
    )

    device_table["checked_at"] = (
        device_table["checked_at"]
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    st.dataframe(
        device_table.style.map(
        highlight_status,
        subset=["status"]
        ),
        use_container_width=True,
        hide_index=True
    )

    # ======================================
    # MONITORING TREND
    # ======================================


    # ======================================
    # NETWORK PERFORMANCE PER DEVICE
    # ======================================

    st.divider()
    st.subheader("Network Performance per Device")

    device_options = (
        latest[["device_name", "ip_address"]]
        .drop_duplicates()
        .sort_values(["device_name", "ip_address"])
    )
    device_choices = list(
        device_options.itertuples(index=False, name=None)
    )

    if device_choices:
        selected_performance_device = st.selectbox(
            "Pilih perangkat",
            device_choices,
            format_func=lambda item: f"{item[0]} ({item[1]})",
            key="performance_device"
        )

        selected_period = st.selectbox(
            "Rentang waktu analisis",
            ["Semua", "1 Jam", "24 Jam", "7 Hari", "30 Hari"],
            index=0,
            key="performance_period"
        )

        device_performance = history[
            (history["device_name"] == selected_performance_device[0])
            & (history["ip_address"] == selected_performance_device[1])
        ].copy()

        period_deltas = {
            "1 Jam": pd.Timedelta(hours=1),
            "24 Jam": pd.Timedelta(hours=24),
            "7 Hari": pd.Timedelta(days=7),
            "30 Hari": pd.Timedelta(days=30)
        }

        if selected_period != "Semua":
            cutoff_time = (
                pd.Timestamp.now(tz="Asia/Jakarta")
                - period_deltas[selected_period]
            )
            device_performance = device_performance[
                device_performance["checked_at"] >= cutoff_time
            ].copy()

        device_performance = device_performance.sort_values("checked_at")

        selected_latest_rows = latest[
            (latest["device_name"] == selected_performance_device[0])
            & (latest["ip_address"] == selected_performance_device[1])
        ]

        if not selected_latest_rows.empty:
            selected_latest_row = selected_latest_rows.iloc[0]
            avg_latency = device_performance["latency_ms"].mean()
            avg_packet_loss = device_performance["packet_loss"].mean()

            def format_metric(value, unit):
                if pd.isna(value):
                    return "N/A"
                return f"{value:.2f} {unit}"

            st.caption(
                f"Perangkat: {selected_performance_device[0]} | "
                f"IP: {selected_performance_device[1]} | "
                f"Periode: {selected_period}"
            )

            metric_cols = st.columns(5)
            metric_cols[0].metric(
                "Current Status",
                selected_latest_row["status"]
            )
            metric_cols[1].metric(
                "Current Latency",
                format_metric(selected_latest_row["latency_ms"], "ms")
            )
            metric_cols[2].metric(
                "Current Packet Loss",
                format_metric(selected_latest_row["packet_loss"], "%")
            )
            metric_cols[3].metric(
                "Average Latency",
                format_metric(avg_latency, "ms")
            )
            metric_cols[4].metric(
                "Average Packet Loss",
                format_metric(avg_packet_loss, "%")
            )

            
            # ======================================
            # COMBINED NETWORK PERFORMANCE CHART
            # ======================================

            st.markdown("**Network Performance Trend**")

            chart_data = (
                device_performance
                .sort_values("checked_at")
                .copy()
            )

            latency_data = chart_data.dropna(
                subset=["latency_ms"]
            )

            packet_loss_data = chart_data.dropna(
                subset=["packet_loss"]
            )

            if not chart_data.empty and (
                not latency_data.empty
                or not packet_loss_data.empty
            ):
                fig = go.Figure()

                # Latency menggunakan batang
                if not latency_data.empty:
                    fig.add_trace(
                        go.Bar(
                            x=latency_data["checked_at"],
                            y=latency_data["latency_ms"],
                            name="Latency (ms)",
                            yaxis="y",
                            hovertemplate=(
                                "Waktu: %{x}<br>"
                                "Latency: %{y:.2f} ms"
                                "<extra></extra>"
                            )
                        )
                    )

                # Packet Loss menggunakan garis
                if not packet_loss_data.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=packet_loss_data["checked_at"],
                            y=packet_loss_data["packet_loss"],
                            name="Packet Loss (%)",
                            mode="lines+markers",
                            yaxis="y2",
                            connectgaps=False,
                            hovertemplate=(
                                "Waktu: %{x}<br>"
                                "Packet Loss: %{y:.2f}%"
                                "<extra></extra>"
                            )
                        )
                    )

                fig.update_layout(
                    title="Latency & Packet Loss",
                    xaxis=dict(
                        title="Monitoring Time"
                    ),
                    yaxis=dict(
                        title="Latency (ms)",
                        side="left",
                        rangemode="tozero"
                    ),
                    yaxis2=dict(
                        title="Packet Loss (%)",
                        overlaying="y",
                        side="right",
                        range=[0, 100],
                        ticksuffix="%"
                    ),
                    hovermode="x unified",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    barmode="group"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:
                st.info(
                    "Belum ada data latency dan packet loss "
                    "untuk perangkat dan periode ini."
                )


    # ======================================
    # MONITORING HISTORY
    # ======================================

    st.divider()
    st.subheader("Monitoring History")

    filter_col, limit_col = st.columns([2, 1])

    with filter_col:
        status_filter = st.selectbox(
            "Filter by Status",
            ["ALL", "ONLINE", "OFFLINE"]
        )

    with limit_col:
        record_limit = st.selectbox(
            "Number of Records",
            [10, 25, 50, 100],
            index=1
        )

    filtered_history = history.copy()

    if status_filter != "ALL":
        filtered_history = filtered_history[
            filtered_history["status"] == status_filter
        ]

    filtered_history = (
        filtered_history
        .sort_values("checked_at", ascending=False)
        .head(record_limit)
    )

    filtered_history["checked_at"] = (
        filtered_history["checked_at"]
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    filtered_history = filtered_history.rename(
        columns={
            "checked_at": "Checked At",
            "device_name": "Device Name",
            "ip_address": "IP Address",
            "status": "Status",
            "latency_ms": "Latency (ms)",
            "packet_loss": "Packet Loss (%)"
        }
    )

    st.dataframe(
        filtered_history,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"Displaying {len(filtered_history)} records "
        f"from {len(history)} monitoring records."
    )


# ==========================================
# SNMP MONITORING
# ==========================================

st.divider()
st.header("SNMP Device Monitoring")

if snmp_history.empty:
    st.warning("No SNMP monitoring data available.")
    st.info(
        "Run the SNMP collector first: "
        "python src\\snmp_collector.py"
    )

else:
    # ======================================
    # LATEST SNMP DATA
    # ======================================

    latest_snmp = (
        snmp_history
        .sort_values("checked_at", ascending=False)
        .drop_duplicates(
            subset=["device_name", "ip_address"],
            keep="first"
        )
        .copy()
    )

    selected_device = st.selectbox(
        "Select SNMP Device",
        latest_snmp["device_name"].tolist()
    )

    selected_row = latest_snmp[
        latest_snmp["device_name"] == selected_device
    ].iloc[0]

    # ======================================
    # DEVICE INFORMATION
    # ======================================

    st.subheader("Device Information")

    info_col1, info_col2, info_col3 = st.columns(3)

    info_col1.metric(
        "Device Name",
        selected_row["device_name"]
    )

    info_col2.metric(
        "IP Address",
        selected_row["ip_address"]
    )

    info_col3.metric(
        "System Name",
        selected_row["sys_name"] or "N/A"
    )

    st.caption(
        f"Uptime: {format_uptime(selected_row['uptime_ticks'])}"
    )

    st.caption(
        "Last SNMP collection: "
        f"{selected_row['checked_at'].strftime('%d %b %Y, %H:%M:%S %Z')}"
    )

    # ======================================
    # RAM METRICS
    # ======================================


    st.divider()
    st.subheader("Memory Utilization")

    memory_total = selected_row["memory_total"]
    memory_used = selected_row["memory_used"]
    memory_free = selected_row["memory_free"]
    memory_percent = selected_row["memory_usage_percent"]

    ram_col1, ram_col2, ram_col3 = st.columns(3)

    ram_col1.metric(
        "Total RAM",
        format_mib(memory_total)
    )

    ram_col2.metric(
        "Used RAM",
        format_mib(memory_used)
    )

    ram_col3.metric(
        "Free RAM",
        format_mib(memory_free)
    )

    if pd.notna(memory_percent):
        st.metric(
            "RAM Usage",
            f"{memory_percent:.2f}%"
        )

        st.progress(
            max(0.0, min(float(memory_percent) / 100, 1.0))
        )


    # ======================================
    # RAM ALERTING
    # ======================================

    st.subheader("RAM Alert Status")

    if pd.isna(memory_percent):
        st.error("CRITICAL: RAM metric tidak tersedia.")

    elif memory_percent >= RAM_CRITICAL_THRESHOLD:
        st.error(
            f"CRITICAL: RAM usage mencapai "
            f"{memory_percent:.2f}%. "
            f"Threshold: {RAM_CRITICAL_THRESHOLD}%."
        )

    elif memory_percent >= RAM_WARNING_THRESHOLD:
        st.warning(
            f"WARNING: RAM usage mencapai "
            f"{memory_percent:.2f}%. "
            f"Threshold: {RAM_WARNING_THRESHOLD}%."
        )

    else:
        st.success(
            f"NORMAL: RAM usage {memory_percent:.2f}%. "
            "Tidak ada indikasi penggunaan RAM tinggi."
        )


    # ======================================
    # CPU METRICS
    # ======================================

    st.divider()
    st.subheader("CPU Utilization")

    if pd.notna(selected_row["cpu_usage"]):
        st.metric(
            "CPU Usage",
            f"{selected_row['cpu_usage']:.2f}%"
        )
    else:
        st.info(
            "CPU usage belum tersedia. "
            "OID CPU untuk perangkat ini belum berhasil diverifikasi."
        )

    # ======================================
    # RAM HISTORY CHART
    # ======================================

    st.divider()
    st.subheader("RAM Usage History")

    device_snmp_history = snmp_history[
        (snmp_history["device_name"] == selected_device)
        & (snmp_history["ip_address"] == selected_row["ip_address"])
    ].copy()

    device_snmp_history = (
        device_snmp_history
        .dropna(subset=["memory_usage_percent"])
        .sort_values("checked_at")
    )

    if len(device_snmp_history) > 1:
        ram_chart = device_snmp_history.set_index(
            "checked_at"
        )[["memory_usage_percent"]]

        st.line_chart(
            ram_chart,
            y="memory_usage_percent",
            x_label="Collection Time",
            y_label="RAM Usage (%)",
            use_container_width=True
        )

    else:
        st.info(
            "Grafik RAM membutuhkan minimal dua hasil polling. "
            "Jalankan SNMP collector beberapa kali untuk "
            "membangun histori."
        )

    # ======================================
    # SNMP HISTORY TABLE
    # ======================================

    st.divider()
    st.subheader("SNMP Collection History")

    snmp_limit = st.selectbox(
        "Number of SNMP Records",
        [10, 25, 50, 100],
        key="snmp_record_limit"
    )

    snmp_table = (
        device_snmp_history
        .sort_values("checked_at", ascending=False)
        .head(snmp_limit)
        .copy()
    )

    snmp_table["checked_at"] = (
        snmp_table["checked_at"]
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    snmp_table["memory_total_mib"] = (
        snmp_table["memory_total"] / (1024 * 1024)
    ).round(2)

    snmp_table["memory_used_mib"] = (
        snmp_table["memory_used"] / (1024 * 1024)
    ).round(2)

    snmp_table["memory_free_mib"] = (
        snmp_table["memory_free"] / (1024 * 1024)
    ).round(2)

    display_columns = [
        "checked_at",
        "sys_name",
        "uptime_ticks",
        "memory_total_mib",
        "memory_used_mib",
        "memory_free_mib",
        "memory_usage_percent"
    ]

    st.dataframe(
        snmp_table[display_columns],
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"Displaying {len(snmp_table)} SNMP records "
        f"from {len(device_snmp_history)} records "
        f"for {selected_device}."
    )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "NetOps Automation Platform | "
    "Network Monitoring & SNMP Module | Version 3.0"
)
