import datetime
import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from supabase import create_client

load_dotenv()

client = genai.Client()
MODEL_ID = "gemini-3-flash-preview"


@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_PUBLISHABLE_KEY"],
    )


def init_auth_state():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "email" not in st.session_state:
        st.session_state.email = ""
    if "code_sent" not in st.session_state:
        st.session_state.code_sent = False


def send_login_code(supabase, email: str):
    # Sends a one-time email code.
    # In Supabase Auth email template, use {{ .Token }} instead of {{ .ConfirmationURL }}.
    return supabase.auth.sign_in_with_otp({"email": email})


def verify_login_code(supabase, email: str, code: str):
    # Verify the OTP the user typed into the app.
    return supabase.auth.verify_otp(
        {
            "email": email,
            "token": code,
            "type": "email",
        }
    )


def main():
    st.set_page_config(page_title="Food Science Exam", layout="centered")
    supabase = init_supabase()
    init_auth_state()

    # Dev bypass
    with st.sidebar:
        if st.button("Dev: Skip Login"):
            st.session_state.user = {"email": "dev@test.com"}
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

                    # Store a simple logged-in marker and user info if available.
                    user = getattr(response, "user", None)
                    if user is None and getattr(response, "session", None):
                        user = getattr(response.session, "user", None)

                    st.session_state.user = user or {"email": st.session_state.email}
                    st.session_state.code_sent = False
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

    SYSTEM_PROMPT = """
    Act as a Senior Food Science Exam Proctor. The student is solving a case study about a strawberry protein bar
    turning brown (Maillard reaction).
    Follow these rules:
    1. Do NOT give away the answer.
    2. Use the 'Analytical Approach': First, they must hypothesize reactions.
    Then, they must design an experiment with an independent and dependent variable.
    3. If they propose a valid experiment, simulate the result (e.g., 'Lowering the pH slowed the browning').
    4. Grade them based on terms like 'Maillard reaction', 'reducing sugars', and 'water activity'.
    """

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
            chat = client.chats.create(
                model=MODEL_ID,
                config={"system_instruction": SYSTEM_PROMPT},
            )
            response = chat.send_message(prompt)
            ai_response = response.text

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