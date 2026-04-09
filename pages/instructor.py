import streamlit as st

from streamlit_helpers import nav_query_params_with_sid, render_logout_sidebar, require_instructor

require_instructor()
render_logout_sidebar()

st.title("Educator Dashboard")
st.write("Choose an educator action:")

st.button("Edit allowed users")
st.button("Edit chat prompts")
st.button("See student's chats/scores")
st.button("Practice a chat")

st.divider()
st.page_link("pages/home.py", label="Home", query_params=nav_query_params_with_sid())
st.page_link("pages/exam.py", label="Go to Exam", query_params=nav_query_params_with_sid())
