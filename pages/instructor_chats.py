import streamlit as st

from chat_display import render_readonly_chat_transcript
from database import (
    get_chat_messages,
    get_chat_optional,
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

st.subheader("View conversation")
rows_for_transcript_picker = full_rows
if selected_scenario:
    rows_for_transcript_picker = [
        row for row in rows_for_transcript_picker if row.get("prompt_id") == selected_scenario
    ]
if selected_student:
    rows_for_transcript_picker = [
        row for row in rows_for_transcript_picker if row.get("student_email") == selected_student
    ]

filter_parts = []
if selected_scenario:
    filter_parts.append(
        "scenario: "
        + _preview(
            prompt_by_id.get(selected_scenario, {}).get("scenario_text", "Unknown scenario")
        )
    )
if selected_student:
    filter_parts.append(f"student: {selected_student}")
if filter_parts:
    st.caption("Chat list matches your filters above (" + " · ".join(filter_parts) + ").")
else:
    st.caption(
        "Chat list includes every chat. Use the scenario and/or student filters above to narrow this list."
    )

row_by_chat_id = {
    row.get("chat_id"): row for row in rows_for_transcript_picker if row.get("chat_id")
}
view_chat_options = [""] + [
    row["chat_id"] for row in rows_for_transcript_picker if row.get("chat_id")
]


def _format_view_chat_option(chat_id: str) -> str:
    if not chat_id:
        return "Choose a chat to view the full transcript..."
    row = row_by_chat_id.get(chat_id, {})
    email = row.get("student_email", "Unknown")
    preview = row.get("scenario_preview", "")
    created = row.get("created_date", "")
    return f"{email} · {preview} · {created}"


_picker_key = (
    f"instructor_view_chat_{selected_scenario or 'all'}_{selected_student or 'all'}"
)
selected_view_chat_id = st.selectbox(
    "Select a student's chat",
    options=view_chat_options,
    format_func=_format_view_chat_option,
    key=_picker_key,
)

if selected_view_chat_id:
    chat_row = get_chat_optional(db, selected_view_chat_id)
    if not chat_row:
        st.warning("That chat was not found.")
    else:
        prompt_question = prompt_by_id.get(chat_row.get("initial_prompt_id"))
        if not prompt_question:
            st.warning("The scenario for this chat is missing or no longer available.")
        else:
            try:
                raw_messages = get_chat_messages(db, selected_view_chat_id)
            except Exception as e:
                render_backend_error(
                    "load chat messages",
                    e,
                    key_prefix="instructor_chats_messages",
                )
                st.stop()
            messages = [
                {"role": m["role"], "content": m["content"]}
                for m in raw_messages
            ]
            render_readonly_chat_transcript(
                prompt_question,
                messages,
                chat_row,
                show_instructor_readonly_caption=True,
            )
