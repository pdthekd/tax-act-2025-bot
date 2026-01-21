import streamlit as st
from google import genai
from google.genai import types
import time
import requests  # For the secure feedback form

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tax Act 2025 Assistant",
    page_icon="⚖️",
    layout="wide"
)

# --- VISUAL TWEAKS (CSS) ---
st.markdown("""
<style>
    .stChatInput {
        position: fixed;
        bottom: 3rem;
        z-index: 1000;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 8rem;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
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
    SECURE_EMAIL = st.secrets.get("FEEDBACK_EMAIL", "your_email@example.com")
except Exception:
    st.error("⚠️ API Key missing. Check Streamlit Secrets.")
    st.stop()

# --- SYSTEM INSTRUCTIONS ---
SYSTEM_INSTRUCTION = """
Role: You are an expert Chartered Accountant and Tax Research Assistant specializing ONLY in the Income Tax Act 2025.

Context: You have access to the complete 2025 Tax Library (9 Documents).

HIERARCHY OF TRUTH (STRICT COMPLIANCE REQUIRED):
1. TIER 1 (Final Authority): Income_Tax_Act_2025_Final.pdf (THE LAW)
2. TIER 2 (Mapping): ICAI_Tabular_Mapping_2025.pdf (THE TRANSLATOR)
3. TIER 3 (Intent): Memorandums & Reviews (BACKGROUND ONLY)

OPERATIONAL INSTRUCTIONS:
1. CITATION: Every claim must end with a citation: [File Name, Section X].
2. MAPPING LOGIC: If the user mentions an "Old Section" (e.g., 54B), you MUST:
   a. Check 'ICAI_Tabular_Mapping_2025.pdf' to find the corresponding "New Section".
   b. Read the "New Section" in 'Income_Tax_Act_2025_Final.pdf'.
   c. Answer based *only* on the text of the NEW Section.
3. DEPTH: Do not summarize. List ALL conditions explicitly using bullet points.
4. AUDIO INPUT: If input is audio, transcribe intent first, then answer strictly based on documents.

VERIFICATION PROTOCOL (PERFORM BEFORE ANSWERING):
- Did I quote a section from the 1961 Act? -> STOP. Find the 2025 equivalent.
- Did I answer from memory? -> STOP. Check the provided PDF text.
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

# --- INIT STATE ---
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am ready. Ask me about any section (Old or New)."}]

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Tax Assistant")
    st.caption("Unofficial Tool • Gemini 2.5")
    st.warning("⚠️ **Disclaimer:** Educational research only. Verify citations.")
    st.divider()
    
    # Secure Feedback
    with st.expander("🐞 Report an Issue"):
        with st.form("feedback_form"):
            st.write("Send feedback anonymously.")
            user_msg = st.text_area("What went wrong?", placeholder="E.g., The bot cited the wrong section...")
            last_context = str(st.session_state.messages[-2:]) if len(st.session_state.messages) > 1 else "No history."
            if st.form_submit_button("Send Report"):
                try:
                    requests.post(f"https://formsubmit.co/{SECURE_EMAIL}", data={"message": user_msg, "context": last_context, "_captcha": "false"})
                    st.success("Sent!")
                except:
                    st.error("Error sending.")

    st.divider()
    if st.button("🔄 Start New Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Conversation cleared. Ready."}]
        st.rerun()

    st.divider()
    with st.expander("📂 Source Documents (9)"):
        st.success("✅ System Online")

# --- MAIN CHAT ---
st.title("Tax Act 2025 Research Assistant")
st.markdown("Ask questions with **Voice** 🎙️ or **Text** ⌨️.")

for msg in st.session_state.messages:
    if msg["role"] == "user" and "Audio" in msg.get("type", ""):
        st.chat_message("user").audio(msg["content"])
    else:
        st.chat_message(msg["role"]).write(msg["content"])

# --- INPUT ---
col1, col2 = st.columns([0.85, 0.15])
with col1: text_input = st.chat_input("Type question...")
with col2: audio_input = st.audio_input("🎙️")

user_prompt = audio_input if audio_input else text_input
is_audio = True if audio_input else False

if user_prompt:
    # 1. UI Update
    if is_audio:
        st.session_state.messages.append({"role": "user", "content": user_prompt, "type": "Audio"})
        with st.chat_message("user"): st.audio(user_prompt)
    else:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"): st.write(user_prompt)

    # 2. Logic
    with st.chat_message("assistant"):
        start_time = time.time()
        with st.status("🧠 Checking History & Documents...", expanded=True) as status:
            try:
                # --- MEMORY RECONSTRUCTION (THE FIX) ---
                gemini_history = []
                
                # A. Add Files to History (Context Pinning)
                file_parts = [types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type) for f in st.session_state.knowledge_base]
                file_parts.append(types.Part.from_text(text="Reference these documents for all answers."))
                gemini_history.append(types.Content(role="user", parts=file_parts))
                gemini_history.append(types.Content(role="model", parts=[types.Part.from_text(text="Understood.")]))
                
                # B. Add Chat History (Text Only)
                for msg in st.session_state.messages:
                    if msg['role'] == "assistant" and "I am ready" in str(msg['content']): continue # Skip greeting
                    
                    # Convert to Gemini format
                    role = "user" if msg['role'] == "user" else "model"
                    
                    # Only add TEXT messages to history to save bandwidth/tokens
                    if isinstance(msg['content'], str):
                         gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])]))

                # --- CURRENT TURN SETUP ---
                current_parts = []
                if is_audio:
                    current_parts.append(types.Part.from_bytes(data=user_prompt.getvalue(), mime_type="audio/wav"))
                    current_parts.append(types.Part.from_text(text="Listen to this question. If it mentions an Old Section, MAP it first."))
                else:
                    current_parts.append(types.Part.from_text(text=user_prompt))

                # --- GENERATE ---
                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3),
                    history=gemini_history # <--- MEMORY INJECTED HERE
                )

                response_stream = chat.send_message_stream(current_parts)
                full_response = st.write_stream((chunk.text for chunk in response_stream if chunk.text))
                
                status.update(label=f"✅ Complete ({time.time() - start_time:.2f}s)", state="complete", expanded=False)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.rerun() # Refresh for Sidebar Download

            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

# --- DOWNLOAD LOGIC (After Rerun) ---
if len(st.session_state.messages) > 1:
    chat_text = "TAX LOG\n=======\n\n"
    for msg in st.session_state.messages:
        content = "[Audio]" if isinstance(msg['content'], bytes) else msg['content']
        chat_text += f"[{msg['role'].upper()}]:\n{content}\n\n"
    with st.sidebar:
        st.download_button("📥 Download Log", chat_text, "tax_log.txt", "text/plain", type="primary")
