import streamlit as st
from google import genai
import datetime
import os

# --- CONFIGURATION ---
# Ensure you have 'GOOGLE_API_KEY' set in your environment variables.
# The client will automatically look for this variable.
client = genai.Client() 
MODEL_ID = "gemini-3-flash-preview"

st.set_page_config(page_title="Food Science Problem Solving Exam", layout="centered")

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "log_file" not in st.session_state:
    st.session_state.log_file = f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# --- SYSTEM PROMPT ---
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

# --- UI LAYOUT ---
st.title("Food Science Lab: Case Study Exam")
st.subheader("Scenario: The Browning Strawberry Bar")
st.info("""
**Complaint:** A strawberry bar turns brown and tastes 'toasted' after storage. 
**Ingredients:** Whey protein, strawberry purée, cane sugar, honey, pH 6.0, Aw 0.55.
""")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT LOGIC ---
if prompt := st.chat_input("What is your hypothesis or proposed experiment?"):
    # 1. Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Log the interaction
    with open(st.session_state.log_file, "a") as f:
        f.write(f"USER: {prompt}\n")

    # 3. Generate AI Response using the new SDK chat session
    try:
        # Initialize the chat with the system instruction
        chat = client.chats.create(
            model=MODEL_ID,
            config={'system_instruction': SYSTEM_PROMPT}
        )
        
        # Convert streamlit history to SDK format if needed, 
        # but for a simple flow, we can just send the new prompt 
        # (or send the whole history for context)
        response = chat.send_message(prompt)
        ai_response = response.text
        
        # 4. Display and save AI response
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant"):
            st.markdown(ai_response)
            
        with open(st.session_state.log_file, "a") as f:
            f.write(f"AI: {ai_response}\n\n")
            
    except Exception as e:
        st.error(f"Error calling Gemini: {e}")

# --- PROFESSOR TOOLS ---
with st.sidebar:
    st.header("Admin Controls")
    if st.button("Finalize and Grade"):
        st.warning("Sending full transcript to Gemini for grading...")
        # Grading logic would go here