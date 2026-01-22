import streamlit as st
from google import genai
from google.genai import types
import time
import requests  # Required for the secure feedback form backend

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
        /* Remove huge margins on phone screens */
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 1rem !important;
        }
        /* Make chat input stick to bottom on mobile */
        .stChatInput {
            bottom: 0px !important;
            padding-bottom: 20px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- API & SECRETS SETUP ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    # Securely fetch email. If missing, defaults to dummy to prevent crash (but email won't send).
    SECURE_EMAIL = st.secrets.get("FEEDBACK_EMAIL", "your_email@example.com")
except Exception:
    st.error("⚠️ API Key missing. Check Streamlit Secrets.")
    st.stop()

# --- STRICT SYSTEM INSTRUCTIONS (VERIFICATION PROTOCOL) ---
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
- Does my answer cite 'Income_Tax_Act_2025_Final.pdf'? -> If no, RETHINK.
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

# --- INITIALIZE SESSION STATE ---
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = upload_knowledge_base()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I am ready. Ask me about any section (Old or New)."}]

# --- SIDEBAR: DASHBOARD & FEEDBACK ---
with st.sidebar:
    st.title("⚖️ Tax Assistant")
    st.caption("Unofficial Tool • Gemini 2.5")
    
    # SAFETY SHIELD: Visible Disclaimer
    st.warning("⚠️ **Disclaimer:** This AI tool is for educational research only. It is not affiliated with the ICAI. Verify all citations against the official Act.")
    
    st.divider()
    
    # SECURE FEEDBACK FORM
    with st.expander("🐞 Report an Issue"):
        with st.form("feedback_form"):
            st.write("Send feedback anonymously.")
            user_msg = st.text_area("What went wrong?", placeholder="E.g., The bot cited the wrong section...")
            
            # Context Capture (Last 2 Messages)
            last_context = "No history."
            if len(st.session_state.messages) > 1:
                # Simple string conversion of last interaction for debugging
                last_context = str(st.session_state.messages[-2:])
            
            submit_feedback = st.form_submit_button("Send Report")
            
            if submit_feedback:
                if not user_msg:
                    st.error("Please write a message.")
                else:
                    try:
                        # Secure POST to FormSubmit
                        resp = requests.post(
                            f"https://formsubmit.co/{SECURE_EMAIL}",
                            data={
                                "message": user_msg,
                                "context": last_context,
                                "_subject": "Tax Bot Issue Report",
                                "_captcha": "false"
                            }
                        )
                        if resp.status_code == 200:
                            st.success("Report Sent! Thank you.")
                        else:
                            st.error("Failed to send. Try again later.")
                    except Exception as e:
                        st.error(f"Error sending: {e}")

    st.divider()

    # MEMORY USAGE INDICATOR
    msg_count = len(st.session_state.messages)
    st.caption(f"🧠 Memory Usage: {msg_count} turns")
    if msg_count > 20:
        st.warning("Long conversation. Consider clearing chat.")

    if st.button("🔄 Start New Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Conversation cleared. Ready."}]
        st.rerun()

    st.divider()
    st.link_button("Official ICAI Updates", "https://icai.org/post/23274")
    
    with st.expander("📂 Source Documents (9)"):
        st.success("✅ System Online")

# --- MAIN APP UI ---

st.title("Tax Act 2025 Research Assistant")
st.markdown("Ask questions with **Voice** 🎙️ or **Text** ⌨️. The bot prioritizes the **New 2025 Act**.")

# Display Chat History
for msg in st.session_state.messages:
    if msg["role"] == "user" and "Audio" in msg.get("type", ""):
        st.chat_message("user").audio(msg["content"])
    else:
        st.chat_message(msg["role"]).write(msg["content"])

# --- MULTIMODAL INPUT ---
col1, col2 = st.columns([0.85, 0.15])
with col1:
    text_input = st.chat_input("Type your tax question here...")
with col2:
    audio_input = st.audio_input("🎙️")

user_prompt = None
is_audio = False

if audio_input:
    user_prompt = audio_input
    is_audio = True
elif text_input:
    user_prompt = text_input
    is_audio = False

# --- PROCESSING LOGIC ---
if user_prompt:
    
    # 1. Update UI with User Input
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
        
        with st.status("🧠 Analyzing Documents & History...", expanded=True) as status:
            try:
                # --- MEMORY RECONSTRUCTION (SLIDING WINDOW) ---
                gemini_history = []
                
                # A. Always Pin Documents (Long Term Memory)
                file_parts = [types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type) for f in st.session_state.knowledge_base]
                file_parts.append(types.Part.from_text(text="Reference these documents for all answers."))
                gemini_history.append(types.Content(role="user", parts=file_parts))
                gemini_history.append(types.Content(role="model", parts=[types.Part.from_text(text="Understood.")]))
                
                # B. Sliding Window History (Short Term Memory - Last 15 turns)
                # This prevents "Resource Exhausted" errors on Free Tier
                recent_msgs = st.session_state.messages[-15:]
                
                for msg in recent_msgs:
                    if msg['role'] == "assistant" and "I am ready" in str(msg['content']): continue
                    
                    role = "user" if msg['role'] == "user" else "model"
                    
                    # Optimization: Only send TEXT to history. Skip re-uploading heavy audio bytes.
                    if isinstance(msg['content'], str):
                         gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])]))

                # --- CURRENT TURN ---
                current_parts = []
                if is_audio:
                    current_parts.append(types.Part.from_bytes(data=user_prompt.getvalue(), mime_type="audio/wav"))
                    current_parts.append(types.Part.from_text(text="Listen to this question. If it mentions an Old Section, MAP it to the 2025 Act using the Mapping Table, then answer using the 2025 Act."))
                else:
                    current_parts.append(types.Part.from_text(text=user_prompt))

                # --- API CALL ---
                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.3
                    ),
                    history=gemini_history
                )

                response_stream = chat.send_message_stream(current_parts)
                
                def stream_parser(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                full_response = st.write_stream(stream_parser(response_stream))
                
                end_time = time.time()
                status.update(label=f"✅ Complete ({end_time - start_time:.2f}s)", state="complete", expanded=False)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # FORCE RERUN: Updates the sidebar download button with the latest message
                st.rerun() 
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

# --- DOWNLOAD BUTTON LOGIC (Runs on Rerun) ---
# This sits at the end but injects into sidebar to ensure it has the latest state
if len(st.session_state.messages) > 1:
    chat_text = "TAX RESEARCH LOG\n================\n\n"
    for msg in st.session_state.messages:
        content = msg['content']
        if isinstance(content, bytes): content = "[Audio Data]"
        chat_text += f"[{msg['role'].upper()}]:\n{content}\n\n{'-'*40}\n\n"
    
    with st.sidebar:
        st.download_button("📥 Download Log", chat_text, "tax_session.txt", "text/plain", type="primary")
                    
