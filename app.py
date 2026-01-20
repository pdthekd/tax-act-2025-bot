import streamlit as st
from google import genai
from google.genai import types
import time
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tax Act 2025 Assistant",
    page_icon="⚖️",
    layout="wide"
)

# --- VISUAL TWEAKS (CSS) ---
# This makes the sidebar headers pop and cleans up the chat input
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #f9f9fb;
    }
    .stChatInput {
        position: fixed;
        bottom: 3rem;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- API SETUP ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing. Check Streamlit Secrets.")
    st.stop()

# --- SYSTEM INSTRUCTIONS ---
SYSTEM_INSTRUCTION = """
Role: You are an expert Chartered Accountant and Tax Research Assistant.
Context: You have access to the complete 2025 Tax Library (9 Documents). 
Hierarchy of Truth:
1. TIER 1 (Final Authority): Income_Tax_Act_2025_Final.pdf
2. TIER 2 (Mapping): ICAI_Tabular_Mapping_2025.pdf
3. TIER 3 (Intent): Memorandums & Reviews.

OPERATIONAL INSTRUCTIONS:
1. CITATION: Always cite the specific file name and section number.
2. MAPPING: If the user asks about an Old Section, explicitly map it to the New Section.
3. DEPTH: Do not summarize. List ALL conditions explicitly using bullet points.
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
    
    # We use a placeholder to show loading status, then clear it
    with st.sidebar:
        status_placeholder = st.empty()
        with status_placeholder.status("📚 Initializing Library...", expanded=True) as status:
            for i, filename in enumerate(file_names):
                status.write(f"Loading: {filename[:20]}...")
                try:
                    with open(filename, "rb") as f:
                        myfile = client.files.upload(file=f, config={'display_name': filename})
                    while myfile.state.name == "PROCESSING":
                        time.sleep(1)
                        myfile = client.files.get(name=myfile.name)
                    uploaded_files.append(myfile)
                except Exception as e:
                    st.error(f"Error: {filename}")
            status.update(label="✅ Ready",
