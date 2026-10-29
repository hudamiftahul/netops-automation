
import streamlit as st
import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_DIR / "data" / "netops.db"

st.set_page_config(
    page_title="NetOps Automation Platform",
    page_icon="🖧",
    layout="wide"
)


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


st.title("🖧 NetOps Automation Platform")
st.caption("Network Monitoring Dashboard")

if st.button("🔄 Refresh data"):
    st.cache_data.clear()

history = load_history()

if history.empty:
    st.info(
        "Belum ada riwayat monitoring. "
        "Jalankan python src\\connectivity_check.py terlebih dahulu."
    )
else:
    # Ambil status terbaru setiap perangkat
    latest = (
        history.drop_duplicates(
            subset=["device_name", "ip_address"],
            keep="first"
        )
        .copy()
    )

    online_count = int((latest["status"] == "ONLINE").sum())
    offline_count = int((latest["status"] == "OFFLINE").sum())
    total_count = len(latest)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Devices", total_count)
    col2.metric("Online", online_count)
    col3.metric("Offline", offline_count)

    st.subheader("Current Device Status")

    def highlight_status(value):
        if value == "ONLINE":
            return "color: green; font-weight: bold"
        if value == "OFFLINE":
            return "color: red; font-weight: bold"
        return ""

    st.dataframe(
        latest[
            ["device_name", "ip_address", "status", "checked_at"]
        ].style.map(
            highlight_status,
            subset=["status"]
        ),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Monitoring History")

    status_filter = st.selectbox(
        "Filter status",
        ["ALL", "ONLINE", "OFFLINE"]
    )

    filtered = history.copy()

    if status_filter != "ALL":
        filtered = filtered[
            filtered["status"] == status_filter
        ]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"Menampilkan {len(filtered)} catatan dari "
        f"{len(history)} catatan riwayat."
    )
