import datetime
import uuid

import streamlit as st
from dotenv import load_dotenv

from database import auth_store, init_supabase, send_login_code, verify_login_code
from tools import get_gemini_response

load_dotenv()


def init_auth_state():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "email" not in st.session_state:
        st.session_state.email = ""
    if "code_sent" not in st.session_state:
        st.session_state.code_sent = False


def get_query_params() -> dict:
    try:
        qp = st.query_params
        return {k: qp[k] for k in qp.keys()}
    except Exception:
        qp = st.experimental_get_query_params()
        return {k: (v[0] if isinstance(v, list) and v else "") for k, v in qp.items()}


def set_query_param(key: str, value: str):
    try:
        st.query_params[key] = value
    except Exception:
        # Older Streamlit
        params = st.experimental_get_query_params()
        params[key] = value
        st.experimental_set_query_params(**params)


def clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()


def restore_session_from_sid():
    params = get_query_params()
    sid = params.get("sid")
    if not sid:
        return

    saved = auth_store().get(sid)
    if not saved:
        return

    st.session_state.user = {"email": saved["email"]}
    st.session_state.email = saved["email"]


def main():
    st.set_page_config(page_title="Food Science Exam", layout="centered")
    supabase = init_supabase()
    init_auth_state()

    # Restore login after refresh
    restore_session_from_sid()

    # Dev bypass
    with st.sidebar:
        if st.button("Dev: Skip Login"):
            st.session_state.user = {"email": "dev@test.com"}
            sid = uuid.uuid4().hex
            auth_store()[sid] = {"email": "dev@test.com"}
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

                try:
                    response = verify_login_code(
                        supabase,
                        st.session_state.email,
                        code,
                    )

                    # Save a server-side session keyed by a browser-visible sid
                    sid = uuid.uuid4().hex

                    # Store only what you need
                    auth_store()[sid] = {
                        "email": st.session_state.email,
                        "user": getattr(response, "user", None),
                        "session": getattr(response, "session", None),
                    }

                    st.session_state.user = {"email": st.session_state.email}
                    st.session_state.code_sent = False
                    set_query_param("sid", sid)
                    clear_query_params()  # if you want to remove the OTP code from the URL
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

    # Rest of page logic once logged in
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "log_file" not in st.session_state:
        st.session_state.log_file = f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    st.title("Food Science Lab: Case Study Exam")
    st.subheader("Scenario: The Browning Strawberry Bar")
    st.info("""
    **Complaint:** A strawberry bar turns brown and tastes 'toasted' after storage.
    **Ingredients:** Whey protein, strawberry purée, cane sugar, honey, pH 6.0, Aw 0.55.
    """)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is your hypothesis or proposed experiment?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with open(st.session_state.log_file, "a") as f:
            f.write(f"USER: {prompt}\n")

        try:
            ai_response = get_gemini_response(prompt)

            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)

            with open(st.session_state.log_file, "a") as f:
                f.write(f"AI: {ai_response}\n\n")

        except Exception as e:
            st.error(f"Error calling Gemini: {e}")

    with st.sidebar:
        st.header("Admin Controls")
        if st.button("Finalize and Grade"):
            st.warning("Sending full transcript to Gemini for grading...")
            # Grading logic would go here


if __name__ == "__main__":
    main()
