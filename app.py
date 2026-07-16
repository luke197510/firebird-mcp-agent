"""
Firebird MCP Agent — Frontend Streamlit
Layout: chat a sinistra | artifact + export a destra
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agents.db_agent import DbSession
from ui import extract_tables
from export import dataframes_to_excel, artifact_to_pdf, artifact_to_word

st.set_page_config(
    page_title="Firebird MCP Agent",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS minimale per nascondere il menu hamburger e stringere i padding ──
st.markdown("""
<style>
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  .block-container {padding-top: 1.5rem; padding-bottom: 0;}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────
if "db_session" not in st.session_state:
    with st.spinner("Inizializzazione agente il Database..."):
        st.session_state.db_session = DbSession()

if "chat_history" not in st.session_state:
    st.session_state.chat_history: list[dict] = []

if "last_artifact" not in st.session_state:
    st.session_state.last_artifact: str = ""

# ── Layout ────────────────────────────────────────────────────────────────
col_chat, col_artifact = st.columns([4, 6], gap="large")

# ── Colonna sinistra: chat ────────────────────────────────────────────────
with col_chat:
    st.subheader("💬 Conversazione")

    chat_box = st.container(height=560)
    with chat_box:
        if not st.session_state.chat_history:
            st.caption("Ciao! Chiedi qualcosa sul Database.")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    prompt = st.chat_input("Chiedi al Database...")

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("Elaborazione in corso…"):
            try:
                response = st.session_state.db_session.ask(prompt)
            except Exception as e:
                response = f"⚠️ Errore durante l'elaborazione: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.session_state.last_artifact = response
        st.rerun()

# ── Colonna destra: artifact + export ────────────────────────────────────
with col_artifact:
    st.subheader("📊 Risultato")

    if not st.session_state.last_artifact:
        st.info("La risposta dell'agente apparirà qui con tabelle interattive e opzioni di export.")
    else:
        artifact = st.session_state.last_artifact
        clean_text, dataframes = extract_tables(artifact)

        # Testo formattato
        st.markdown(clean_text)

        # Tabelle come DataFrame interattivi
        for i, df in enumerate(dataframes):
            if len(dataframes) > 1:
                st.caption(f"Tabella {i + 1}")
            st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Export ───────────────────────────────────────────────────────
        st.divider()
        st.caption("Esporta risultato")
        exp1, exp2, exp3, exp4 = st.columns(4)

        if dataframes:
            with exp1:
                st.download_button(
                    "⬇ Excel",
                    data=dataframes_to_excel(dataframes),
                    file_name="export_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        with exp2:
            st.download_button(
                "⬇ PDF",
                data=artifact_to_pdf(clean_text, dataframes),
                file_name="export_export.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with exp3:
            st.download_button(
                "⬇ Word",
                data=artifact_to_word(clean_text, dataframes),
                file_name="export_export.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with exp4:
            st.download_button(
                "⬇ Testo",
                data=artifact.encode("utf-8"),
                file_name="export_risposta.txt",
                mime="text/plain",
                use_container_width=True,
            )
