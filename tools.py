from google import genai


client = genai.Client()
MODEL_ID = "gemini-3-flash-preview"

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
