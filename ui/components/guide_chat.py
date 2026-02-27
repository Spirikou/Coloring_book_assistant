"""Chat component for documentation Q&A in the Guide tab."""

import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from utils.doc_retriever import retrieve

SYSTEM_PROMPT = """You are a helpful assistant for the Coloring Book Workflow Assistant app.
Answer questions based ONLY on the provided documentation excerpts. Be concise and user-friendly.
If the documentation does not contain relevant information, say so clearly.
Do not make up information. If asked about features, explain what the docs say."""


def _answer_question(query: str, context_chunks: list) -> str:
    """Generate an answer using the LLM with retrieved context."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OpenAI API key not set. Please set OPENAI_API_KEY in your .env file."
    context = "\n\n---\n\n".join(
        f"[From: {source}]\n{chunk}" for chunk, source in context_chunks
    )
    if not context.strip():
        context = "No relevant documentation found."
    from config import GUIDE_CHAT_MODEL, GUIDE_CHAT_MODEL_TEMPERATURE
    llm = ChatOpenAI(
        model=GUIDE_CHAT_MODEL,
        temperature=GUIDE_CHAT_MODEL_TEMPERATURE,
        api_key=api_key,
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Documentation:\n\n{context}\n\nUser question: {query}"),
    ]
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"Error generating answer: {str(e)}"


def render_guide_chat():
    """Render the chat UI for documentation Q&A."""
    if "guide_chat_history" not in st.session_state:
        st.session_state.guide_chat_history = []

    for msg in st.session_state.guide_chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about this app..."):
        st.session_state.guide_chat_history.append({"role": "user", "content": prompt})
        with st.spinner("Looking up documentation..."):
            chunks = retrieve(prompt, k=5)
            answer = _answer_question(prompt, chunks)
        st.session_state.guide_chat_history.append({"role": "assistant", "content": answer})
        st.rerun()
