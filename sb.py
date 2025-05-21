import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="SQLite Viewer", layout="wide")

# --- Session State Initialization ---
if 'db_files' not in st.session_state:
    st.session_state.db_files = {}
if 'active_db' not in st.session_state:
    st.session_state.active_db = None
if 'query_tabs' not in st.session_state:
    st.session_state.query_tabs = {}
if 'query_tab_counter' not in st.session_state:
    st.session_state.query_tab_counter = 1
if 'filters' not in st.session_state:
    st.session_state.filters = {}
if 'clear_flags' not in st.session_state:
    st.session_state.clear_flags = {}

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

# --- Add Query Tab Button in Sidebar ---
if st.sidebar.button("+ Add Query Tab"):
    new_tab_name = f"Query Tab {st.session_state.query_tab_counter}"
    st.session_state.query_tabs[new_tab_name] = pd.DataFrame()
    st.session_state.query_tab_counter += 1

# --- Sidebar Filters ---
st.sidebar.header("Column Filters")
for table in selected_tables:
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

    # Initialize filters and clear flags
    if table not in st.session_state.filters:
        st.session_state.filters[table] = {col: "" for col in df.columns}
    if table not in st.session_state.clear_flags:
        st.session_state.clear_flags[table] = False

    with st.sidebar.expander(f"Filters for {table}"):
        if st.button("Clear Filters", key=f"clear_button_{table}"):
            st.session_state.clear_flags[table] = True

        # If flagged to clear, reset filters and clear flag
        if st.session_state.clear_flags[table]:
            for col in df.columns:
                st.session_state.filters[table][col] = ""
            st.session_state.clear_flags[table] = False

        # Input filters
        for col in df.columns:
            val = st.text_input(f"{table} → {col}", st.session_state.filters[table][col], key=f"filter_{table}_{col}")
            st.session_state.filters[table][col] = val

# --- Main Area Tabs for Tables + Query Tabs ---
query_tab_names = list(st.session_state.query_tabs.keys())
tabs = st.tabs(selected_tables + query_tab_names)

# --- Show Selected Tables ---
for i, table in enumerate(selected_tables):
    with tabs[i]:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

        # Apply filters
        filtered_df = df.copy()
        for col, val in st.session_state.filters[table].items():
            if val:
                filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(val, case=False, na=False)]

        st.subheader(f"Table: {table}")
        st.dataframe(filtered_df, use_container_width=True)

# --- Query Interface Tabs ---
for i, query_tab in enumerate(query_tab_names):
    with tabs[len(selected_tables) + i]:
        st.subheader(query_tab)
        query = st.text_area(f"SQL Query ({query_tab})", key=f"query_input_{query_tab}")
        if st.button(f"Execute ({query_tab})"):
            try:
                result = pd.read_sql_query(query, conn)
                st.session_state.query_tabs[query_tab] = result
            except Exception as e:
                st.error(f"Query failed: {e}")

        if not st.session_state.query_tabs[query_tab].empty:
            st.dataframe(st.session_state.query_tabs[query_tab], use_container_width=True)

conn.close()
