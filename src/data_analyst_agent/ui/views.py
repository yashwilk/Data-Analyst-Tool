"""The ONLY module in ui/ that calls st.* -- everything else fetches data."""

from __future__ import annotations

import base64

import streamlit as st


def render_health_status(is_healthy: bool) -> None:
    if is_healthy:
        st.sidebar.success("Backend: online")
    else:
        st.sidebar.error("Backend: unreachable")


def render_error(message: str) -> None:
    st.error(message)


def render_login_form() -> tuple[str, str] | None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")
    return (email, password) if submitted else None


def render_register_form() -> tuple[str, str] | None:
    with st.form("register_form"):
        email = st.text_input("Email", key="register_email")
        password = st.text_input(
            "Password", type="password", key="register_password", help="At least 8 characters"
        )
        submitted = st.form_submit_button("Create account", type="primary")
    return (email, password) if submitted else None


def render_schema_panel(schema: dict | None) -> None:
    st.sidebar.subheader("Dataset")
    if not schema:
        st.sidebar.caption("Schema unavailable")
        return
    st.sidebar.caption(f"Table `{schema['table_name']}` -- {schema['row_count']} rows")
    with st.sidebar.expander("Columns"):
        for col in schema["columns"]:
            st.markdown(f"**{col['name']}** ({col['dtype']})")
            st.caption(f"e.g. {col['sample_values']}")


def render_chat_turn(question: str, answer: str) -> None:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        st.write(answer)


def render_charts(charts: list[dict]) -> None:
    if not charts:
        return
    st.subheader("Charts")
    for chart in charts:
        image_bytes = base64.b64decode(chart["image_base64"])
        st.image(image_bytes, caption=f"{chart['title']} -- {chart['caption']}")


def render_research_report(result: dict) -> None:
    st.markdown(result["answer"])

    if result.get("key_findings"):
        st.subheader("Key findings")
        for finding in result["key_findings"]:
            st.markdown(f"- {finding}")

    render_charts(result.get("charts", []))

    with st.expander("SQL queries used"):
        for sql in result.get("queries_used", []):
            st.code(sql, language="sql")
