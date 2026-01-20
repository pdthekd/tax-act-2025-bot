import streamlit as st
import google.generativeai as genai
import os
import time

# --- PAGE CONFIGURATION (Beta) ---
st.set_page_config(
    page_title="Tax Act 2025 (BETA)",
    page_icon="🧪",
    layout="centered"
)

# --- API SETUP ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
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
    
    with st.status("🧪 Initializing Beta Knowledge Base...", expanded=True) as status:
        for i, filename in enumerate(file_names):
            status.write(f"Loading: {filename}...")
            try:
                myfile = genai.upload_file(filename)
                # Wait for Google to process
                while myfile.state.name == "PROCESSING":
                    time.sleep(1)
                    myfile = genai.get_file(myfile.name)
                uploaded_files.append(myfile)
            except Exception as e:
                st.warning(f"Skipped {filename}: {e}")
        status.update(label="✅ Beta Knowledge Base Ready!", state="complete", expanded=False)
            
    return uploaded_files

# --- HELPER: CLEAN STREAM PARSER ---
def stream_parser(stream):
    for chunk in stream:
        if chunk.text:
            yield chunk.text

# --- MAIN APP UI ---
st.title("🧪 Tax Bot (Beta Testing)")
st.caption("Testing: Gemini 1.5 Flash • Streaming UI • Full Database")

# 1. Initialize Knowledge Base
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()

# 2. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "I am the Beta Bot. I have read ALL files and I am ready to test."}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 3. Handle Input
if prompt := st.chat_input("Ask about Rationale or Sections..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        start_time = time.time()
        
        # A. Thinking Bubble
        with st.status("🔍 Researching Tax Laws...", expanded=True) as status:
            st.write("• Consulting Income Tax Act 2025...")
            time.sleep(0.3) 
            st.write("• Checking ICAI Mapping Table...")
            time.sleep(0.3)
            
            try:
                # B. Configure Model (Using Standard Flash)
                # We use the generic tag "gemini-1.5-flash" to avoid version errors
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash", 
                    system_instruction=SYSTEM_INSTRUCTION
                )
                
                chat_session = model.start_chat(
                    history=[
                        {"role": "user", "parts": st.session_state.knowledge_base + ["System Ready."]},
                        {"role": "model", "parts": ["Understood."]}
                    ]
                )
                
                # C. Stream Request
                response_stream = chat_session.send_message(prompt, stream=True)
                
                # D. Parse & Display
                full_response = st.write_stream(stream_parser(response_stream))
                
                # E. Update Status
                end_time = time.time()
                elapsed_time = end_time - start_time
                status.update(label=f"✅ Answer Found in {elapsed_time:.2f}s", state="complete", expanded=False)
                
                # Save to history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Beta Test Failed: {e}")
