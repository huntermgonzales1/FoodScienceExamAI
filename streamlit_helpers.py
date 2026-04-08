import streamlit as st

from database import auth_store


def init_auth_state():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "email" not in st.session_state:
        st.session_state.email = ""
    if "code_sent" not in st.session_state:
        st.session_state.code_sent = False
    if "supabase_session" not in st.session_state:
        st.session_state.supabase_session = None


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

    user = saved.get("user")
    session = saved.get("session")
    st.session_state.user = {
        "email": saved["email"],
        "id": getattr(user, "id", None),
    }
    st.session_state.email = saved["email"]
    st.session_state.supabase_session = session
