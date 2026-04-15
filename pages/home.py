import streamlit as st

from streamlit_helpers import ensure_session_restored

ensure_session_restored()

if st.session_state.user is None:
    st.switch_page("pages/login.py")
else:
    is_instructor = bool(st.session_state.user.get("is_instructor", False))
    target = "pages/instructor.py" if is_instructor else "pages/exam.py"
    st.switch_page(target)

st.stop()
