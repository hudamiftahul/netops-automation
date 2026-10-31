
import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_DIR / "data" / "netops.db"

st.set_page_config(
    page_title="NetOps Automation Platform",
    page_icon="🖧",
    layout="wide"
)


# ==========================================
# DATABASE
# ==========================================

@st.cache_data(ttl=10)
def load_history():
    if not DATABASE_FILE.exists():
        return pd.DataFrame(
            columns=[
                "checked_at",
                "device_name",
                "ip_address",
                "status"
            ]
        )

    with sqlite3.connect(DATABASE_FILE) as connection:
        return pd.read_sql_query(
            """
            SELECT checked_at, device_name, ip_address, status
            FROM monitoring_history
            ORDER BY id DESC
            """,
            connection
        )


# ==========================================
# HEADER
# ==========================================

st.title("🖧 NetOps Automation Platform")
st.caption("Network Operations & Monitoring Dashboard")

col_refresh, col_time = st.columns([1, 4])

with col_refresh:
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

history = load_history()

if history.empty:
    st.warning("No monitoring data available.")
    st.info(
        "Run the monitoring script first: "
        "python src\\connectivity_check.py"
    )
    st.stop()


# ==========================================
# DATA PROCESSING
# ==========================================

history["checked_at"] = pd.to_datetime(
    history["checked_at"],
    errors="coerce",
    utc=True
)

history = history.dropna(subset=["checked_at"])

history["checked_at"] = (
    history["checked_at"].dt.tz_convert("Asia/Jakarta")
)

latest = (
    history.sort_values("checked_at", ascending=False)
    .drop_duplicates(
        subset=["device_name", "ip_address"],
        keep="first"
    )
    .copy()
)

online_count = int((latest["status"] == "ONLINE").sum())
offline_count = int((latest["status"] == "OFFLINE").sum())
total_count = len(latest)

last_check = history["checked_at"].max()


# ==========================================
# KPI METRICS
# ==========================================

st.subheader("Monitoring Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Devices",
    total_count
)

col2.metric(
    "Online Devices",
    online_count
)

col3.metric(
    "Offline Devices",
    offline_count
)

online_percentage = (
    online_count / total_count * 100
    if total_count > 0 else 0
)

col4.metric(
    "Online Percentage",
    f"{online_percentage:.1f}%"
)

st.caption(
    f"Last monitoring recorded: {last_check.strftime('%d %b %Y, %H:%M:%S %Z')}"
)

st.divider()


# ==========================================
# CURRENT DEVICE STATUS
# ==========================================

st.subheader("🖥️ Current Device Status")

def highlight_status(value):
    if value == "ONLINE":
        return "color: #16A34A; font-weight: bold"
    elif value == "OFFLINE":
        return "color: #DC2626; font-weight: bold"
    return ""


device_table = latest[
    ["device_name", "ip_address", "status", "checked_at"]
].copy()

device_table["checked_at"] = device_table[
    "checked_at"
].dt.strftime("%Y-%m-%d %H:%M:%S")

st.dataframe(
    device_table.style.map(
        highlight_status,
        subset=["status"]
    ),
    use_container_width=True,
    hide_index=True
)


# ==========================================
# MONITORING CHART
# ==========================================

st.divider()
st.subheader("📊 Monitoring Trend")

trend = (
    history.groupby(["checked_at", "status"])
    .size()
    .unstack(fill_value=0)
)

for status in ["ONLINE", "OFFLINE"]:
    if status not in trend.columns:
        trend[status] = 0

trend = trend[["ONLINE", "OFFLINE"]].sort_index()

if len(trend) > 1:
    st.line_chart(
        trend,
        y=["ONLINE", "OFFLINE"],
        x_label="Monitoring Time",
        y_label="Number of Devices",
        use_container_width=True
    )
else:
    st.info(
        "Grafik tren membutuhkan lebih dari satu waktu pemeriksaan. "
        "Jalankan monitoring beberapa kali untuk melihat tren."
    )


# ==========================================
# MONITORING HISTORY
# ==========================================

st.divider()
st.subheader("📋 Monitoring History")

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

filtered_history = filtered_history.sort_values(
    "checked_at",
    ascending=False
).head(record_limit)

filtered_history["checked_at"] = (
    filtered_history["checked_at"]
    .dt.strftime("%Y-%m-%d %H:%M:%S")
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

st.divider()

st.caption(
    "NetOps Automation Platform | Network Monitoring Module | Version 2.0"
)
