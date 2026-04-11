import streamlit as st
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions


CHAT_STATUS_ACTIVE = "active"
CHAT_STATUS_COMPLETED = "completed"
CHAT_STATUS_GRADED = "graded"


@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_PUBLISHABLE_KEY"],
    )


@st.cache_resource
def auth_store():
    # Server-side session store for this Streamlit process.
    # Key: session_id, Value: dict with user/session info.
    return {}


def init_authenticated_supabase(access_token: str):
    options = SyncClientOptions(
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_PUBLISHABLE_KEY"],
        options=options,
    )


@st.cache_resource
def init_admin_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SECRET_KEY"],
    )


def send_login_code(supabase, email: str):
    return supabase.auth.sign_in_with_otp({"email": email})


def verify_login_code(supabase, email: str, code: str):
    return supabase.auth.verify_otp(
        {
            "email": email,
            "token": code,
            "type": "email",
        }
    )


def get_user_is_instructor(supabase, user_id: str) -> bool:
    response = (
        supabase.table("user_profile")
        .select("is_instructor")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return False
    return bool(rows[0].get("is_instructor", False))


def list_allowed_emails(supabase) -> list[dict]:
    response = (
        supabase.table("allowed_emails")
        .select("email, expiration_date, is_instructor")
        .order("email")
        .execute()
    )
    return response.data or []


def upsert_allowed_email(
    supabase,
    email: str,
    expiration_date: str | None,
    is_instructor: bool = False,
) -> dict:
    response = (
        supabase.table("allowed_emails")
        .upsert(
            {
                "email": email,
                "expiration_date": expiration_date,
                "is_instructor": is_instructor,
            },
            on_conflict="email",
        )
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else {}


def get_prompt_question(supabase, prompt_id: str) -> dict:
    response = (
        supabase.table("prompt_question")
        .select("*")
        .eq("prompt_id", prompt_id)
        .single()
        .execute()
    )
    return response.data


def list_prompt_questions(supabase) -> list[dict]:
    response = (
        supabase.table("prompt_question")
        .select(
            "prompt_id, scenario_text, info_text, system_instruction, available_date, "
            "expire_date, order_index, is_practice"
        )
        .order("available_date", desc=True)
        .execute()
    )
    return response.data or []


def save_prompt_question(
    supabase,
    scenario_text: str,
    info_text: str,
    system_instruction: str,
    available_date: str,
    expire_date: str | None,
    order_index: int | None,
    is_practice: bool,
    prompt_id: str | None = None,
) -> dict:
    payload = {
        "scenario_text": scenario_text,
        "info_text": info_text,
        "system_instruction": system_instruction,
        "available_date": available_date,
        "expire_date": expire_date,
        "order_index": order_index,
        "is_practice": is_practice,
    }

    if prompt_id:
        payload["prompt_id"] = prompt_id
        response = (
            supabase.table("prompt_question")
            .upsert(payload, on_conflict="prompt_id")
            .execute()
        )
    else:
        response = supabase.table("prompt_question").insert(payload).execute()

    rows = response.data or []
    return rows[0] if rows else {}


def get_active_chat_for_prompt(supabase, user_id: str, prompt_id: str) -> dict | None:
    response = (
        supabase.table("chat")
        .select("*")
        .eq("user_id", user_id)
        .eq("initial_prompt_id", prompt_id)
        .eq("status", CHAT_STATUS_ACTIVE)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def get_latest_chat_for_prompt(supabase, user_id: str, prompt_id: str) -> dict | None:
    response = (
        supabase.table("chat")
        .select("*")
        .eq("user_id", user_id)
        .eq("initial_prompt_id", prompt_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def create_chat(supabase, user_id: str, prompt_id: str) -> dict:
    response = (
        supabase.table("chat")
        .insert(
            {
                "user_id": user_id,
                "initial_prompt_id": prompt_id,
                "status": CHAT_STATUS_ACTIVE,
            }
        )
        .execute()
    )
    return response.data[0]


def get_or_create_active_chat(supabase, user_id: str, prompt_id: str) -> dict:
    chat = get_active_chat_for_prompt(supabase, user_id, prompt_id)
    if chat is not None:
        return chat
    return create_chat(supabase, user_id, prompt_id)


def get_current_chat_for_prompt(supabase, user_id: str, prompt_id: str) -> dict:
    active_chat = get_active_chat_for_prompt(supabase, user_id, prompt_id)
    if active_chat is not None:
        return active_chat

    latest_chat = get_latest_chat_for_prompt(supabase, user_id, prompt_id)
    if latest_chat is not None:
        return latest_chat

    return create_chat(supabase, user_id, prompt_id)


def get_chat_messages(supabase, chat_id: str) -> list[dict]:
    response = (
        supabase.table("chat_message")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at")
        .order("message_id")
        .execute()
    )
    return response.data or []


def list_chats(supabase) -> list[dict]:
    response = (
        supabase.table("chat")
        .select(
            "chat_id, user_id, initial_prompt_id, created_at, final_grade, "
            "grade_justification, status"
        )
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def list_user_chats(supabase, user_id: str) -> list[dict]:
    response = (
        supabase.table("chat")
        .select(
            "chat_id, user_id, initial_prompt_id, created_at, final_grade, "
            "grade_justification, status"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def list_user_profiles(supabase) -> list[dict]:
    response = (
        supabase.table("user_profile")
        .select("user_id, email")
        .order("email")
        .execute()
    )
    return response.data or []


def get_user_chat_by_id(supabase, user_id: str, chat_id: str) -> dict | None:
    response = (
        supabase.table("chat")
        .select("*")
        .eq("chat_id", chat_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def get_chat(supabase, chat_id: str) -> dict:
    response = (
        supabase.table("chat")
        .select("*")
        .eq("chat_id", chat_id)
        .single()
        .execute()
    )
    return response.data


def get_chat_optional(supabase, chat_id: str) -> dict | None:
    response = (
        supabase.table("chat")
        .select("*")
        .eq("chat_id", chat_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def create_chat_message(supabase, chat_id: str, role: str, content: str) -> dict:
    response = (
        supabase.table("chat_message")
        .insert(
            {
                "chat_id": chat_id,
                "role": role,
                "content": content,
            }
        )
        .execute()
    )
    return response.data[0]


def update_chat_grade(
    supabase,
    chat_id: str,
    final_grade: float,
    grade_justification: str,
    status: str = CHAT_STATUS_GRADED,
) -> dict:
    response = (
        supabase.table("chat")
        .update(
            {
                "status": status,
                "final_grade": final_grade,
                "grade_justification": grade_justification,
            }
        )
        .eq("chat_id", chat_id)
        .execute()
    )
    return get_chat(supabase, chat_id)
