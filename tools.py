import json

import streamlit as st
from google import genai


client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL_ID = "gemini-2.5-flash"
GRADE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "grade": {
            "type": "number",
            "description": "A numeric grade from 0 to 10.",
        },
        "justification": {
            "type": "string",
            "description": "A brief explanation of the score.",
        },
    },
    "required": ["grade", "justification"],
}

def _build_chat_history(messages: list[dict]) -> list[dict]:
    history = []
    for message in messages:
        if message["role"] == "user":
            history.append({"role": "user", "parts": [{"text": message["content"]}]})
        elif message["role"] == "assistant":
            history.append({"role": "model", "parts": [{"text": message["content"]}]})
    return history


def get_gemini_response(
    prompt: str,
    system_instruction: str,
    messages: list[dict] | None = None,
) -> str:
    chat = client.chats.create(
        model=MODEL_ID,
        config={"system_instruction": system_instruction},
        history=_build_chat_history(messages or []),
    )
    response = chat.send_message(prompt)
    return response.text


def _format_chat_transcript(messages: list[dict]) -> str:
    transcript_lines = []
    for index, message in enumerate(messages, start=1):
        transcript_lines.append(
            f"{index}. {message['role'].upper()}: {message['content']}"
        )
    return "\n".join(transcript_lines)


def grade_chat_with_gemini(
    prompt_question: dict,
    messages: list[dict],
    grading_prompt: str | None = None,
) -> dict:
    grading_instruction = grading_prompt or (
        "You are grading a food science exam conversation. Evaluate the student's "
        "scientific reasoning, use of the scenario details, clarity, and whether the "
        "proposal is practical and responsive to the case. Return only valid JSON."
    )

    transcript = _format_chat_transcript(messages)
    contents = f"""
Grade the following exam attempt.

Scenario text:
{prompt_question["scenario_text"]}

Additional info:
{prompt_question["info_text"]}

Original chat system instruction:
{prompt_question["system_instruction"]}

Grading guidance:
{grading_instruction}

Transcript:
{transcript}

Return JSON with exactly these fields:
- "grade": number from 0 to 10
- "justification": short explanation for the score
""".strip()

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": GRADE_RESPONSE_SCHEMA,
            "temperature": 0.2,
        },
    )

    result = json.loads(response.text)
    result["grade"] = max(0.0, min(10.0, float(result["grade"])))
    result["justification"] = str(result["justification"]).strip()
    return result
