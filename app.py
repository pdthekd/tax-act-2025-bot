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
            status.update(label="✅ Ready", state="complete", expanded=False)
        
        # Once done, we remove the big status box and just show a small indicator
        time.sleep(2)
        status_placeholder.empty()
        
    return uploaded_files

# --- SIDEBAR: "ACTIONS FIRST" DESIGN ---
with st.sidebar:
    st.title("⚖️ Tax Assistant")
    st.caption("Gemini 2.5 Flash • Pro Edition")
    st.divider()

    # SECTION 1: HIGH VALUE ACTIONS (AT THE TOP)
    st.subheader("📝 Session Actions")
    
    # Export Button (Prominent)
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
            type="primary" # Makes the button stand out (filled color)
        )
    
    # Clear Button
    if st.button("🔄 Start New Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Conversation cleared. Ready for new queries."}]
        st.rerun()

    st.divider()

    # SECTION 2: LOW VALUE INFO (COLLAPSED AT BOTTOM)
    # We hide the file list in an expander so it doesn't clutter the view
    with st.expander("📂 View Source Documents (9)"):
        st.caption(" The bot is currently reading these files:")
        st.text("1. Income_Tax_Act_2025_Final.pdf")
        st.text("2. ICAI_Tabular_Mapping_2025.pdf")
        st.text("3. Memorandum_Part_1.pdf")
        st.text("4. Memorandum_Part_2.pdf")
        st.text("5. Memorandum_Part_3.pdf")
        st.text("6. Memorandum_Part_4.pdf")
        st.text("7. Suggestions_Review.pdf")
        st.text("8. ICAI_Suggestions_Bill.pdf")
        st.text("9. ICAI_Suggestions_Act.pdf")
        st.success("✅ All Documents Active")

# --- MAIN APP LOGIC ---

# 1. Initialize DB (Happens silently now)
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()

# 2. Main Title
st.title("Tax Act 2025 Research Assistant")
st.markdown("Ask complex questions about sections, rates, and rationale.")

# 3. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am ready. Ask me about TDS, Capital Gains, or Section mappings."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 4. Handle Input
if prompt := st.chat_input("Ex: What are the conditions for Section 194C?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        start_time = time.time()
        
        # Status Bubble
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
