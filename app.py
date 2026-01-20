import streamlit as st
from google import genai
from google.genai import types
import time
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tax Act 2025 Assistant",
    page_icon="⚖️",
    layout="wide"  # Changed to 'wide' for better reading space
)

# --- CUSTOM CSS (Visual Polish) ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .stChatInput {
        position: fixed;
        bottom: 3rem;
    }
    .stStatus {
        font-size: 0.9rem;
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
    
    # We move the visual loader to the Sidebar!
    with st.sidebar:
        with st.status("📚 Loading Tax Library...", expanded=True) as status:
            for i, filename in enumerate(file_names):
                status.write(f"📄 {filename[:25]}...") # Truncate long names
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
                    st.error(f"Failed: {filename}")
            status.update(label="✅ Library Ready (9 Files)", state="complete", expanded=False)
            
    return uploaded_files

# --- MAIN APP LOGIC ---

# Sidebar: Controls
with st.sidebar:
    st.title("⚖️ Research Tools")
    st.caption("Gemini 2.5 Flash • 2M Context")
    
    # 1. Initialize DB
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = upload_knowledge_base()
    
    st.divider()
    
    # 2. Export Feature
    st.subheader("💾 Export Research")
    if "messages" in st.session_state:
        # Convert chat history to a string
        chat_text = "TAX RESEARCH SESSION LOG\n========================\n\n"
        for msg in st.session_state.messages:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            chat_text += f"[{role}]:\n{msg['content']}\n\n{'-'*40}\n\n"
            
        st.download_button(
            label="Download Session Log (.txt)",
            data=chat_text,
            file_name="tax_research_session.txt",
            mime="text/plain"
        )
    
    # 3. Clear History
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = [{"role": "assistant", "content": "Conversation cleared. Ready for new queries."}]
        st.rerun()

# Main Chat Area
st.title("Tax Act 2025 Research Assistant")
st.markdown("Ask complex questions about sections, rates, and rationale. I will cite the **Final Act** and **Mapping Tables**.")

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am ready. Ask me about TDS, Capital Gains, or Section mappings."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Handle Input
if prompt := st.chat_input("Ex: What are the conditions for Section 194C?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        start_time = time.time()
        
        # Thinking Bubble (Now cleaner)
        with st.status("🔍 Analyzing 9 Legal Documents...", expanded=True) as status:
            st.write("• Consulting Income Tax Act 2025...")
            time.sleep(0.3)
            
            try:
                # Create Chat
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

                # Stream Request
                response_stream = chat.send_message_stream(prompt)
                
                # Parse & Display
                def stream_parser(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                full_response = st.write_stream(stream_parser(response_stream))
                
                # Stats
                end_time = time.time()
                elapsed_time = end_time - start_time
                status.update(label=f"✅ Research Complete ({elapsed_time:.2f}s)", state="complete", expanded=False)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")
