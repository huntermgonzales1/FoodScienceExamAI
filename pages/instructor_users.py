import streamlit as st

from database import init_authenticated_supabase, list_allowed_emails, upsert_allowed_email
from streamlit_helpers import (
    nav_query_params_with_sid,
    render_logout_sidebar,
    require_instructor,
)

require_instructor()
render_logout_sidebar()

st.page_link(
    "pages/instructor.py",
    label="Back to Instructor Dashboard",
    query_params=nav_query_params_with_sid(),
)
st.title("Edit Allowed Users")

session = st.session_state.supabase_session
access_token = getattr(session, "access_token", None)
if not access_token:
    st.error("A valid Supabase session is required. Please log in again.")
    st.page_link("pages/login.py", label="Go to Login", query_params=nav_query_params_with_sid())
    st.stop()

db = init_authenticated_supabase(access_token)

try:
    rows = list_allowed_emails(db)
except Exception as e:
    st.error(f"Error loading allowed users: {e}")
    st.stop()

display_rows = [
    {
        "email": row.get("email", ""),
        "expiration_date": row.get("expiration_date") or "Never",
        "is_instructor": bool(row.get("is_instructor", False)),
    }
    for row in rows
]

st.subheader("Current Allowed Users")
if display_rows:
    st.dataframe(display_rows, width="stretch", hide_index=True)
else:
    st.info("No allowed users found.")

st.subheader("Add or Update Allowed User")
with st.form("upsert_allowed_user_form", clear_on_submit=True):
    email = st.text_input("Email")
    is_instructor = st.checkbox("Instructor", value=False)
    never_expires = st.checkbox("Never expires", value=True)
    expiration_date = st.date_input("Expiration date", disabled=never_expires)
    submitted = st.form_submit_button("Save")

if submitted:
    clean_email = email.strip().lower()
    if not clean_email:
        st.warning("Please enter an email.")
        st.stop()

    expiration_value = None if never_expires else expiration_date.isoformat()

    try:
        upsert_allowed_email(
            db,
            email=clean_email,
            expiration_date=expiration_value,
            is_instructor=is_instructor,
        )
        st.success(f"Saved allowed user: {clean_email}")
        st.rerun()
    except Exception as e:
        st.error(f"Error saving allowed user: {e}")
