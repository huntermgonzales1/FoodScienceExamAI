from google import genai


client = genai.Client()
MODEL_ID = "gemini-3-flash-preview"

SYSTEM_PROMPT = """
    Act as a Senior Food Science Exam Proctor. The student is solving a case study about a strawberry protein bar
    turning brown (Maillard reaction).
    Follow these rules:
    1. Do NOT give away the answer.
    2. Use the 'Analytical Approach': First, they must hypothesize reactions.
    Then, they must design an experiment with an independent and dependent variable.
    3. If they propose a valid experiment, simulate the result (e.g., 'Lowering the pH slowed the browning').
    4. Grade them based on terms like 'Maillard reaction', 'reducing sugars', and 'water activity'.
    """


def get_gemini_response(prompt: str) -> str:
    chat = client.chats.create(
        model=MODEL_ID,
        config={"system_instruction": SYSTEM_PROMPT},
    )
    response = chat.send_message(prompt)
    return response.text
