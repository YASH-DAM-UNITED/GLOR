import streamlit as st
import time
import streamlit.components.v1 as components

# =========================================================
# SYSTEM CONFIG
# =========================================================
st.set_page_config(page_title="GLOR Portal", layout="wide", initial_sidebar_state="collapsed")

# Session States
if "lang" not in st.session_state: st.session_state.lang = "en"
if "show_mgmt_password" not in st.session_state: st.session_state.show_mgmt_password = False
if "mgmt_lock_until" not in st.session_state: st.session_state.mgmt_lock_until = 0
if "show_hr_password" not in st.session_state: st.session_state.show_hr_password = False

texts = {
    "en": {"title": "G L O R ", "sub": "Operations management <br>just got easier.", "desc": "Welcome to the central command unit for GLOR.", "btn_staff": "Staff Access →"},
    "ar": {"title": "بـارت", "sub": "إدارة العمليات <br>أصبحت أسهل.", "desc": "أهلاً بك في وحدة التحكم المركزية لـ GLOR.", "btn_staff": "وصول الموظفين ←"}
}
T = texts[st.session_state.lang]

# =========================================================
# CARAMEL CSS ARCHITECTURE
# =========================================================
st.markdown("""<style>
:root {
    --caramel-primary: #C68E17;
    --caramel-accent: #A07513;
    --caramel-soft: #FDF5E6;
    --text-dark: #5D4037;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
.stApp { background-color: var(--caramel-soft) !important; }
h1, h2, h3, p { color: var(--text-dark) !important; }

.glor-logo { 
    background: linear-gradient(90deg, var(--caramel-primary) 0%, var(--caramel-accent) 100%) !important;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900 !important;
}
.registered { color: var(--caramel-primary) !important; font-size: 26px; font-weight: 900; }

.card-glow { position: relative; padding: 2px; background: #FFFFFF; border-radius: 22px; box-shadow: 0 10px 15px -3px rgba(198, 142, 23, 0.1); }
.card-glow::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(transparent, var(--caramel-primary), transparent 30%); animation: rotate 4s linear infinite; }
.card-content { position: relative; background: #FFFFFF; border-radius: 20px; padding: 30px; }

div.stButton > button { 
    background: var(--caramel-primary) !important;
    color: white !important;
    border-radius: 50px !important;
    font-weight: 900 !important;
    text-transform: uppercase !important;
    transition: all 0.4s ease !important;
}
div.stButton > button:hover { background: var(--caramel-accent) !important; box-shadow: 0 10px 20px rgba(160, 117, 19, 0.3) !important; }
@keyframes rotate { 100% { transform: rotate(360deg); } }
</style>""", unsafe_allow_html=True)

# =========================================================
# UI RENDERING
# =========================================================
lang_col1, lang_col2 = st.columns([10, 1])
with lang_col2:
    if st.button("🌐"):
        st.session_state.lang = "ar" if st.session_state.lang == "en" else "en"
        st.rerun()

st.markdown(f"<h1 style='text-align: center;'><span class='glor-logo'>{T['title']}</span><span class='registered'>®</span></h1>", unsafe_allow_html=True)
st.markdown(f"<h1 style='text-align: center;'>{T['sub']}</h1>", unsafe_allow_html=True)

# Grid Layout
grid_left, grid_center, grid_right = st.columns(3, gap="large")

with grid_left:
    st.markdown("<div class='card-glow'><div class='card-content'><h3>Staff DashBoard</h3>", unsafe_allow_html=True)
    if st.button(T['btn_staff'], use_container_width=True): st.switch_page("pages/staff_dashboard.py")
    st.markdown("</div></div>", unsafe_allow_html=True)

with grid_center:
    st.markdown("<div class='card-glow'><div class='card-content'><h3>HR DashBoard</h3>", unsafe_allow_html=True)
    if st.button("HR Access →", use_container_width=True): st.session_state.show_hr_password = True
    st.markdown("</div></div>", unsafe_allow_html=True)

with grid_right:
    st.markdown("<div class='card-glow'><div class='card-content'><h3>Admin DashBoard</h3>", unsafe_allow_html=True)
    if time.time() < st.session_state.mgmt_lock_until:
        st.button("Console Locked 🔒", disabled=True, use_container_width=True)
    elif st.button("Admin Access →", use_container_width=True):
        st.session_state.show_mgmt_password = True
    st.markdown("</div></div>", unsafe_allow_html=True)

# =========================================================
# SECURITY FORMS
# =========================================================
if st.session_state.show_hr_password:
    with st.form("hr_form"):
        pwd = st.text_input("HR Password", type="password")
        if st.form_submit_button("Verify"):
            if pwd == st.secrets["HR_PASSWORD"]: st.switch_page("pages/staff_schedule.py")
            else: st.error("Invalid token")

if st.session_state.show_mgmt_password:
    with st.form("admin_form"):
        pwd = st.text_input("Admin Password", type="password")
        if st.form_submit_button("Verify"):
            if pwd == st.secrets["MANAGER_PASSWORD"]: st.switch_page("pages/management_dashboard.py")
            else: st.error("Invalid token")
