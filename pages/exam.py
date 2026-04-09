import streamlit as st

from database import (
    CHAT_STATUS_ACTIVE,
    CHAT_STATUS_GRADED,
    create_chat_message,
    get_chat_messages,
    get_current_chat_for_prompt,
    get_prompt_question,
    init_admin_supabase,
    init_authenticated_supabase,
    update_chat_grade,
)
from streamlit_helpers import nav_query_params_with_sid, render_logout_sidebar, require_student_or_authorized
from tools import get_gemini_response, grade_chat_with_gemini

PROMPT_ID = "21b23642-6bf2-4777-bef0-394c2aafb071"
DEFAULT_GRADING_PROMPT = (
    "Score this submission from 0 to 10. Reward scientifically grounded reasoning, "
    "good use of the case facts, clear experimental design, and actionable next "
    "steps. Penalize vague claims, unsupported conclusions, or missing justification."
)

require_student_or_authorized(allow_instructor=True)
render_logout_sidebar()

session = st.session_state.supabase_session
access_token = getattr(session, "access_token", None)
user_id = st.session_state.user.get("id") if st.session_state.user else None

if not access_token or not user_id:
    st.error("A valid Supabase session is required to load and save chats. Please log in with email.")
    st.page_link("pages/login.py", label="Go to Login", query_params=nav_query_params_with_sid())
    st.stop()

db = init_authenticated_supabase(access_token)
admin_db = init_admin_supabase()

try:
    prompt_question = get_prompt_question(db, PROMPT_ID)
    current_chat = get_current_chat_for_prompt(db, user_id, PROMPT_ID)
    chat_messages = get_chat_messages(db, current_chat["chat_id"])
except Exception as e:
    st.error(f"Error loading exam data: {e}")
    st.stop()

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

st.divider()
st.page_link("pages/home.py", label="Home", query_params=nav_query_params_with_sid())
