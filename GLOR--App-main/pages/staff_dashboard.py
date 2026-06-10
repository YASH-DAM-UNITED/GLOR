import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials


import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from pathlib import Path
import pandas as pd
import time

# ---------------- PAGE CONFIG ----------------
st.set_page_config(layout="wide", page_title="GLOR Staff Dashboard")

SESSION_TIMEOUT = 30 * 60

# ---------------- CLEAN UI STYLE ----------------
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
[data-testid="stToolbar"] {display:none;}
[data-testid="stSidebar"] {display:none;}

.block-container {
    padding: 1rem 2rem;
    max-width: 1200px;
    margin: auto;
}

.stApp {
    background: linear-gradient(135deg,#eef2f7,#d6e4ff);
}

h1, h2, h3 {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div style="
    background: linear-gradient(90deg, #1f1f2e, #4b6cb7);
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 20px;
">
<h1 style='color:white; margin:0;'>GLOR Staff Dashboard</h1>
<p style='color:#e0e0e0; margin:0;'>Select Branch & Access Operations</p>
</div>
""", unsafe_allow_html=True)

# ---------------- PASSWORD FILE ----------------
FILE_NAME = Path(__file__).parent / "passwords.json"

def init_file():
    if not FILE_NAME.exists():
        with open(FILE_NAME, "w") as f:
            json.dump({"admin": "admin123"}, f)

def load_admin():
    with open(FILE_NAME, "r") as f:
        return json.load(f)

init_file()

# ---------------- SESSION STATE ----------------
defaults = {
    "authenticated": False,
    "auth_branch": None,
    "reset_mode": False,
    "selected_branch": "-- Select Branch --",
    "last_activity": None
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v




# --- HELPER FUNCTIONS FOR NOTIFICATIONS ---
# --- HELPER FUNCTIONS FOR NOTIFICATIONS ---
@st.dialog("📦 New Transfer Received")
def show_transfer_dialog(transfer):
    st.write(f"### Transfer ID: `{transfer['ID']}`")
    st.info(f"**From:** {transfer['Origin']}")
    
    st.markdown("---")
    with st.container(border=True):
        st.write("**Items to be accepted:**")
        st.text(transfer['Items']) 
        st.write(f"**Quantities:**")
        st.text(transfer['Quantities'])
    
    st.write(f"**Reason:** {transfer['Reason']}")
    
    col1, col2 = st.columns(2)
    if col1.button("✅ Accept", use_container_width=True):
        update_transfer_status(transfer['ID'], "Accepted")
        st.rerun()
    if col2.button("❌ Reject", use_container_width=True):
        update_transfer_status(transfer['ID'], "Rejected")
        st.rerun()

def update_transfer_status(transfer_id, status):
    sheet = st.session_state.gs_client.open("MASTERBRANCHSHEET").worksheet("Transfers")
    # Finding the row by ID column (Assuming 'ID' is the first column)
    cell = sheet.find(transfer_id)
    if cell:
        # Update Column 7 (Status)
        sheet.update_cell(cell.row, 7, status)
        st.success(f"Transfer {transfer_id} marked as {status}")

def check_for_pending_transfers():
    sheet = st.session_state.gs_client.open("MASTERBRANCHSHEET").worksheet("Transfers")
    records = sheet.get_all_records()
    my_branch = st.session_state.selected_branch
    
    # Filter for pending transfers where current branch is the destination
    pending = [r for r in records if r['Destination'] == my_branch and r['Status'] == 'Pending']
    
    if pending:
        # Show only the first one to avoid UI/Dialog conflicts
        show_transfer_dialog(pending[0])
# ---------------- ACTIVITY ----------------
def refresh_activity():
    st.session_state.last_activity = time.time()

# ---------------- TIMEOUT ----------------
def check_timeout():
    if st.session_state.authenticated and st.session_state.last_activity:
        if time.time() - st.session_state.last_activity > SESSION_TIMEOUT:
            st.session_state.authenticated = False
            st.session_state.auth_branch = None
            st.session_state.last_activity = None
            st.warning("⏱️ Logged out due to inactivity.")

check_timeout()



@st.cache_data(ttl=3600)  # Caches for 1 hour
def get_branch_credentials():
    # Only called if cache is empty or expired
    client = st.session_state.gs_client
    sheet = client.open("MASTERBRANCHSHEET").sheet1
    records = sheet.get_all_records()
    
    # Pre-process into a dictionary for O(1) lookup speed
    creds_map = {}
    for row in records:
        key = f"{row['BranchCode']} - {row['BranchName']}"
        creds_map[key] = {
            "password": str(row.get("Password", "")).strip(),
            "SheetID": row.get("SheetID"),
            "data": row
        }
    return records, creds_map

# Call it once at the start
all_records, branch_creds_map = get_branch_credentials()

# ---------------- SELF-HEALING GOOGLE CONNECTION ----------------
def get_fresh_client():
    creds_dict = st.secrets["GOOGLE_CREDS_JSON"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Always create a fresh credential object to avoid stale token issues
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# Ensure client exists and is fresh
if "gs_client" not in st.session_state:
    try:
        creds_dict = st.secrets["GOOGLE_CREDS_JSON"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        st.session_state.gs_client = gspread.authorize(creds)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()
# ---------------- LOAD BRANCHES & PASSWORDS (CONSOLIDATED & CACHED) ----------------
@st.cache_data(ttl=3000)
def load_master_branch_data():
    client = st.session_state.gs_client 
    sheet = client.open("MASTERBRANCHSHEET").sheet1
    records = sheet.get_all_records()
    
    passwords = {"admin": load_admin()["admin"]}
    for row in records:
        # STRIP WHITESPACE to ensure the key is clean
        code = str(row['BranchCode']).strip()
        name = str(row['BranchName']).strip()
        key = f"{code} - {name}"
        passwords[key] = str(row.get("Password", "")).strip()
        
    return records, passwords
# Fetch data securely and instantly from memory
branch_data, passwords = load_master_branch_data()
branches = [f"{b['BranchCode']} - {b['BranchName']}" for b in branch_data]

# ONLY set this if it isn't already there to avoid unnecessary processing
if "branch_list" not in st.session_state:
    st.session_state.branch_list = branches

# Fetch data securely and instantly from memory
branch_data, passwords = load_master_branch_data()
branches = [f"{b['BranchCode']} - {b['BranchName']}" for b in branch_data]
branch_options = ["-- Select Branch --"] + branches

def save_passwords(branch_key, new_password):
    # Change 'client' to 'st.session_state.gs_client'
    sheet = st.session_state.gs_client.open("MASTERBRANCHSHEET").sheet1
    records = sheet.get_all_records()

    for idx, row in enumerate(records, start=2):
        key = f"{row['BranchCode']} - {row['BranchName']}"
        if key == branch_key:
            col_index = list(row.keys()).index("Password") + 1
            sheet.update_cell(idx, col_index, new_password)
            # Clear cache so the new password takes effect immediately
            load_master_branch_data.clear()
            return

# ---------------- PIN FIRST 3 COLUMNS ----------------
st.markdown("""
<style>
div[data-testid="stDataFrame"] thead th:nth-child(1),
div[data-testid="stDataFrame"] tbody td:nth-child(1) {
    position: sticky;
    left: 0;
    background: white;
    z-index: 3;
}

div[data-testid="stDataFrame"] thead th:nth-child(2),
div[data-testid="stDataFrame"] tbody td:nth-child(2) {
    position: sticky;
    left: 150px;
    background: white;
    z-index: 2;
}

div[data-testid="stDataFrame"] thead th:nth-child(3),
div[data-testid="stDataFrame"] tbody td:nth-child(3) {
    position: sticky;
    left: 300px;
    background: white;
    z-index: 2;
}
</style>
""", unsafe_allow_html=True)

# ---------------- BRANCH SELECT ----------------
st.subheader("Select Branch")

if st.session_state.selected_branch == "-- Select Branch --":
    st.session_state.authenticated = False
    st.session_state.auth_branch = None
    st.session_state.last_activity = None

    with st.popover("Choose Branch"):
        selected_branch = st.radio("Branch List", branch_options, index=0)

        if selected_branch != "-- Select Branch --":
            st.session_state.selected_branch = selected_branch
            st.rerun()

else:
    st.success(f"Selected Branch: {st.session_state.selected_branch}")

    col1, col2= st.columns(2)

    if col1.button("🔄 Logout "):
        st.session_state.selected_branch = "-- Select Branch --"
        st.session_state.authenticated = False
        st.session_state.auth_branch = None
        st.session_state.last_activity = None
        st.rerun()
    if col2.button("🔄 Refresh "):
        st.rerun()
    





# ---------------- BRANCH INFO ----------------
branch_info = None

if st.session_state.selected_branch != "-- Select Branch --":
    branch_info = next(
        b for b in branch_data
        if f"{b['BranchCode']} - {b['BranchName']}" == st.session_state.selected_branch
    )

# ---------------- MAIN ----------------
if st.session_state.selected_branch != "-- Select Branch --":

    if not st.session_state.authenticated:
        st.subheader("Branch Login")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            # Retrieve specific branch info from the cached map
            branch_data = branch_creds_map.get(st.session_state.selected_branch)
            
            if branch_data and branch_data["password"] == password:
                st.session_state.authenticated = True
                st.session_state.auth_branch = st.session_state.selected_branch
                st.session_state.last_activity = time.time()
                
                # Assign cached data directly to state
                st.session_state.sheet_id = branch_data["SheetID"]
                st.session_state.branch_info = branch_data["data"]
                st.rerun()
            else:
                st.error("Incorrect password")

    # ---------------- RESET PASSWORD ----------------
    if st.session_state.reset_mode:
        st.subheader("Reset Password")
        admin_pass = st.text_input("Admin Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Update Password"):
            if admin_pass == load_admin()["admin"]:
                save_passwords(st.session_state.selected_branch, new_pass)
                st.success("Password updated successfully")
                st.session_state.reset_mode = False
            else:
                st.error("Wrong admin password")

# ---------------- AFTER LOGIN ----------------
if st.session_state.authenticated:
    st.success(f"Logged in: {st.session_state.selected_branch}")
    
    # Check for transfers immediately upon login
    check_for_pending_transfers()
    
    col1, col2, col3, col4 = st.columns(4)

    if col1.button("📦 Stock Record"):
        refresh_activity()
        st.switch_page("pages/stock_consumption.py")

    if col2.button("📅 Staff Schedule"):
        refresh_activity()
        st.switch_page("pages/staff_schedule.py")
        
    if col3.button("🔍 Stock View"):
        st.session_state.show_stock_view = not st.session_state.get("show_stock_view", False)
        refresh_activity()
        

    if col4.button("📦 Stock Transfer Internal"):
        st.switch_page("pages/stock_transfer.py")

# ---------------- STOCK VIEW SECTION ----------------
if st.session_state.get("show_stock_view", False):
    if branch_info is not None:
        with st.spinner("Fetching live stock data..."):
            sheet = st.session_state.gs_client.open_by_key(branch_info["SheetID"])
            ws = sheet.worksheet("Stocks")
            data = ws.get_all_values()
            
            if len(data) < 2:
                st.warning("Stock sheet is empty.")
            else:
                # 1. Convert to DataFrame
                headers = data[0]
                df = pd.DataFrame(data[1:], columns=headers)
                
                # 2. Clean data: Convert columns from index 3 onwards to numeric
                # This prevents issues with empty strings or formatting
                data_cols = df.columns[3:]
                for col in data_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # 3. Calculate Total
                df["Total"] = df[data_cols].sum(axis=1)
                
                # 4. Split by section (Assuming a marker row like "Daily Item" exists)
                # We identify where the sections break
                daily_mask = df.iloc[:, 0].str.lower().str.contains("daily item", na=False)
                weekly_mask = df.iloc[:, 0].str.lower().str.contains("weekly item", na=False)
                
                # Find indices to slice the dataframe
                daily_idx = df.index[daily_mask].tolist()
                weekly_idx = df.index[weekly_mask].tolist()
                
                start_daily = daily_idx[0] + 1 if daily_idx else 0
                start_weekly = weekly_idx[0] + 1 if weekly_idx else len(df)
                
                # Slice and remove empty/marker rows
                daily_df = df.iloc[start_daily:start_weekly].dropna(subset=[df.columns[0]])
                weekly_df = df.iloc[start_weekly:].dropna(subset=[df.columns[0]])
                
                # 5. Display
                st.subheader("📦 Daily Items Stock")
                st.dataframe(daily_df, use_container_width=True, height=400)
                
                st.subheader("📦 Weekly Items Stock")
                st.dataframe(weekly_df, use_container_width=True, height=400)
                
                # Save for other pages
                st.session_state.current_stocks = {
                    "daily": daily_df.to_dict('records'), 
                    "weekly": weekly_df.to_dict('records')
                }
    else:
        st.session_state.show_stock_view = False
        st.rerun()

# --- REPLACE THIS ENTIRE FUNCTION ---
def check_notifications():
    # Use the session_state client to avoid 'client' not defined errors
    sheet = st.session_state.gs_client.open("MASTERBRANCHSHEET").worksheet("Notifications")
    records = sheet.get_all_records()
    
    # Safely handle the string splitting
    branch_val = st.session_state.selected_branch
    if "--" in branch_val: return 
    
    my_code = branch_val.split(" - ")[0]
    
    # Filter for unread
    unread = [r for r in records if str(r['TargetBranchCode']) == my_code and r['Status'] == 'unread']
    
    for note in unread:
        st.toast(f"📦 Incoming Transfer: {note['Message']}", icon="🔔")


# ---------------- BACK ----------------
if st.button("⬅ Back"):
    st.switch_page("app.py")
