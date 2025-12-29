import streamlit as st
import pandas as pd
import json
import os
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Keyword Crawl Dashboard", layout="wide")
st_autorefresh(interval=15000, key="refresh")

st.title("🔍 Live Keyword Crawling Dashboard")

STATUS_FILE = "crawl_status.json"
CSV_FILE = "keyword_search_results.csv"

# ================= STATUS =================
if os.path.exists(STATUS_FILE):
    with open(STATUS_FILE) as f:
        status = json.load(f)
else:
    status = {"state": "IDLE"}

st.subheader("🚦 Crawl Status")

state = status.get("state", "IDLE")
if state == "RUNNING":
    st.success("🟢 Crawl in progress")
elif state == "COMPLETED":
    st.info("✅ Crawl completed")
else:
    st.warning("⚪ Idle")

col1, col2, col3 = st.columns(3)
col1.metric("Total URLs", status.get("total_urls", 0))
col2.metric("Processed", status.get("processed", 0))
col3.metric("Matches Found", status.get("found", 0))

progress = status.get("processed", 0) / max(status.get("total_urls", 1), 1)
st.progress(progress)

st.caption("Currently Processing:")
st.code(status.get("current_url", "—"))

st.divider()

# ================= TABLE =================
st.subheader("📄 Results")

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)

    filter_option = st.selectbox(
        "Filter",
        ["All", "Found Only", "Not Found"]
    )

    if filter_option == "Found Only":
        df = df[df["Found Keyword"] == "YES"]
    elif filter_option == "Not Found":
        df = df[df["Found Keyword"] == "NO"]

    st.dataframe(df, use_container_width=True)
else:
    st.warning("CSV file not available yet")
