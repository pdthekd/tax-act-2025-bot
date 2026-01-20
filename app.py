import streamlit as st
from google import genai
from google.genai import types
import time
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tax Act 2025 (BETA)",
    page_icon="🧪",
    layout="wide"
)

# --- VISUAL TWEAKS (CSS) ---
# FIX: Removed the "background-color" rule so Dark Mode works correctly.
st.markdown("""
<style>
    .stChatInput {
        position: fixed;
        bottom: 3rem;
        z-index: 1000;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
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
    
    # Sidebar Loading UI
    with st.sidebar:
        status_placeholder = st.empty()
        
        # This block handles the loading animation
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
            
            # This is the line that caused the error before. It is fixed now.
            status.update(label="✅ Ready", state="complete", expanded=False)
        
        # Remove the status box after 2 seconds
        time.sleep(2)
        status_placeholder.empty()
        
    return uploaded_files

# --- SIDEBAR: ACTIONS ---
with st.sidebar:
    st.title("🧪 Beta Bot")
    st.caption("Gemini 2.5 Flash • Testing Mode")
    st.divider()

    st.subheader("📝 Session Actions")
    
    # Export Button
    if "messages" in st.session_state:
        chat_text = "TAX RESEARCH LOG\n================\n\n"
        for msg in st.session_state.messages:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            chat_text += f"[{role}]:\n{msg['content']}\n\n{'-'*40}\n\n"
            
        st.download_button(
            label="📥 Download Research (.txt)",
            data=chat_text,
            file_name="tax_research_session.txt",
            mime="text/plain",
            type="primary"
        )
    
    # Clear Button
    if st.button("🔄 Start New Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Conversation cleared. Ready for new queries."}]
        st.rerun()

    st.divider()

    # File List (Collapsed)
    with st.expander("📂 View Source Documents (9)"):
        st.caption("The bot is reading these files:")
        st.text("1. Income_Tax_Act_2025_Final.pdf")
        st.text("2. ICAI_Tabular_Mapping_2025.pdf")
        st.text("3. Memorandum_Part_1.pdf")
        st.text("4. Memorandum_Part_2.pdf")
        st.text("5. Memorandum_Part_3.pdf")
        st.text("6. Memorandum_Part_4.pdf")
        st.text("7. Suggestions_Review.pdf")
        st.text("8. ICAI_Suggestions_Bill.pdf")
        st.text("9. ICAI_Suggestions_Act.pdf")
        st.success("✅ Active")

# --- MAIN APP LOGIC ---

# 1. Initialize DB
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()

# 2. Title
st.title("Tax Act 2025 Research Assistant (BETA)")
st.markdown("Ask complex questions about sections, rates, and rationale.")

# 3. History
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am the Beta Bot. I am ready."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 4. Input & Response
if prompt := st.chat_input("Ex: What are the conditions for Section 194C?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        start_time = time.time()
        
        with st.status("🔍 Analyzing Documents...", expanded=True) as status:
            st.write("• Consulting Income Tax Act 2025...")
            time.sleep(0.2)
            
            try:
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

                response_stream = chat.send_message_stream(prompt)
                
                def stream_parser(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                full_response = st.write_stream(stream_parser(response_stream))
                
                end_time = time.time()
                elapsed_time = end_time - start_time
                status.update(label=f"✅ Complete ({elapsed_time:.2f}s)", state="complete", expanded=False)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")
