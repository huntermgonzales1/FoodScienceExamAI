import streamlit as st
from supabase import create_client


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
