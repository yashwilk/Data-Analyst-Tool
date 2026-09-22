"""Single-page Streamlit UI.

Two screens in one page, gated by session state:
1. Not logged in -- Login / Register tabs (session_state["token"] unset).
2. Logged in -- the chat box with a mode toggle between Chat (quick
   conversational answers) and Research (deeper analysis + charts).

Thin client only -- all reasoning happens behind the FastAPI backend via
`api_client.py`; this file just wires session state to it and to
`views.py`.
"""

from __future__ import annotations

import streamlit as st

from data_analyst_agent.ui import api_client, views

st.set_page_config(page_title="Data Analyst Agent", page_icon="📊", layout="centered")

if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list[tuple[question, answer]]
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

views.render_health_status(api_client.check_health())

st.title("📊 Data Analyst Agent")

if not st.session_state.token:
    st.caption("Log in or create an account to start asking questions about the dataset.")

    login_tab, register_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        submission = views.render_login_form()
        if submission:
            email, password = submission
            result = api_client.login(email, password)
            if not result["success"]:
                views.render_error(result["error"] or "Login failed")
            else:
                st.session_state.token = result["data"]["access_token"]
                st.session_state.user_email = email
                st.rerun()

    with register_tab:
        submission = views.render_register_form()
        if submission:
            email, password = submission
            result = api_client.register(email, password)
            if not result["success"]:
                views.render_error(result["error"] or "Registration failed")
            else:
                st.session_state.token = result["data"]["access_token"]
                st.session_state.user_email = email
                st.success("Account created!")
                st.rerun()

    st.stop()

token = st.session_state.token

with st.sidebar:
    st.caption(f"Logged in as **{st.session_state.user_email}**")
    if st.button("Log out"):
        st.session_state.token = None
        st.session_state.user_email = None
        st.session_state.chat_history = []
        st.session_state.conversation_id = None
        st.rerun()

views.render_schema_panel(api_client.get_dataset_schema(token))

st.caption("Ask questions about the loaded customer purchase dataset.")

mode = st.radio(
    "Mode",
    options=["💬 Chat", "🔬 Research (deep + charts)"],
    horizontal=True,
    help=(
        "Chat: quick conversational answers, remembers the conversation. "
        "Research: multi-query deep analysis with charts, each question is standalone."
    ),
)

if mode == "💬 Chat":
    for question, answer in st.session_state.chat_history:
        views.render_chat_turn(question, answer)

    question = st.chat_input("Ask a question about the dataset...")
    if question:
        views.render_chat_turn(question, "")
        with st.spinner("Thinking..."):
            result = api_client.call_chat(question, st.session_state.conversation_id, token)

        if not result["success"]:
            views.render_error(result["error"] or "Something went wrong")
        else:
            data = result["data"]
            st.session_state.conversation_id = data["conversation_id"]
            st.session_state.chat_history.append((question, data["answer"]))
            st.rerun()

    if st.session_state.chat_history and st.button("New conversation"):
        st.session_state.chat_history = []
        st.session_state.conversation_id = None
        st.rerun()

else:
    question = st.text_area(
        "What would you like a deep-dive analysis of?",
        placeholder="e.g. Which product categories generate the most revenue, and how has that changed over time?",
    )
    if st.button("Run research", type="primary") and question.strip():
        with st.spinner("Running multi-query analysis, this can take up to a minute..."):
            result = api_client.call_research(question, token)

        if not result["success"]:
            views.render_error(result["error"] or "Something went wrong")
        else:
            views.render_research_report(result["data"])
