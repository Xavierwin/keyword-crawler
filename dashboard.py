import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Keyword Search Dashboard", layout="wide")

st.title("🔍 Keyword Search Dashboard")

CSV_FILE = "keyword_search_results.csv"

if not os.path.exists(CSV_FILE):
    st.warning("CSV file not found. Run crawler first.")
    st.stop()

df = pd.read_csv(CSV_FILE)

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total URLs", len(df))
col2.metric("Matches Found", df[df["Found Keyword"] == "YES"].shape[0])
col3.metric("PDF Matches", df[df["Type"] == "PDF"].shape[0])

st.divider()

# Filters
keyword_filter = st.selectbox("Filter", ["All", "Found Only", "Not Found"])

if keyword_filter == "Found Only":
    df = df[df["Found Keyword"] == "YES"]
elif keyword_filter == "Not Found":
    df = df[df["Found Keyword"] == "NO"]

st.dataframe(df, use_container_width=True)
