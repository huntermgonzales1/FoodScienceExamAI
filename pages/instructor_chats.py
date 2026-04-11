import streamlit as st

from database import (
    init_authenticated_supabase,
    list_chats,
    list_prompt_questions,
    list_user_profiles,
)
from streamlit_helpers import (
    nav_query_params_with_sid,
    render_backend_error,
    render_logout_sidebar,
    require_instructor,
)


def _preview(text: str, max_len: int = 80) -> str:
    stripped = (text or "").strip()
    if len(stripped) <= max_len:
        return stripped
    return f"{stripped[:max_len]}..."


def _to_display_rows(chats: list[dict], user_email_by_id: dict, prompt_by_id: dict) -> list[dict]:
    rows = []
    for chat in chats:
        prompt = prompt_by_id.get(chat.get("initial_prompt_id"), {})
        rows.append(
            {
                "prompt_id": chat.get("initial_prompt_id"),
                "chat_id": chat.get("chat_id"),
                "student_email": user_email_by_id.get(chat.get("user_id"), "Unknown"),
                "scenario_preview": _preview(prompt.get("scenario_text", "Unknown scenario")),
                "created_date": chat.get("created_at"),
                "score": chat.get("final_grade"),
                "score_explanation": chat.get("grade_justification"),
            }
        )
    return rows


require_instructor()
render_logout_sidebar()

st.page_link(
    "pages/instructor.py",
    label="Back to Instructor Dashboard",
    query_params=nav_query_params_with_sid(),
)
st.title("Student Chats and Scores")

session = st.session_state.supabase_session
access_token = getattr(session, "access_token", None)
if not access_token:
    st.error("A valid Supabase session is required. Please log in again.")
    st.page_link("pages/login.py", label="Go to Login", query_params=nav_query_params_with_sid())
    st.stop()

db = init_authenticated_supabase(access_token)

try:
    chats = list_chats(db)
    profiles = list_user_profiles(db)
    prompts = list_prompt_questions(db)
except Exception as e:
    render_backend_error("load chat data", e, key_prefix="instructor_chats_load")
    st.stop()

user_email_by_id = {row.get("user_id"): row.get("email", "") for row in profiles}
prompt_by_id = {row.get("prompt_id"): row for row in prompts}
full_rows = _to_display_rows(chats, user_email_by_id, prompt_by_id)
table_columns = [
    "chat_id",
    "student_email",
    "scenario_preview",
    "created_date",
    "score",
    "score_explanation",
]

st.subheader("All Chats")
if full_rows:
    st.dataframe(
        [{k: row.get(k) for k in table_columns} for row in full_rows],
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No chats found.")

st.subheader("Filter by Scenario")
scenario_ids = sorted(
    {
        row.get("prompt_id")
        for row in full_rows
        if row.get("prompt_id") in prompt_by_id
    }
)
scenario_options = [""] + scenario_ids
selected_scenario = st.selectbox(
    "Select a scenario",
    options=scenario_options,
    format_func=lambda x: (
        "Choose a scenario..."
        if x == ""
        else _preview(prompt_by_id.get(x, {}).get("scenario_text", "Unknown scenario"))
    ),
)

if selected_scenario:
    scenario_rows = [row for row in full_rows if row.get("prompt_id") == selected_scenario]
    if scenario_rows:
        st.dataframe(
            [{k: row.get(k) for k in table_columns} for row in scenario_rows],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No chats found for this scenario.")

st.subheader("Filter by Student")
student_options = [""] + sorted(
    {row.get("student_email", "") for row in full_rows if row.get("student_email")}
)
selected_student = st.selectbox(
    "Select a student email",
    options=student_options,
    format_func=lambda x: "Choose a student..." if x == "" else x,
)

if selected_student:
    student_rows = [row for row in full_rows if row.get("student_email") == selected_student]
    if student_rows:
        st.dataframe(
            [{k: row.get(k) for k in table_columns} for row in student_rows],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No chats found for this student.")
