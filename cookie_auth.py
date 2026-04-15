"""
Persist Supabase session tokens in browser cookies so auth survives a full page refresh.

Uses streamlit-cookies-controller (client-side cookies; not HttpOnly).
See https://discuss.streamlit.io/t/new-component-streamlit-cookies-controller/64251
"""

from __future__ import annotations

import traceback

import streamlit as st
from streamlit_cookies_controller import CookieController, RemoveEmptyElementContainer
from supabase import create_client

from database import get_user_is_instructor, init_authenticated_supabase

CONTROLLER_STATE_KEY = "fsea_auth_cookie_ctl"
AUTH_DEBUG_KEY = "_fsea_auth_debug"
HYDRATE_KEY = "_fsea_cookie_hydrate"

# CookieController must be constructed at most once per script run; a second
# construction sets st.session_state[CONTROLLER_STATE_KEY] and raises on Streamlit 1.56+.
_run_cookie_controller: CookieController | None = None


def reset_run_cookie_controller() -> None:
    """Call once at the start of each Streamlit run (see app.py main())."""
    global _run_cookie_controller
    _run_cookie_controller = None


def get_cookie_controller() -> CookieController:
    global _run_cookie_controller
    if _run_cookie_controller is None:
        RemoveEmptyElementContainer()
        _run_cookie_controller = CookieController(key=CONTROLLER_STATE_KEY)
    return _run_cookie_controller


def _record_auth_restore_error(exc: BaseException | None, note: str = "") -> None:
    parts = []
    if note:
        parts.append(note)
    if exc is not None:
        parts.append(f"{type(exc).__name__}: {exc}")
        parts.append(traceback.format_exc())
    st.session_state[AUTH_DEBUG_KEY] = "\n".join(parts) if parts else (note or "Unknown auth restore error")


def consume_auth_debug_message() -> str | None:
    """Return and clear the last auth-restore diagnostic (for the login page)."""
    return st.session_state.pop(AUTH_DEBUG_KEY, None)


def _cookie_prefix() -> str:
    if "COOKIE_PREFIX" in st.secrets:
        p = str(st.secrets["COOKIE_PREFIX"]).strip()
        if p:
            return p
    return "fsea"


def _cookie_max_age() -> float:
    if "AUTH_COOKIE_MAX_AGE" in st.secrets:
        return float(st.secrets["AUTH_COOKIE_MAX_AGE"])
    return 604800.0


def _access_cookie_name() -> str:
    return f"{_cookie_prefix()}_sb_access"


def _refresh_cookie_name() -> str:
    return f"{_cookie_prefix()}_sb_refresh"


def render_cookie_controller_ui() -> None:
    """Mount the cookie component (hidden) so get/set/remove talk to the browser."""
    get_cookie_controller()


def save_auth_cookies(session) -> None:
    access = getattr(session, "access_token", None)
    refresh = getattr(session, "refresh_token", None)
    if not access or not refresh:
        return
    st.session_state.pop(HYDRATE_KEY, None)
    ctl = get_cookie_controller()
    opts = {"max_age": _cookie_max_age(), "path": "/", "same_site": "lax"}
    ctl.set(_access_cookie_name(), access, **opts)
    ctl.set(_refresh_cookie_name(), refresh, **opts)


def clear_auth_cookies() -> None:
    st.session_state.pop(HYDRATE_KEY, None)
    try:
        ctl = get_cookie_controller()
        ctl.remove(_access_cookie_name())
        ctl.remove(_refresh_cookie_name())
    except Exception:
        pass


def _apply_tokens_to_session(access: str, refresh: str) -> bool:
    st.session_state.pop(HYDRATE_KEY, None)
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_PUBLISHABLE_KEY"],
        )
        auth_res = supabase.auth.set_session(access, refresh)
    except Exception as e:
        _record_auth_restore_error(e, "supabase.auth.set_session failed")
        clear_auth_cookies()
        return False

    session = auth_res.session
    user = auth_res.user
    if not session or not user:
        _record_auth_restore_error(None, "set_session returned no session or user")
        clear_auth_cookies()
        return False

    user_id = getattr(user, "id", None)
    access_token = getattr(session, "access_token", None)
    if not user_id or not access_token:
        _record_auth_restore_error(None, "session missing user_id or access_token")
        clear_auth_cookies()
        return False

    app_metadata = getattr(user, "app_metadata", None) or {}
    if not app_metadata.get("is_authorized", False):
        _record_auth_restore_error(None, "JWT app_metadata.is_authorized is false after restore")
        clear_auth_cookies()
        return False

    is_instructor = bool(app_metadata.get("is_instructor", False))
    try:
        db = init_authenticated_supabase(access_token)
        is_instructor = get_user_is_instructor(db, user_id)
    except Exception:
        pass

    email = (getattr(user, "email", None) or "").strip()
    st.session_state.user = {
        "email": email,
        "id": user_id,
        "is_instructor": is_instructor,
    }
    st.session_state.email = email
    st.session_state.supabase_session = session
    st.session_state.is_instructor = is_instructor
    st.session_state.pop(AUTH_DEBUG_KEY, None)
    return True


def try_restore_session_from_cookies() -> bool:
    if st.session_state.get("user") is not None:
        return True

    try:
        ctl = get_cookie_controller()
        access = ctl.get(_access_cookie_name())
        refresh = ctl.get(_refresh_cookie_name())
        if access and refresh:
            return _apply_tokens_to_session(access, refresh)

        ctl.refresh()
        access = ctl.get(_access_cookie_name())
        refresh = ctl.get(_refresh_cookie_name())
        if access and refresh:
            return _apply_tokens_to_session(access, refresh)

        # First paint after a hard refresh often returns {} until the component syncs once.
        n = st.session_state.get(HYDRATE_KEY, 0)
        if n < 1:
            st.session_state[HYDRATE_KEY] = 1
            st.rerun()
        return False
    except Exception as e:
        _record_auth_restore_error(e, "try_restore_session_from_cookies")
        st.session_state.pop(HYDRATE_KEY, None)
        return False
