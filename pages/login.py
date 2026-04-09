import uuid

import streamlit as st

from database import (
    auth_store,
    get_user_is_instructor,
    init_authenticated_supabase,
    init_supabase,
    send_login_code,
    verify_login_code,
)
from streamlit_helpers import (
    ensure_session_restored,
    nav_query_params_with_sid,
    render_logout_sidebar,
)

ensure_session_restored()

if st.session_state.user is not None:
    render_logout_sidebar()
    st.title("Already Logged In")
    is_instructor = bool(st.session_state.user.get("is_instructor", False))
    st.info("Your session is active.")
    st.page_link("pages/home.py", label="Go to Home", query_params=nav_query_params_with_sid())
    if is_instructor:
        st.page_link(
            "pages/instructor.py",
            label="Go to Instructor Dashboard",
            query_params=nav_query_params_with_sid(),
        )
    else:
        st.page_link("pages/exam.py", label="Go to Exam", query_params=nav_query_params_with_sid())
    st.stop()

supabase = init_supabase()

st.title("Student Login")

if not st.session_state.code_sent:
    email = st.text_input("University Email", value=st.session_state.email)

    if st.button("Send Code"):
        email = email.strip().lower()

        if not email:
            st.warning("Enter your email first.")
            st.stop()

        try:
            send_login_code(supabase, email)
            st.session_state.email = email
            st.session_state.code_sent = True
            st.success("Code sent! Check your email and enter it below.")
            st.rerun()
        except Exception as e:
            st.error(f"Error sending code: {e}")
    st.stop()

st.write(f"Code sent to **{st.session_state.email}**")
code = st.text_input("Enter 6-digit code", max_chars=12)

col1, col2 = st.columns(2)

with col1:
    if st.button("Verify Code"):
        code = code.strip()

        if not code:
            st.warning("Enter the code from your email.")
            st.stop()

        try:
            response = verify_login_code(supabase, st.session_state.email, code)
            user = getattr(response, "user", None)
            session = getattr(response, "session", None)

            app_metadata = getattr(user, "app_metadata", {})
            is_authorized = app_metadata.get("is_authorized", False)

            if not is_authorized:
                st.error("Access Denied: Your email is not on the authorized whitelist.")
                st.stop()

            user_id = getattr(user, "id", None)
            access_token = getattr(session, "access_token", None)
            if not user_id or not access_token:
                st.error("Login succeeded but session details are missing. Please try again.")
                st.stop()

            is_instructor = bool(app_metadata.get("is_instructor", False))
            try:
                db = init_authenticated_supabase(access_token)
                is_instructor = get_user_is_instructor(db, user_id)
            except Exception:
                # Fall back to JWT metadata so login still succeeds if profile RLS is misconfigured.
                pass

            sid = uuid.uuid4().hex
            auth_store()[sid] = {
                "email": st.session_state.email,
                "user": user,
                "session": session,
                "is_instructor": is_instructor,
            }

            st.session_state.user = {
                "email": st.session_state.email,
                "id": user_id,
                "is_instructor": is_instructor,
            }
            st.session_state.supabase_session = session
            st.session_state.is_instructor = is_instructor
            st.session_state.code_sent = False

            target = "pages/instructor.py" if is_instructor else "pages/exam.py"
            st.switch_page(target, query_params={"sid": sid})
        except Exception as e:
            st.error(f"Login failed: {e}")

with col2:
    if st.button("Resend Code"):
        try:
            send_login_code(supabase, st.session_state.email)
            st.success("New code sent.")
        except Exception as e:
            st.error(f"Error resending code: {e}")
