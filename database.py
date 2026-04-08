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


def get_prompt_question(supabase, prompt_id: str) -> dict:
    response = (
        supabase.table("prompt_question")
        .select("*")
        .eq("prompt_id", prompt_id)
        .single()
        .execute()
    )
    return response.data


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


def get_chat(supabase, chat_id: str) -> dict:
    response = (
        supabase.table("chat")
        .select("*")
        .eq("chat_id", chat_id)
        .single()
        .execute()
    )
    return response.data


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
