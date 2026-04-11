import ast

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
    if "is_instructor" not in st.session_state:
        st.session_state.is_instructor = False


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
        "is_instructor": bool(saved.get("is_instructor", False)),
    }
    st.session_state.email = saved["email"]
    st.session_state.supabase_session = session
    st.session_state.is_instructor = bool(saved.get("is_instructor", False))


def get_current_sid() -> str | None:
    sid = get_query_params().get("sid")
    return sid or None


def nav_query_params_with_sid(extra: dict | None = None) -> dict | None:
    params = {}
    sid = get_current_sid()
    if sid:
        params["sid"] = sid
    if extra:
        params.update(extra)
    return params or None


def ensure_session_restored():
    init_auth_state()
    if st.session_state.user is None:
        restore_session_from_sid()


def switch_page_with_sid(page: str):
    st.switch_page(page, query_params=nav_query_params_with_sid())


def require_logged_in():
    ensure_session_restored()
    if st.session_state.user is None:
        switch_page_with_sid("pages/login.py")
        st.stop()


def require_instructor():
    require_logged_in()
    is_instructor = bool(st.session_state.user.get("is_instructor", False))
    if not is_instructor:
        switch_page_with_sid("pages/unauthorized.py")
        st.stop()


def require_student_or_authorized(allow_instructor: bool = True):
    require_logged_in()
    is_instructor = bool(st.session_state.user.get("is_instructor", False))
    if is_instructor and not allow_instructor:
        switch_page_with_sid("pages/unauthorized.py")
        st.stop()


def logout_and_redirect_to_login():
    sid = get_current_sid()
    if sid and sid in auth_store():
        del auth_store()[sid]

    st.session_state.user = None
    st.session_state.email = ""
    st.session_state.code_sent = False
    st.session_state.supabase_session = None
    st.session_state.is_instructor = False
    if "chat_id" in st.session_state:
        del st.session_state["chat_id"]
    if "messages" in st.session_state:
        del st.session_state["messages"]

    clear_query_params()
    st.switch_page("pages/login.py")
    st.stop()


def render_logout_sidebar():
    ensure_session_restored()
    with st.sidebar:
        if st.session_state.user is not None and st.button("Logout"):
            logout_and_redirect_to_login()


def _parse_error_payload(error: Exception) -> dict:
    payload = {}
    raw_text = str(error)

    # Supabase errors sometimes expose a dict-like string:
    # {'message': 'JWT expired', 'code': 'PGRST303', ...}
    if raw_text.startswith("{") and raw_text.endswith("}"):
        try:
            possible_payload = ast.literal_eval(raw_text)
            if isinstance(possible_payload, dict):
                payload = possible_payload
        except (ValueError, SyntaxError):
            pass

    if not payload:
        for key in ("message", "code", "hint", "details"):
            value = getattr(error, key, None)
            if value:
                payload[key] = value

    if not payload:
        payload["message"] = raw_text

    return payload


def is_jwt_expired_error(error: Exception) -> bool:
    payload = _parse_error_payload(error)
    code = str(payload.get("code", "")).strip().upper()
    message = str(payload.get("message", "")).strip().lower()
    raw_text = str(error).strip().lower()

    if code == "PGRST303":
        return True
    return "jwt expired" in message or "jwt expired" in raw_text


def render_backend_error(action: str, error: Exception, key_prefix: str = "backend_error"):
    payload = _parse_error_payload(error)

    if is_jwt_expired_error(error):
        st.error("Your login session expired while this page was open.")
        st.info("To continue: 1) click logout, 2) sign in again, 3) reopen this page.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Logout and go to Login", key=f"{key_prefix}_logout"):
                logout_and_redirect_to_login()
        with col2:
            st.page_link(
                "pages/login.py",
                label="Go to Login",
                query_params=nav_query_params_with_sid(),
            )
    else:
        st.error(f"Error trying to {action}.")

    with st.expander("Technical Details"):
        st.code(
            (
                f"Action: {action}\n"
                f"Message: {payload.get('message', 'Unknown error')}\n"
                f"Code: {payload.get('code', 'N/A')}\n"
                f"Hint: {payload.get('hint', 'N/A')}\n"
                f"Details: {payload.get('details', 'N/A')}"
            )
        )
