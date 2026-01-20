import streamlit as st
import google.generativeai as genai
import os
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tax Act 2025 Assistant",
    page_icon="⚖️",
    layout="centered"
)

# --- API SETUP ---
# We get the API Key from Streamlit Secrets (configured later)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Key not found. Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# --- SYSTEM INSTRUCTIONS (Your "Brain") ---
SYSTEM_INSTRUCTION = """
Role: You are an expert Chartered Accountant and Tax Research Assistant.

Context & Source Material:
You have access to 9 specific documents. You must follow this strict "Hierarchy of Truth":

TIER 1: THE LAW (Final Authority)
- File: Income_Tax_Act_2025_Final.pdf
- Usage: Absolute truth. All rates, penalties, and compliance MUST come from here.

TIER 2: THE TRANSLATOR (Section Mapping)
- File: ICAI_Tabular_Mapping_2025.pdf
- Usage: Use when user asks about Old vs. New sections.

TIER 3: THE CONTEXT & INTENT (Background)
- Files: Memorandum_of_Suggestions parts 1-4, ICAI_Suggestions_Review.
- Usage: Use strictly for "Rationale" or "Background". Do not cite as law.

OPERATIONAL INSTRUCTIONS:
1. Citation: Explicitly state the source file name when quoting.
2. Section Mapping: If user asks about an Old Section, find the New Section in the Mapping file first.
3. Formatting: Use Markdown tables for comparisons.
"""

# --- FILE UPLOADER FUNCTION (Cached for Speed) ---
@st.cache_resource
def upload_knowledge_base():
    """
    This function uploads the PDFs to Gemini once when the app starts.
    It returns the list of file handles.
    """
    file_names = [
        "Income_Tax_Act_2025_Final.pdf",
        #"ICAI_Tabular_Mapping_2025.pdf",
        #"Memorandum_of_Suggestions_2025-part-1.pdf",
        #"Memorandum_of_Suggestions_2025-part-2.pdf",
        #"Memorandum_of_Suggestions_2025-part-3.pdf",
        #"Memorandum_of_Suggestions_2025-part-4.pdf",
        #"ICAI_Suggestions_Review.pdf",
        #"ICAI's suggestions considered in the Income-tax Bill 2025 tabled in the Lok Sabha on 13.02.2025.pdf",
        #"ICAI's Suggestions considered in the Income-tax Act, 2025.pdf"
    ]
    
    uploaded_files = []
    status_bar = st.progress(0, text="Initializing Knowledge Base...")
    
    for i, filename in enumerate(file_names):
        try:
            status_bar.progress((i + 1) / len(file_names), text=f"Loading: {filename}")
            # Upload to Gemini
            myfile = genai.upload_file(filename)
            
            # Wait for processing
            while myfile.state.name == "PROCESSING":
                time.sleep(2)
                myfile = genai.get_file(myfile.name)
            
            uploaded_files.append(myfile)
            
        except Exception as e:
            st.warning(f"Could not load {filename}. Make sure it is in the GitHub folder. Error: {e}")
            
    status_bar.empty()
    return uploaded_files

# --- MAIN APP UI ---
st.title("⚖️ Tax Act 2025 Research Bot")
st.markdown("Use this tool to search across the **Final Act**, **Mapping Table**, and **ICAI Suggestions**.")

# 1. Initialize the Knowledge Base
if "knowledge_base" not in st.session_state:
    with st.spinner("Connecting to Tax Documents... (This takes 30s once)"):
        st.session_state.knowledge_base = upload_knowledge_base()
        st.success("Knowledge Base Loaded!")

# 2. Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I have read the Income Tax Act 2025 and related ICAI documents. Ask me about any section, rate, or rationale."}
    ]

# 3. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Handle User Input
if prompt := st.chat_input("Ask about Section 45, TDS rates, or old vs new provisions..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Configure Model with the uploaded files + System Instructions
            model = genai.GenerativeModel(
                model_name="gemini-2.5-pro",
                system_instruction=SYSTEM_INSTRUCTION
            )
            
            # Start Chat with the files in history
            chat_session = model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": st.session_state.knowledge_base + ["Hello, I am ready."]
                    },
                    {
                        "role": "model",
                        "parts": ["Understood. I have access to the 9 documents. Ready for queries."]
                    }
                ]
            )
            
            # Send the actual user query (send history logic is simplified here for stability)
            response = chat_session.send_message(prompt)
            message_placeholder.markdown(response.text)
            
            # Save response
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            message_placeholder.error(f"An error occurred: {e}")
