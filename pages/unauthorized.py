import streamlit as st

from streamlit_helpers import ensure_session_restored, nav_query_params, render_logout_sidebar

ensure_session_restored()
render_logout_sidebar()

st.title("Unauthorized")
st.error("You do not have permission to view this page.")
st.page_link("pages/home.py", label="Return to Home", query_params=nav_query_params())
