import uuid

import streamlit as st
from dotenv import load_dotenv

from database import (
    CHAT_STATUS_ACTIVE,
    CHAT_STATUS_GRADED,
    auth_store,
    create_chat_message,
    get_current_chat_for_prompt,
    get_chat_messages,
    get_prompt_question,
    init_admin_supabase,
    init_authenticated_supabase,
    init_supabase,
    send_login_code,
    update_chat_grade,
    verify_login_code,
)
from streamlit_helpers import (
    clear_query_params,
    get_query_params,
    init_auth_state,
    restore_session_from_sid,
    set_query_param,
)
from tools import get_gemini_response, grade_chat_with_gemini

load_dotenv()
PROMPT_ID = "21b23642-6bf2-4777-bef0-394c2aafb071"
DEFAULT_GRADING_PROMPT = (
    "Score this submission from 0 to 10. Reward scientifically grounded reasoning, "
    "good use of the case facts, clear experimental design, and actionable next "
    "steps. Penalize vague claims, unsupported conclusions, or missing justification."
)


def main():
    st.set_page_config(page_title="Food Science Exam", layout="centered")
    supabase = init_supabase()
    init_auth_state()

    # Restore login after refresh
    restore_session_from_sid()

    # Dev bypass
    with st.sidebar:
        if st.button("Dev: Skip Login"):
            st.session_state.user = {"email": "dev@test.com", "id": None}
            st.session_state.supabase_session = None
            sid = uuid.uuid4().hex
            auth_store()[sid] = {"email": "dev@test.com", "user": None, "session": None}
            set_query_param("sid", sid)
            st.rerun()

        if st.session_state.user is not None and st.button("Logout"):
            params = get_query_params()
            sid = params.get("sid")
            if sid and sid in auth_store():
                del auth_store()[sid]
            st.session_state.user = None
            st.session_state.email = ""
            st.session_state.code_sent = False
            clear_query_params()
            st.rerun()

    # Auth gate
    if st.session_state.user is None:
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
            return

        st.write(f"Code sent to **{st.session_state.email}**")
        code = st.text_input("Enter 6-digit code", max_chars=12)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Verify Code"):
                code = code.strip()

                if not code:
                    st.warning("Enter the code from your email.")
                    st.stop()

                # In the 'with col1:' block of your modified app.py
                try:
                    response = verify_login_code(supabase, st.session_state.email, code)
                    user = getattr(response, "user", None)
                    
                    # 1. GET THE AUTHORIZATION STATUS FROM METADATA
                    # This matches the 'is_authorized' key we set in the SQL trigger
                    app_metadata = getattr(user, "app_metadata", {})
                    is_authorized = app_metadata.get("is_authorized", False)

                    # 2. THE GATEKEEPER
                    if not is_authorized:
                        st.error("Access Denied: Your email is not on the authorized whitelist.")
                        st.stop() # Stops execution before any session is saved

                    # 3. IF AUTHORIZED, PROCEED
                    sid = uuid.uuid4().hex
                    auth_store()[sid] = {
                        "email": st.session_state.email,
                        "user": user,
                        "session": getattr(response, "session", None),
                    }

                    st.session_state.user = {
                        "email": st.session_state.email,
                        "id": getattr(user, "id", None),
                    }
                    st.session_state.supabase_session = getattr(response, "session", None)
                    st.session_state.code_sent = False
                    set_query_param("sid", sid)
                    st.rerun()

                except Exception as e:
                    st.error(f"Login failed: {e}")

        with col2:
            if st.button("Resend Code"):
                try:
                    send_login_code(supabase, st.session_state.email)
                    st.success("New code sent.")
                except Exception as e:
                    st.error(f"Error resending code: {e}")

        return

    session = st.session_state.supabase_session
    access_token = getattr(session, "access_token", None)
    user_id = st.session_state.user.get("id") if st.session_state.user else None

    if not access_token or not user_id:
        st.error("A valid Supabase session is required to load and save chats. Please log in with email instead of using the dev bypass.")
        return

    db = init_authenticated_supabase(access_token)
    admin_db = init_admin_supabase()

    try:
        prompt_question = get_prompt_question(db, PROMPT_ID)
        current_chat = get_current_chat_for_prompt(db, user_id, PROMPT_ID)
        chat_messages = get_chat_messages(db, current_chat["chat_id"])
    except Exception as e:
        st.error(f"Error loading exam data: {e}")
        return

    st.session_state.chat_id = current_chat["chat_id"]
    st.session_state.messages = [
        {"role": message["role"], "content": message["content"]}
        for message in chat_messages
    ]

    st.title("Food Science Lab: Case Study Exam")
    st.subheader("Scenario: The Browning Strawberry Bar")
    st.info(prompt_question["scenario_text"])
    st.write(prompt_question["info_text"])

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if current_chat["status"] == CHAT_STATUS_GRADED:
        st.success(f"Final grade: {current_chat['final_grade']}/10")
        st.write(current_chat["grade_justification"])
        st.info(
            "This exam attempt has been finalized and can no longer receive new "
            "messages. If you believe this grading was unreasonable, please contact "
            "your professor."
        )

    chat_is_active = current_chat["status"] == CHAT_STATUS_ACTIVE

    if prompt := st.chat_input(
        "What is your hypothesis or proposed experiment?",
        disabled=not chat_is_active,
    ):
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            create_chat_message(db, st.session_state.chat_id, "user", prompt)
            ai_response = get_gemini_response(
                prompt=prompt,
                system_instruction=prompt_question["system_instruction"],
                messages=st.session_state.messages[:-1],
            )
            create_chat_message(db, st.session_state.chat_id, "assistant", ai_response)

            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)

        except Exception as e:
            st.error(f"Error calling Gemini: {e}")

    with st.sidebar:
        st.header("Exam Controls")
        if current_chat["status"] == CHAT_STATUS_GRADED:
            st.caption("This attempt has already been finalized and graded.")

        finalize_disabled = (not chat_is_active) or (len(st.session_state.messages) == 0)
        if st.button("Finalize and Grade", disabled=finalize_disabled):
            with st.spinner("Sending the full transcript to Gemini for grading..."):
                try:
                    grading_result = grade_chat_with_gemini(
                        prompt_question=prompt_question,
                        messages=st.session_state.messages,
                        grading_prompt=DEFAULT_GRADING_PROMPT,
                    )
                    updated_chat = update_chat_grade(
                        admin_db,
                        st.session_state.chat_id,
                        final_grade=grading_result["grade"],
                        grade_justification=grading_result["justification"],
                    )
                    st.success(
                        f"Saved grade {updated_chat['final_grade']}/10 to the database."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error finalizing and grading chat: {e}")


if __name__ == "__main__":
    main()
