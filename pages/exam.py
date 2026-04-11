import math
from datetime import date

import streamlit as st

from database import (
    CHAT_STATUS_ACTIVE,
    CHAT_STATUS_GRADED,
    create_chat,
    create_chat_message,
    get_chat_messages,
    get_user_chat_by_id,
    init_admin_supabase,
    init_authenticated_supabase,
    list_prompt_questions,
    list_user_chats,
    update_chat_grade,
)
from streamlit_helpers import (
    get_query_params,
    nav_query_params_with_sid,
    render_backend_error,
    render_logout_sidebar,
    require_student_or_authorized,
)
from chat_display import render_readonly_chat_transcript
from tools import get_gemini_response, grade_chat_with_gemini

DEFAULT_GRADING_PROMPT = (
    "Score this submission from 0 to 10. Reward scientifically grounded reasoning, "
    "good use of the case facts, clear experimental design, and actionable next "
    "steps. Penalize vague claims, unsupported conclusions, or missing justification."
)


def _preview(text: str, max_len: int = 90) -> str:
    stripped = (text or "").strip()
    if len(stripped) <= max_len:
        return stripped
    return f"{stripped[:max_len]}..."


def _iso_to_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _is_prompt_currently_available(prompt: dict, today: date) -> bool:
    available_date = _iso_to_date(prompt.get("available_date"))
    expire_date = _iso_to_date(prompt.get("expire_date"))
    if available_date is None:
        return False
    if today < available_date:
        return False
    return expire_date is None or today <= expire_date


def _prompt_sort_key(prompt: dict) -> tuple:
    order_index = prompt.get("order_index")
    available_date = _iso_to_date(prompt.get("available_date"))
    available_ordinal = available_date.toordinal() if available_date else 0
    return (
        order_index is None,
        order_index if order_index is not None else math.inf,
        -available_ordinal,
    )


def _set_chat_query_param(chat_id: str | None):
    extra = {"chat_id": chat_id} if chat_id else None
    params = nav_query_params_with_sid(extra=extra) or {}

    try:
        st.query_params.clear()
        for key, value in params.items():
            st.query_params[key] = value
    except Exception:
        st.experimental_set_query_params(**params)


def _prompt_status_label(prompt: dict, latest_chat: dict | None, today: date) -> str:
    if latest_chat and latest_chat.get("status") == CHAT_STATUS_GRADED:
        return "Graded"

    is_available = _is_prompt_currently_available(prompt, today)
    if latest_chat and not is_available:
        return "Expired (read-only)"
    if is_available:
        return "Available"
    return "Unavailable"


def _pick_default_prompt_id(
    prompts: list[dict],
    latest_chat_by_prompt_id: dict[str, dict],
    today: date,
) -> str | None:
    for prompt in prompts:
        prompt_id = prompt.get("prompt_id")
        if not prompt_id:
            continue
        has_started = prompt_id in latest_chat_by_prompt_id
        is_active = _is_prompt_currently_available(prompt, today)
        if has_started and is_active:
            return prompt_id

    for prompt in prompts:
        prompt_id = prompt.get("prompt_id")
        if prompt_id and _is_prompt_currently_available(prompt, today):
            return prompt_id

    for prompt in prompts:
        prompt_id = prompt.get("prompt_id")
        if prompt_id and prompt_id in latest_chat_by_prompt_id:
            return prompt_id

    return None


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

st.page_link("pages/home.py", label="Home", query_params=nav_query_params_with_sid())
st.title("Food Science Lab: Case Study Exam")

pending_warning = st.session_state.pop("exam_warning", None)
if pending_warning:
    st.warning(pending_warning)

try:
    prompt_rows = list_prompt_questions(db)
    user_chats = list_user_chats(db, user_id)
except Exception as e:
    render_backend_error("load exam data", e, key_prefix="exam_load")
    st.stop()

prompt_by_id = {row.get("prompt_id"): row for row in prompt_rows if row.get("prompt_id")}
latest_chat_by_prompt_id: dict[str, dict] = {}
for chat in user_chats:
    prompt_id = chat.get("initial_prompt_id")
    if prompt_id and prompt_id not in latest_chat_by_prompt_id:
        latest_chat_by_prompt_id[prompt_id] = chat

today = date.today()
visible_prompts = [
    prompt
    for prompt in prompt_rows
    if _is_prompt_currently_available(prompt, today)
    or prompt.get("prompt_id") in latest_chat_by_prompt_id
]
visible_prompts.sort(key=_prompt_sort_key)

query_chat_id = get_query_params().get("chat_id")

current_chat = None
prompt_question = None
chat_messages = []

if query_chat_id:
    try:
        current_chat = get_user_chat_by_id(db, user_id, query_chat_id)
    except Exception as e:
        render_backend_error("load selected chat", e, key_prefix="exam_selected_chat")
        st.stop()

    if current_chat is None:
        st.session_state["exam_warning"] = (
            "The requested chat was not found or you do not have access to it. "
            "We selected a default case study for you."
        )
        _set_chat_query_param(None)
        st.rerun()

    prompt_question = prompt_by_id.get(current_chat.get("initial_prompt_id"))
    if prompt_question is None:
        st.session_state["exam_warning"] = (
            "The requested chat references a prompt that is no longer visible. "
            "We selected a default case study for you."
        )
        _set_chat_query_param(None)
        st.rerun()

    try:
        chat_messages = get_chat_messages(db, current_chat["chat_id"])
    except Exception as e:
        render_backend_error("load selected chat messages", e, key_prefix="exam_selected_messages")
        st.stop()

if current_chat is None:
    default_prompt_id = _pick_default_prompt_id(
        visible_prompts,
        latest_chat_by_prompt_id,
        today,
    )
    if not default_prompt_id:
        st.info("No case studies are currently available.")
        st.stop()

    default_existing_chat = latest_chat_by_prompt_id.get(default_prompt_id)
    if default_existing_chat:
        _set_chat_query_param(default_existing_chat["chat_id"])
        st.rerun()

    default_prompt = prompt_by_id.get(default_prompt_id)
    if default_prompt is None or not _is_prompt_currently_available(default_prompt, today):
        st.info("No case studies are currently available.")
        st.stop()

    try:
        created_chat = create_chat(db, user_id, default_prompt_id)
    except Exception as e:
        render_backend_error("create default exam chat", e, key_prefix="exam_create_default_chat")
        st.stop()

    _set_chat_query_param(created_chat["chat_id"])
    st.rerun()

if current_chat is None or prompt_question is None:
    st.info("Unable to load a chat right now.")
    st.stop()

st.session_state.chat_id = current_chat["chat_id"]
st.session_state.messages = [
    {"role": message["role"], "content": message["content"]}
    for message in chat_messages
]

prompt_is_available = _is_prompt_currently_available(prompt_question, today)
chat_is_active = current_chat.get("status") == CHAT_STATUS_ACTIVE
can_continue = prompt_is_available and chat_is_active

render_readonly_chat_transcript(
    prompt_question,
    st.session_state.messages,
    current_chat,
)

if current_chat["status"] == CHAT_STATUS_GRADED:
    st.info(
        "This exam attempt has been finalized and can no longer receive new "
        "messages."
    )
elif not prompt_is_available:
    st.info(
        "This prompt is outside its availability window. You can review this chat, "
        "but you cannot add messages or finalize it."
    )
elif not chat_is_active:
    st.info("This chat is no longer active and is read-only.")

if prompt := st.chat_input(
    "What is your hypothesis or proposed experiment?",
    disabled=not can_continue,
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
        render_backend_error("send or save chat messages", e, key_prefix="exam_chat")

with st.sidebar:
    st.header("Case Study")
    prompt_options = [row["prompt_id"] for row in visible_prompts]
    current_prompt_id = current_chat.get("initial_prompt_id")
    selected_prompt_id = st.selectbox(
        "Switch case study",
        options=prompt_options,
        index=prompt_options.index(current_prompt_id),
        format_func=lambda prompt_id: (
            f"[{_prompt_status_label(prompt_by_id[prompt_id], latest_chat_by_prompt_id.get(prompt_id), today)}] "
            f"{_preview(prompt_by_id[prompt_id].get('scenario_text', 'Untitled case study'))}"
        ),
    )

    if selected_prompt_id != current_prompt_id:
        selected_existing_chat = latest_chat_by_prompt_id.get(selected_prompt_id)
        if selected_existing_chat:
            _set_chat_query_param(selected_existing_chat["chat_id"])
            st.rerun()

        try:
            created_chat = create_chat(db, user_id, selected_prompt_id)
        except Exception as e:
            render_backend_error("create exam chat", e, key_prefix="exam_create_chat")
            st.stop()

        _set_chat_query_param(created_chat["chat_id"])
        st.rerun()

    st.header("Exam Controls")
    if current_chat["status"] == CHAT_STATUS_GRADED:
        st.caption("This attempt has already been finalized and graded.")
    elif not prompt_is_available:
        st.caption("This prompt has expired for submission and is read-only.")
    elif not chat_is_active:
        st.caption("This chat is no longer active.")

    finalize_disabled = (not can_continue) or (len(st.session_state.messages) == 0)
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
                render_backend_error("finalize and grade chat", e, key_prefix="exam_grade")
