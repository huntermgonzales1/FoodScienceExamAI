import streamlit as st

from streamlit_helpers import (
    nav_query_params,
    render_logout_sidebar,
    require_instructor,
)

require_instructor()
render_logout_sidebar()

st.title("Educator Dashboard")
st.write("Choose an educator action:")

if st.button("Edit allowed users"):
    st.switch_page("pages/instructor_users.py")
    st.stop()
if st.button("Edit chat prompts"):
    st.switch_page("pages/instructor_prompts.py")
    st.stop()
if st.button("See student's chats/scores"):
    st.switch_page("pages/instructor_chats.py")
    st.stop()
if st.button("Practice a chat"):
    st.switch_page("pages/exam.py")
    st.stop()

st.divider()
st.page_link("pages/home.py", label="Home", query_params=nav_query_params())
