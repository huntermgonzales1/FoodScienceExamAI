import streamlit as st
from datetime import date

from database import init_authenticated_supabase, list_allowed_emails, upsert_allowed_email
from streamlit_helpers import (
    nav_query_params_with_sid,
    render_backend_error,
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
    render_backend_error("load allowed users", e, key_prefix="instructor_users_load")
    st.stop()

rows_by_email = {row.get("email", ""): row for row in rows if row.get("email")}
selected_key = "instructor_users_selected_email"

if selected_key not in st.session_state:
    st.session_state[selected_key] = None


def load_user_into_form(row: dict):
    expiration = row.get("expiration_date")
    st.session_state["instructor_users_form_email"] = row.get("email", "")
    st.session_state["instructor_users_form_is_instructor"] = bool(
        row.get("is_instructor", False)
    )
    st.session_state["instructor_users_form_never_expires"] = expiration is None
    st.session_state["instructor_users_form_expiration_date"] = (
        date.fromisoformat(expiration) if expiration else date.today()
    )

display_rows = [
    {
        "email": row.get("email", ""),
        "expiration_date": row.get("expiration_date") or "Never",
        "is_instructor": bool(row.get("is_instructor", False)),
    }
    for row in rows
]

st.subheader("Current Allowed Users")
selected_email = st.session_state[selected_key]
selected_row = rows_by_email.get(selected_email) if selected_email else None

if selected_row:
    st.info(f"Showing details for: {selected_email}")
    st.dataframe([selected_row], width="stretch", hide_index=True)
    if st.button("Back to full table"):
        st.session_state[selected_key] = None
        st.rerun()
elif display_rows:
    st.dataframe(display_rows, width="stretch", hide_index=True)
    selected_option = st.selectbox(
        "Select an existing user to view/edit",
        options=[""] + list(rows_by_email.keys()),
        format_func=lambda x: "Choose a user..." if x == "" else x,
    )
    if st.button("Open Selected User"):
        if not selected_option:
            st.warning("Choose a user first.")
            st.stop()
        st.session_state[selected_key] = selected_option
        load_user_into_form(rows_by_email[selected_option])
        st.rerun()
else:
    st.info("No allowed users found.")

st.subheader("Add or Update Allowed User")
st.session_state.setdefault("instructor_users_form_email", "")
st.session_state.setdefault("instructor_users_form_is_instructor", False)
st.session_state.setdefault("instructor_users_form_never_expires", True)
st.session_state.setdefault("instructor_users_form_expiration_date", date.today())

email = st.text_input("Email", key="instructor_users_form_email")
is_instructor = st.checkbox("Instructor", key="instructor_users_form_is_instructor")
never_expires = st.checkbox("Never expires", key="instructor_users_form_never_expires")
expiration_date = st.date_input(
    "Expiration date",
    key="instructor_users_form_expiration_date",
    disabled=never_expires,
)
submitted = st.button("Save")

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
        render_backend_error("save allowed user", e, key_prefix="instructor_users_save")
