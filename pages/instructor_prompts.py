import uuid
from datetime import date

import streamlit as st

from database import init_authenticated_supabase, list_prompt_questions, save_prompt_question
from streamlit_helpers import (
    nav_query_params,
    render_backend_error,
    render_logout_sidebar,
    require_instructor,
)


def _preview(text: str, max_len: int = 80) -> str:
    stripped = (text or "").strip()
    if len(stripped) <= max_len:
        return stripped
    return f"{stripped[:max_len]}..."


def _iso_to_date(value: str | None, default: date | None = None) -> date:
    if value:
        return date.fromisoformat(value)
    return default or date.today()


require_instructor()
render_logout_sidebar()

st.page_link(
    "pages/instructor.py",
    label="Back to Instructor Dashboard",
    query_params=nav_query_params(),
)
st.title("Edit Chat Prompts")

session = st.session_state.supabase_session
access_token = getattr(session, "access_token", None)
if not access_token:
    st.error("A valid Supabase session is required. Please log in again.")
    st.page_link("pages/login.py", label="Go to Login", query_params=nav_query_params())
    st.stop()

db = init_authenticated_supabase(access_token)

try:
    rows = list_prompt_questions(db)
except Exception as e:
    render_backend_error("load prompts", e, key_prefix="instructor_prompts_load")
    st.stop()

rows_by_id = {row.get("prompt_id", ""): row for row in rows if row.get("prompt_id")}
selected_key = "instructor_prompts_selected_id"

if selected_key not in st.session_state:
    st.session_state[selected_key] = None


def load_prompt_into_form(row: dict):
    expire_value = row.get("expire_date")
    order_value = row.get("order_index")

    st.session_state["instructor_prompts_form_prompt_id"] = row.get("prompt_id", "")
    st.session_state["instructor_prompts_form_scenario_text"] = row.get("scenario_text", "")
    st.session_state["instructor_prompts_form_info_text"] = row.get("info_text", "")
    st.session_state["instructor_prompts_form_system_instruction"] = row.get(
        "system_instruction", ""
    )
    st.session_state["instructor_prompts_form_available_date"] = _iso_to_date(
        row.get("available_date")
    )
    st.session_state["instructor_prompts_form_never_expires"] = expire_value is None
    st.session_state["instructor_prompts_form_expire_date"] = _iso_to_date(expire_value)
    st.session_state["instructor_prompts_form_has_order_index"] = order_value is not None
    st.session_state["instructor_prompts_form_order_index"] = int(order_value or 0)
    st.session_state["instructor_prompts_form_is_practice"] = bool(
        row.get("is_practice", False)
    )

display_rows = [
    {
        "prompt_id": row.get("prompt_id", ""),
        "available_date": row.get("available_date"),
        "expire_date": row.get("expire_date") or "Never",
        "order_index": row.get("order_index"),
        "is_practice": bool(row.get("is_practice", False)),
        "scenario_preview": _preview(row.get("scenario_text", "")),
    }
    for row in rows
]

st.subheader("Current Prompts")
selected_prompt_id = st.session_state[selected_key]
selected_row = rows_by_id.get(selected_prompt_id) if selected_prompt_id else None

if selected_row:
    st.info(f"Showing details for prompt: {selected_prompt_id}")
    st.dataframe([selected_row], width="stretch", hide_index=True)
    if st.button("Back to full table"):
        st.session_state[selected_key] = None
        st.rerun()
elif display_rows:
    st.dataframe(display_rows, width="stretch", hide_index=True)
    prompt_options = [""] + list(rows_by_id.keys())
    selected_option = st.selectbox(
        "Select an existing prompt to view/edit",
        options=prompt_options,
        format_func=lambda x: (
            "Choose a prompt..."
            if x == ""
            else f"{x} | {_preview(rows_by_id[x].get('scenario_text', ''), 50)}"
        ),
    )
    if st.button("Open Selected Prompt"):
        if not selected_option:
            st.warning("Choose a prompt first.")
            st.stop()
        st.session_state[selected_key] = selected_option
        load_prompt_into_form(rows_by_id[selected_option])
        st.rerun()
else:
    st.info("No prompts found.")

st.subheader("Add or Update Prompt")
st.session_state.setdefault("instructor_prompts_form_prompt_id", "")
st.session_state.setdefault("instructor_prompts_form_scenario_text", "")
st.session_state.setdefault("instructor_prompts_form_info_text", "")
st.session_state.setdefault("instructor_prompts_form_system_instruction", "")
st.session_state.setdefault("instructor_prompts_form_available_date", date.today())
st.session_state.setdefault("instructor_prompts_form_never_expires", True)
st.session_state.setdefault("instructor_prompts_form_expire_date", date.today())
st.session_state.setdefault("instructor_prompts_form_has_order_index", False)
st.session_state.setdefault("instructor_prompts_form_order_index", 0)
st.session_state.setdefault("instructor_prompts_form_is_practice", False)

prompt_id = st.text_input(
    "Prompt ID (optional, for updating an existing prompt)",
    key="instructor_prompts_form_prompt_id",
)
scenario_text = st.text_area(
    "Scenario text", height=120, key="instructor_prompts_form_scenario_text"
)
info_text = st.text_area("Info text", height=120, key="instructor_prompts_form_info_text")
system_instruction = st.text_area(
    "System instruction", height=180, key="instructor_prompts_form_system_instruction"
)
available_date = st.date_input(
    "Available date", key="instructor_prompts_form_available_date"
)
never_expires = st.checkbox(
    "Never expires", key="instructor_prompts_form_never_expires"
)
expire_date = st.date_input(
    "Expire date",
    key="instructor_prompts_form_expire_date",
    disabled=never_expires,
)
has_order_index = st.checkbox(
    "Set order index", key="instructor_prompts_form_has_order_index"
)
order_index = st.number_input(
    "Order index",
    step=1,
    key="instructor_prompts_form_order_index",
    disabled=not has_order_index,
)
is_practice = st.checkbox("Practice prompt", key="instructor_prompts_form_is_practice")
submitted = st.button("Save Prompt")

if submitted:
    clean_prompt_id = prompt_id.strip()
    clean_scenario = scenario_text.strip()
    clean_info = info_text.strip()
    clean_system = system_instruction.strip()

    if clean_prompt_id:
        try:
            str(uuid.UUID(clean_prompt_id))
        except ValueError:
            st.warning("Prompt ID must be a valid UUID when provided.")
            st.stop()

    if not clean_scenario or not clean_info or not clean_system:
        st.warning("Scenario text, info text, and system instruction are required.")
        st.stop()

    expire_value = None if never_expires else expire_date.isoformat()
    order_value = int(order_index) if has_order_index else None

    try:
        save_prompt_question(
            db,
            scenario_text=clean_scenario,
            info_text=clean_info,
            system_instruction=clean_system,
            available_date=available_date.isoformat(),
            expire_date=expire_value,
            order_index=order_value,
            is_practice=is_practice,
            prompt_id=clean_prompt_id or None,
        )
        st.success("Prompt saved.")
        st.rerun()
    except Exception as e:
        render_backend_error("save prompt", e, key_prefix="instructor_prompts_save")
