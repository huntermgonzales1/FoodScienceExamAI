import streamlit as st

from streamlit_helpers import ensure_session_restored, switch_page_with_sid

ensure_session_restored()

if st.session_state.user is None:
    switch_page_with_sid("pages/login.py")
else:
    is_instructor = bool(st.session_state.user.get("is_instructor", False))
    target = "pages/instructor.py" if is_instructor else "pages/exam.py"
    switch_page_with_sid(target)

st.stop()
