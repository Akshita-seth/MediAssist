# ============================================
# app.py — FULL FILE (replace existing)
# ============================================

import streamlit as st
import os
import sys
import tempfile
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__)))

from generator import answer_question
from embed_store import store_chunks_ephemeral

st.set_page_config(page_title="MediAssist", page_icon="🩺")

# ---- Sidebar: eval metrics (update these if you rerun eval_harness.py) ----
with st.sidebar:
    st.markdown("### Measured Accuracy")
    st.caption("From eval_harness.py, run on a 95-question held-out test set")
    st.metric("Refusal accuracy", "100% (95/95)")
    st.metric("Retrieval hit rate", "94.4% (67/71)")
    st.metric("Hallucination rate", "8.5% (6/71)")

st.title("🩺 MediAssist")
st.caption("Ask questions about your medical documents — grounded answers only, no medical advice.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = {}

pdf_folder = "data/raw_pdfs"
available_docs = sorted([f for f in os.listdir(pdf_folder) if f.endswith('.pdf')])

st.subheader("Upload your own document")
uploaded_file = st.file_uploader("Upload a medical PDF", type=["pdf"])

if uploaded_file is not None and uploaded_file.name not in st.session_state.uploaded_docs:
    with st.spinner(f"Processing {uploaded_file.name}..."):
        temp_dir = os.path.join(tempfile.gettempdir(), st.session_state.session_id)
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)

        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            upload_collection_name = f"upload_{st.session_state.session_id}"
            store_chunks_ephemeral(temp_path, collection_name=upload_collection_name)
            st.session_state.uploaded_docs[uploaded_file.name] = temp_path
            st.success(f"{uploaded_file.name} processed — select it below to ask questions.")
        except Exception as e:
            st.error(f"Couldn't process this document: {e}")

if st.session_state.uploaded_docs:
    if st.button("Clear uploaded documents"):
        st.session_state.uploaded_docs = {}
        st.rerun()

doc_source = st.radio("Document source", ["Sample documents", "My uploaded document"], horizontal=True)

collection_name = None

if doc_source == "Sample documents":
    selected_doc = st.selectbox("Select a document", available_docs)
else:
    if not st.session_state.uploaded_docs:
        st.info("Upload a PDF above first.")
        st.stop()
    selected_doc = st.selectbox("Select your uploaded document", list(st.session_state.uploaded_docs.keys()))
    collection_name = f"upload_{st.session_state.session_id}"

question = st.text_input("Ask a question about this document")

if st.button("Get Answer") and question:
    with st.spinner("Thinking..."):
        result = answer_question(question, source_doc=selected_doc, collection_name=collection_name)

    st.markdown("### Answer")

    if result["type"] == "answered":
        st.success(result["text"])
    elif result["type"] == "refused":
        st.warning(f"🚫 **Refused (advice-seeking question)**\n\n{result['text']}")
    elif result["type"] == "not_found":
        st.info(f"❔ **Not found in document**\n\n{result['text']}")
    elif result["type"] == "error":
        st.error(result["text"])

    if result["retrieved"] is not None:
        with st.expander("Show retrieved source chunks (what the model actually saw)"):
            docs = result["retrieved"]["documents"][0]
            metas = result["retrieved"]["metadatas"][0]
            for doc, meta in zip(docs, metas):
                st.markdown(f"**[{meta['section']}]**")
                st.text(doc)
                st.divider()