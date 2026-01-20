import streamlit as st
import google.generativeai as genai
import os
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Tax Act 2025 (BETA)", page_icon="🧪")

# --- API SETUP ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Key missing.")
    st.stop()

# --- SYSTEM INSTRUCTIONS ---
#SYSTEM_INSTRUCTION = """
#Role: You are an expert Chartered Accountant.
#Context: Answer strictly based on the provided Income Tax Act 2025 and Memorandum.
#Rules:
#1. Use 'ICAI_Tabular_Mapping_2025.pdf' to map Old Sections to New Sections.
#2. Quote the 'Income_Tax_Act_2025_Final.pdf' as the final authority.
#"""

# --- ENHANCED SYSTEM INSTRUCTIONS ---
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

# --- FILE CONFIGURATION (Testing FULL Database) ---
@st.cache_resource
def upload_knowledge_base():
    # We uncomment ALL files to test if 'Flash' can handle them
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
    status_bar = st.progress(0, text="Loading Full Knowledge Base...")
    
    for i, filename in enumerate(file_names):
        try:
            status_bar.progress((i + 1) / len(file_names), text=f"Processing: {filename}")
            myfile = genai.upload_file(filename)
            while myfile.state.name == "PROCESSING":
                time.sleep(1)
                myfile = genai.get_file(myfile.name)
            uploaded_files.append(myfile)
        except Exception as e:
            st.warning(f"Skipped {filename}: {e}")
            
    status_bar.empty()
    return uploaded_files

# --- MAIN APP ---
st.title("🧪 Tax Bot (Beta Testing)")

if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()
    st.success(f"✅ Loaded {len(st.session_state.knowledge_base)} documents!")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am the Beta Bot. I have read ALL files."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Ask about Rationale or Sections..."):
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        # TEST 1: Try 'gemini-1.5-flash' (Best for large context)
        # If this fails, try 'gemini-1.5-pro-002'
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp", 
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        chat = model.start_chat(history=[
            {"role": "user", "parts": st.session_state.knowledge_base + ["System Ready."]},
            {"role": "model", "parts": ["Understood."]}
        ])
        
        response = chat.send_message(prompt)
        st.chat_message("assistant").write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        
    except Exception as e:
        st.error(f"Beta Test Failed: {e}")
