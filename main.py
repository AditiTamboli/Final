import streamlit as st
from google import genai
from datetime import date
import re

# ---------- LOAD API FROM STREAMLIT SECRETS ----------
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("❌ GEMINI_API_KEY not found in Streamlit Secrets")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ---------- PAGE ----------
st.set_page_config(page_title="AI Text Summarizer Pro", page_icon="🤖", layout="wide")

# ---------- DAILY RESET ----------
today = str(date.today())

if "day" not in st.session_state:
    st.session_state.day = today
    st.session_state.request_count = 0
    st.session_state.daily_limit = 50

if st.session_state.day != today:
    st.session_state.day = today
    st.session_state.request_count = 0

# ---------- CHAT HISTORY ----------
if "history" not in st.session_state:
    st.session_state.history = []

# ---------- INPUT TEXT STATE ----------
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# ---------- HEADER ----------
st.title("🤖 AI Text Summarizer Pro")
st.caption("Upload file • Hindi/English • Smart summary")
st.markdown("---")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("📊 Usage Today")

    used = st.session_state.request_count
    limit = st.session_state.daily_limit
    remaining = max(0, limit - used)

    st.progress(used / limit if limit else 0)
    st.write(f"Used: **{used}**")
    st.write(f"Remaining: **{remaining}**")

    if st.button("🧹 Clear chat"):
        st.session_state.history = []

# ---------- INPUT AREA ----------
col1, col2 = st.columns([2,1])

with col1:

    if st.button("🧪 Load sample text"):
        st.session_state.input_text = (
            "Blockchain technology is a decentralized digital ledger that records "
            "transactions securely across multiple computers. It ensures transparency, "
            "security, and trust without needing intermediaries. Blockchain is used in "
            "cryptocurrency, supply chains, healthcare records, and digital identity."
        )

    st.text_area("📝 Enter text", height=260, key="input_text")

with col2:
    uploaded = st.file_uploader("📂 Upload txt/pdf", type=["txt","pdf"])

# ---------- FILE READ ----------
if uploaded:
    if uploaded.type == "text/plain":
        st.session_state.input_text = uploaded.read().decode()

    else:
        try:
            from pypdf import PdfReader
            pdf = PdfReader(uploaded)
            text = ""
            for p in pdf.pages:
                text += p.extract_text() or ""
            st.session_state.input_text = text
        except:
            st.warning("PDF read failed")

# ---------- OPTIONS ----------
st.markdown("### ⚙️ Summary Options")

c1, c2, c3 = st.columns(3)

with c1:
    summary_length = st.select_slider(
        "Summary length",
        options=["Very short","Short","Balanced","Detailed","Very detailed"],
        value="Balanced"
    )

with c2:
    max_tokens = st.slider("Max tokens", 50, 1000, 300, 50)

with c3:
    language = st.selectbox("Language", ["English","Hindi"])

format_type = st.radio("Format", ["Paragraph","Bullet points"])

# temperature map
temp_map = {
    "Very short":0.1,
    "Short":0.3,
    "Balanced":0.5,
    "Detailed":0.7,
    "Very detailed":0.9
}
temperature = temp_map[summary_length]

# ---------- GENERATE ----------
if st.button("✨ Generate Summary", use_container_width=True):

    text_input = st.session_state.input_text

    if st.session_state.request_count >= st.session_state.daily_limit:
        st.error("🚫 Daily limit reached")
        st.stop()

    if not text_input.strip():
        st.warning("Enter text first")
        st.stop()

    with st.spinner("🤖 AI is typing..."):

        prompt = f"""
Provide a {summary_length.lower()} summary.

Language: {language}
Format: {format_type}

Text:
{text_input}
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature":temperature,
                    "max_output_tokens":max_tokens
                }
            )

            answer = response.text
            st.session_state.request_count += 1

            # save chat
            preview = f"📄 Text submitted ({len(text_input.split())} words)"
            st.session_state.history.append(("user", preview))
            st.session_state.history.append(("ai", answer))

            # ---------- OUTPUT ----------
            st.subheader("📄 Summary")
            st.write(answer)

            # copy/download
            st.download_button("📋 Copy Summary", answer, file_name="summary.txt")

            # metrics
            original = len(text_input.split())
            summ = len(answer.split())
            reduction = ((original - summ)/original*100) if original else 0

            m1,m2,m3 = st.columns(3)
            m1.metric("Original words", original)
            m2.metric("Summary words", summ)
            m3.metric("Reduction %", f"{reduction:.1f}%")

        except Exception as e:

            txt = str(e)

            if "RESOURCE_EXHAUSTED" in txt or "429" in txt:
                match = re.search(r'quotaValue[^\d]*(\d+)', txt)
                if match:
                    st.session_state.daily_limit = int(match.group(1))

                st.error("🚫 Gemini quota reached")
                st.info(f"Daily limit: {st.session_state.daily_limit}")
            else:
                st.error(txt)

# ---------- CHAT DISPLAY ----------
st.markdown("## 💬 Conversation")

for role, msg in st.session_state.history:
    if role == "user":
        st.markdown(f"🟢 **You:** {msg}")
    else:
        st.markdown(f"🤖 **AI:** {msg}")

# ---------- AUTO SCROLL ----------
st.markdown("""
<script>
window.scrollTo(0, document.body.scrollHeight);
</script>
""", unsafe_allow_html=True)

# ---------- FOOTER ----------
st.markdown("---")
st.caption("Built with Streamlit + Gemini 2.5 Flash")