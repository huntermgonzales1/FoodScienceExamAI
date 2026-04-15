import streamlit as st

from cookie_auth import render_cookie_controller_ui, reset_run_cookie_controller


def main():
    reset_run_cookie_controller()
    st.set_page_config(page_title="Food Science Exam", layout="centered")
    render_cookie_controller_ui()
    pages = [
        st.Page("pages/home.py", title="Home", url_path="", default=True, visibility="hidden"),
        st.Page("pages/login.py", title="Login", url_path="login", visibility="hidden"),
        st.Page("pages/exam.py", title="Exam", url_path="exam", visibility="hidden"),
        st.Page(
            "pages/instructor.py",
            title="Instructor",
            url_path="instructor",
            visibility="hidden",
        ),
        st.Page(
            "pages/instructor_users.py",
            title="Instructor Users",
            url_path="instructor-users",
            visibility="hidden",
        ),
        st.Page(
            "pages/instructor_prompts.py",
            title="Instructor Prompts",
            url_path="instructor-prompts",
            visibility="hidden",
        ),
        st.Page(
            "pages/instructor_chats.py",
            title="Instructor Chats",
            url_path="instructor-chats",
            visibility="hidden",
        ),
        st.Page(
            "pages/unauthorized.py",
            title="Unauthorized",
            url_path="unauthorized",
            visibility="hidden",
        ),
    ]
    selected_page = st.navigation(pages, position="hidden")
    selected_page.run()


if __name__ == "__main__":
    main()
