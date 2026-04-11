import streamlit as st

from streamlit_helpers import (
    nav_query_params_with_sid,
    render_logout_sidebar,
    require_instructor,
    switch_page_with_sid,
)

require_instructor()
render_logout_sidebar()

st.title("Educator Dashboard")
st.write("Choose an educator action:")

if st.button("Edit allowed users"):
    switch_page_with_sid("pages/instructor_users.py")
    st.stop()
if st.button("Edit chat prompts"):
    switch_page_with_sid("pages/instructor_prompts.py")
    st.stop()
if st.button("See student's chats/scores"):
    switch_page_with_sid("pages/instructor_chats.py")
    st.stop()
if st.button("Practice a chat"):
    switch_page_with_sid("pages/exam.py")
    st.stop()

st.divider()
st.page_link("pages/home.py", label="Home", query_params=nav_query_params_with_sid())
