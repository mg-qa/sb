import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import os

# Increase file upload limit to 3GB

st.set_page_config(page_title="SQLite Viewer", layout="wide")

# # --- Theme and Text Size Switch ---
# st.markdown("""
#     <style>
#     .dark-mode {
#         background-color: #121212;
#         color: white;
#     }
#     .light-mode {
#         background-color: white;
#         color: black;
#     }
#     .large-text {
#         font-size: 36px;
#     }
#     .medium-text {
#         font-size: 16px;
#     }
#     .small-text {
#         font-size: 14px;
#     }
#     </style>
# """, unsafe_allow_html=True)

# --- Sidebar Settings ---
# st.sidebar.title("Settings")
# theme = st.sidebar.selectbox("Choose Theme", ["Light", "Dark"])
# text_size = st.sidebar.selectbox("Text Size", ["Medium", "Large", "Small"])

# body_class = f"{'dark-mode' if theme == 'Dark' else 'light-mode'} {'large-text' if text_size == 'Large' else 'small-text' if text_size == 'Small' else 'medium-text'}"
# st.markdown(f"<body class='{body_class}'>", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'db_files' not in st.session_state:
    st.session_state.db_files = {}
if 'active_db' not in st.session_state:
    st.session_state.active_db = None
if 'query_tabs' not in st.session_state:
    st.session_state.query_tabs = {}

# --- File Uploader ---
st.sidebar.header("Upload SQLite Files")
uploaded_files = st.sidebar.file_uploader(
    "Upload SQLite DBs (with or without extensions)", type=None, accept_multiple_files=True
)

# Save uploaded files to session state
def load_databases():
    temp_dir = os.path.join(os.getcwd(), "uploaded_dbs")
    os.makedirs(temp_dir, exist_ok=True)

    for file in uploaded_files:
        if file.name not in st.session_state.db_files:
            db_path = os.path.join(temp_dir, file.name)
            with open(db_path, 'wb') as f:
                f.write(file.read())
            try:
                test_conn = sqlite3.connect(db_path)
                test_conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
                test_conn.close()
                st.session_state.db_files[file.name] = db_path
            except sqlite3.DatabaseError:
                st.warning(f"'{file.name}' is not a valid SQLite database.")

load_databases()

# --- Database Selector ---
st.sidebar.header("Databases")
db_names = list(st.session_state.db_files.keys())
if db_names:
    selected_db = st.sidebar.radio("Select Active DB", db_names)
    st.session_state.active_db = selected_db
else:
    st.warning("Upload at least one SQLite database file.")
    st.stop()

# --- Sidebar Table List ---
conn = sqlite3.connect(st.session_state.db_files[st.session_state.active_db])
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

st.sidebar.header("Tables")
selected_tables = st.sidebar.multiselect("Choose tables to view", tables)

# --- Main Area Tabs for Tables ---
tabs = st.tabs(selected_tables + ["+ New Query Tab"])

# --- Show Selected Tables ---
for i, table in enumerate(selected_tables):
    with tabs[i]:
        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 1000", conn)
        st.subheader(f"Table: {table}")
        st.dataframe(df, use_container_width=True)

# --- Query Interface ---
query_tab_index = len(selected_tables)
with tabs[query_tab_index]:
    new_query_name = st.text_input("Query Tab Name", "Query 1")
    query = st.text_area("SQL Query")
    if st.button("Execute Query"):
        try:
            result = pd.read_sql_query(query, conn)
            st.session_state.query_tabs[new_query_name] = result
        except Exception as e:
            st.error(f"Query failed: {e}")

# --- Display Executed Query Tabs ---
if st.session_state.query_tabs:
    st.header("Query Results")
    for name, result_df in st.session_state.query_tabs.items():
        with st.expander(name):
            st.dataframe(result_df, use_container_width=True)

conn.close()
