import streamlit as st
from google import genai
from google.genai import types
import time
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tax Act 2025 (BETA)",
    page_icon="🧪",
    layout="centered"
)

# --- API SETUP (NEW SDK) ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing. Check Streamlit Secrets.")
    st.stop()

# --- SYSTEM INSTRUCTIONS ---
SYSTEM_INSTRUCTION = """
Role: You are an expert Chartered Accountant and Tax Research Assistant.

Context & Source Material:
You have access to the complete 2025 Tax Library (9 Documents). 
You must follow this strict "Hierarchy of Truth":

TIER 1: THE LAW (Final Authority)
- File: Income_Tax_Act_2025_Final.pdf
- Usage: Absolute truth. All rates, penalties, and compliance MUST come from here.

TIER 2: THE TRANSLATOR (Section Mapping)
- File: ICAI_Tabular_Mapping_2025.pdf
- Usage: Use when user asks about Old vs. New sections.

TIER 3: THE INTENT (Background)
- Files: Memorandum_of_Suggestions parts 1-4, Reviews.
- Usage: Use ONLY when user asks for "Rationale", "Reasoning", or "History".

OPERATIONAL INSTRUCTIONS:
1. CITATION: Always cite the specific file name and section number.
2. MAPPING: If the user asks about an Old Section (e.g., 115BAA), explicitly state: "Old Section X corresponds to New Section Y as per the Mapping Table."
3. DEPTH: Do not summarize. If a section has conditions (e.g., "subject to..."), LIST ALL CONDITIONS explicitly.
4. FORMAT: Use bullet points for conditions to make it readable.
"""

# --- FILE CONFIGURATION ---
@st.cache_resource
def upload_knowledge_base():
    # Loading ALL 9 files
    file_names = [
        "Income_Tax_Act_2025_Final.pdf",
        "ICAI_Tabular_Mapping_2025.pdf",
        "Memorandum_of_Suggestions_2025-part-1.pdf",
        "Memorandum_of_Suggestions_2025-part-2.pdf",
        "Memorandum_of_Suggestions_2025-part-3.pdf",
        "Memorandum_of_Suggestions_2025-part-4.pdf",
        "ICAI_Suggestions_Review.pdf",
        "ICAI's suggestions considered in the Income-tax Bill 2025 tabled in the Lok Sabha on 13.02.2025.pdf",
        "ICAI's Suggestions considered in the Income-tax Act, 2025.pdf"
    ]
    
    uploaded_files = []
    
    with st.status("🧪 Initializing Knowledge Base...", expanded=True) as status:
        for i, filename in enumerate(file_names):
            status.write(f"Loading: {filename}...")
            try:
                # 1. Upload using the new SDK
                with open(filename, "rb") as f:
                    myfile = client.files.upload(file=f, config={'display_name': filename})
                
                # 2. Wait for processing
                while myfile.state.name == "PROCESSING":
                    time.sleep(1)
                    myfile = client.files.get(name=myfile.name)
                
                uploaded_files.append(myfile)
                
            except Exception as e:
                st.warning(f"Skipped {filename}: {e}")
        status.update(label="✅ Knowledge Base Ready!", state="complete", expanded=False)
            
    return uploaded_files

# --- MAIN APP UI ---
st.title("🧪 Tax Bot (Beta Testing)")
st.caption("Testing: Gemini 2.5 Flash • Full Database")

# 1. Initialize Knowledge Base
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()

# 2. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "I am ready. Using the new Gemini 2.5 Flash model."}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 3. Handle Input
if prompt := st.chat_input("Ask about Rationale or Sections..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        start_time = time.time()
        
        with st.status("🔍 Researching Tax Laws...", expanded=True) as status:
            st.write("• Consulting Income Tax Act 2025...")
            time.sleep(0.3)
            
            try:
                # B. Create Chat with YOUR SPECIFIC MODEL
                # We found this in your diagnostic list: models/gemini-2.5-flash
                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.3
                    ),
                    history=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=f.uri,
                                    mime_type=f.mime_type
                                ) for f in st.session_state.knowledge_base
                            ] + [types.Part.from_text(text="System Ready.")]
                        ),
                        types.Content(
                            role="model",
                            parts=[types.Part.from_text(text="Understood.")]
                        )
                    ]
                )

                # C. Stream Request
                response_stream = chat.send_message_stream(prompt)
                
                # D. Parse & Display
                def stream_parser(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                full_response = st.write_stream(stream_parser(response_stream))
                
                end_time = time.time()
                elapsed_time = end_time - start_time
                status.update(label=f"✅ Answer Found in {elapsed_time:.2f}s", state="complete", expanded=False)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Beta Test Failed: {e}")
