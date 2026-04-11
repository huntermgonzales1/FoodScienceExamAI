import streamlit as st

from database import CHAT_STATUS_GRADED


def render_readonly_chat_transcript(
    prompt_question: dict,
    messages: list[dict],
    chat_row: dict | None = None,
    *,
    show_instructor_readonly_caption: bool = False,
) -> None:
    """Render scenario, info text, message thread, and graded summary (if applicable)."""
    if show_instructor_readonly_caption:
        st.caption("Instructor view (read-only).")

    st.subheader("Scenario")
    st.info(prompt_question["scenario_text"])
    st.write(prompt_question["info_text"])

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if chat_row and chat_row.get("status") == CHAT_STATUS_GRADED:
        st.success(f"Final grade: {chat_row['final_grade']}/10")
        st.write(chat_row["grade_justification"])
