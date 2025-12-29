import streamlit as st
import pandas as pd
import json
import os
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Keyword Crawl Dashboard", layout="wide")
st_autorefresh(interval=15000, key="refresh")

CONFIG_FILE = "search_config.json"
STATUS_FILE = "crawl_status.json"
CSV_FILE = "keyword_search_results.csv"

st.title("🔍 Keyword Search Dashboard")

# ===== USER INPUT =====
st.subheader("🔑 Search Keyword")

keyword = st.text_input("Enter keyword to search")

if st.button("Save keyword"):
    if keyword.strip():
        with open(CONFIG_FILE, "w") as f:
            json.dump({"search_keyword": keyword.strip()}, f, indent=2)
        st.success("Keyword saved. Trigger crawler from GitHub Actions.")
    else:
        st.warning("Keyword cannot be empty")

st.divider()

# ===== STATUS =====
if os.path.exists(STATUS_FILE):
    with open(STATUS_FILE) as f:
        status = json.load(f)
else:
    status = {"state": "IDLE"}

state = status.get("state", "IDLE")

st.subheader("🚦 Crawl Status")

if state == "RUNNING":
    st.success(f"🟢 Running (Keyword: {status.get('keyword')})")
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

st.caption("Currently processing:")
st.code(status.get("current_url", "—"))

st.divider()

# ===== RESULTS =====
st.subheader("📄 Results")

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("No results yet")
