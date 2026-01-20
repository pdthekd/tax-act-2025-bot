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
st.markdown("""
<style>
    /* 1. Fixed Chat Input */
    .stChatInput {
        position: fixed;
        bottom: 3rem;
        z-index: 1000;
    }
    
    /* 2. Adjust Main Padding (Desktop) */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 8rem; /* Space for the audio widget */
    }

    /* 3. MOBILE OPTIMIZATION */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 1rem !important;
        }
        .stChatInput {
            bottom: 0px !important;
            padding-bottom: 20px !important;
        }
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
4. AUDIO INPUT: If the input is audio, transcribe the intent first, then answer strictly based on the documents.
"""

# --- FILE CONFIGURATION ---
@st.cache_resource
def upload_knowledge_base():
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
        time.sleep(1)
        status_placeholder.empty()
        
    return uploaded_files

# --- SIDEBAR: ACTIONS & DISCLAIMER ---
with st.sidebar:
    st.title("⚖️ Tax Assistant")
    st.caption("Unofficial Research Tool • Gemini 2.5")
    
    # SAFETY SHIELD: Visible Disclaimer
    st.warning("⚠️ **Disclaimer:** This AI tool is for educational research only. It is not affiliated with the ICAI. Verify all citations against the official Act.")
    
    st.divider()

    st.subheader("📝 Actions")
    if "messages" in st.session_state:
        chat_text = "TAX RESEARCH LOG\n================\n\n"
        for msg in st.session_state.messages:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            chat_text += f"[{role}]:\n{msg['content']}\n\n{'-'*40}\n\n"
        st.download_button("📥 Download Log", chat_text, "tax_session.txt", "text/plain", type="primary")
    
    if st.button("🔄 Start New Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Conversation cleared. Ready for new queries."}]
        st.rerun()

    st.divider()
    st.link_button("Official ICAI Updates", "https://icai.org/post/23274")
    
    with st.expander("📂 Source Documents (9)"):
        st.success("✅ System Online")

# --- MAIN APP LOGIC ---

if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()

st.title("Tax Act 2025 Research Assistant")
st.markdown("Ask questions with **Voice** 🎙️ or **Text** ⌨️.")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am ready. Click the microphone to speak or type your question."}]

for msg in st.session_state.messages:
    if msg["role"] == "user" and "Audio" in msg.get("type", ""):
        st.chat_message("user").audio(msg["content"])
    else:
        st.chat_message(msg["role"]).write(msg["content"])

# --- MULTIMODAL INPUT AREA ---
col1, col2 = st.columns([0.85, 0.15])

with col1:
    text_input = st.chat_input("Type your tax question here...")

with col2:
    audio_input = st.audio_input("🎙️")

# Determine Input
user_prompt = None
is_audio = False

if audio_input:
    user_prompt = audio_input
    is_audio = True
elif text_input:
    user_prompt = text_input
    is_audio = False

# PROCESS INPUT
if user_prompt:
    
    # 1. Display User Message
    if is_audio:
        st.session_state.messages.append({"role": "user", "content": user_prompt, "type": "Audio"})
        with st.chat_message("user"):
            st.audio(user_prompt)
    else:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.write(user_prompt)

    # 2. Generate Answer
    with st.chat_message("assistant"):
        start_time = time.time()
        
        with st.status("🧠 Analyzing Input...", expanded=True) as status:
            try:
                # Prepare Content
                user_content_parts = []
                
                # A. Add Files
                for f in st.session_state.knowledge_base:
                    user_content_parts.append(
                        types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type)
                    )
                
                # B. Add User Input
                if is_audio:
                    audio_bytes = user_prompt.getvalue()
                    user_content_parts.append(
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
                    )
                    user_content_parts.append(
                        types.Part.from_text(text="Listen to this question and answer it based on the Tax Act documents.")
                    )
                else:
                    user_content_parts.append(
                        types.Part.from_text(text=user_prompt)
                    )

                # C. Call Gemini 2.5 Flash
                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.3
                    ),
                    history=[] 
                )

                # D. Stream Response
                response_stream = chat.send_message_stream(user_content_parts)
                
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
