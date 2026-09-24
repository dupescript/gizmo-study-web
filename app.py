import streamlit as st
import openai
import json
import pypdf
import io
import random

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

# Page Layout Setup
st.set_page_config(page_title="Gizmo AI Study & Trivia", page_icon="🎯", layout="centered")

# --- INITIALIZE SESSION STATE ---
if "cards" not in st.session_state:
    st.session_state.cards = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}

# --- HELPER FUNCTIONS ---
def generate_cards_fast(prompt: str):
    last_err = ""
    for model_id in PREFERRED_MODELS:
        try:
            response = client.chat.completions.create(
                model=model_id,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response, None
        except Exception as e:
            last_err = str(e)
            continue
    return None, last_err

# --- HEADER ---
st.title("🎯 Gizmo AI Study & Trivia")
st.markdown("Generate AI flashcards from your class notes or PDFs and test your knowledge!")

# --- TABS ---
tab_gen, tab_quiz = st.tabs(["📚 Generate Flashcards", "🎮 Play Trivia"])

# ==========================================
# TAB 1: GENERATE FLASHCARDS
# ==========================================
with tab_gen:
    st.header("Upload Study Material")
    
    uploaded_file = st.file_uploader("Upload a PDF or TXT file", type=["pdf", "txt"])
    notes_input = st.text_area("Or paste your text notes directly:")
    card_count = st.slider("Number of Flashcards to generate", min_value=3, max_value=25, value=10)
    clear_existing = st.checkbox("Clear previous deck before generating new cards", value=True)

    if st.button("🚀 Generate Flashcards", type="primary", use_container_width=True):
        extracted_text = ""

        if uploaded_file:
            if uploaded_file.name.endswith(".pdf"):
                try:
                    reader = pypdf.PdfReader(uploaded_file)
                    for page in reader.pages:
                        extracted_text += (page.extract_text() or "") + "\n"
                except Exception as e:
                    st.error(f"Failed to read PDF: {e}")
            elif uploaded_file.name.endswith(".txt"):
                extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
        elif notes_input.strip():
            extracted_text = notes_input.strip()

        if not extracted_text.strip():
            st.warning("⚠️ Please upload a document or paste text first.")
        else:
            with st.spinner("✨ Generating AI flashcards via Groq..."):
                extracted_text = extracted_text[:15000]
                
                prompt = f"""
                Extract exactly {card_count} unique multiple-choice study flashcards from the text below.
                Return ONLY a valid JSON object with a single key "cards" containing an array of objects.
                Each object MUST have:
                - "question": string
                - "options": list of 4 short strings
                - "answer": exact string matching one of the options
                
                Source Text:
                {extracted_text}
                """

                response, err = generate_cards_fast(prompt)

                if not response:
                    st.error(f"❌ Failed to generate cards: {err}")
                else:
                    try:
                        data = json.loads(response.choices[0].message.content)
                        new_cards = data.get("cards", [])

                        for card in new_cards:
                            random.shuffle(card["options"])

                        if clear_existing:
                            st.session_state.cards = new_cards
                        else:
                            st.session_state.cards.extend(new_cards)

                        st.session_state.current_index = 0
                        st.session_state.score = 0
                        st.session_state.user_answers = {}

                        st.success(f"🎉 Successfully created {len(new_cards)} flashcards! Switch to the **Play Trivia** tab to start.")
                    except Exception as e:
                        st.error(f"❌ Failed to parse response: {e}")

# ==========================================
# TAB 2: PLAY TRIVIA
# ==========================================
with tab_quiz:
    cards = st.session_state.cards
    idx = st.session_state.current_index

    if not cards:
        st.info("ℹ️ No flashcards available yet. Go to the **Generate Flashcards** tab to create some!")
    elif idx >= len(cards):
        st.balloons()
        st.subheader("🏆 TRIVIA COMPLETED!")
        st.metric(label="Final Score", value=f"{st.session_state.score} / {len(cards)}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Play Again", use_container_width=True):
                st.session_state.current_index = 0
                st.session_state.score = 0
                st.session_state.user_answers = {}
                st.rerun()
        with col2:
            if st.button("🗑️ Clear Deck", use_container_width=True):
                st.session_state.cards = []
                st.session_state.current_index = 0
                st.session_state.score = 0
                st.session_state.user_answers = {}
                st.rerun()
    else:
        card = cards[idx]
        progress = (idx + 1) / len(cards)
        st.progress(progress, text=f"Question {idx + 1} of {len(cards)}")

        st.subheader(f"Q: {card['question']}")

        # Answer Selection
        selected_option = st.radio(
            "Select your answer:",
            card["options"],
            key=f"radio_{idx}"
        )

        col_sub, col_skip = st.columns([2, 1])

        with col_sub:
            if st.button("Lock In Answer 🔒", type="primary", use_container_width=True):
                correct = card["answer"]
                if selected_option == correct:
                    st.success("🎉 Correct Answer!")
                    st.session_state.score += 1
                else:
                    st.error(f"❌ Wrong! Correct answer: **{correct}**")

                st.session_state.current_index += 1
                st.session_state.user_answers[idx] = selected_option
                st.rerun()

        with col_skip:
            if st.button("Skip Question ➡️", use_container_width=True):
                st.session_state.current_index += 1
                st.rerun()