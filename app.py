# Importing Required Packages
import streamlit as st
from FinalClient import modified_laminate_agent
from langchain.schema import HumanMessage
import time
import asyncio

# Memory Initialization in Streamlit
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "last_hexcode" not in st.session_state:
    st.session_state["last_hexcode"] = None
if "shown_laminates" not in st.session_state:
    st.session_state["shown_laminates"] = {}

# The Streamlit UI
st.set_page_config(page_title="Laminate Finder with Memory")
st.title("Laminate Finder AI Agent")
st.markdown(
    "<div style='font-size:20px; font-weight:bold;'>Ask Something About Laminates</div>",
    unsafe_allow_html=True)

# Reset Button
if st.button("Reset Session"):
    st.session_state["chat_history"] = []
    st.session_state["last_hexcode"] = None
    st.session_state["shown_laminates"] = {}
    st.rerun()

# Display Chat History
if st.session_state["chat_history"]:
    st.markdown("### **Conversation History**")
    for msg in st.session_state["chat_history"]:
        role = "You" if isinstance(msg, HumanMessage) else "Agent"
        st.markdown(f"**{role}:** {msg.content}")

# Defining the Input Box
user_input = st.text_input("", placeholder="What's on your mind")

# What will happen when the Submit button is clicked
if st.button("Submit"):
    if not user_input.strip():
        st.warning("Please enter a prompt.")
    else:
        log_placeholder = st.empty()
        log_messages = [
            "Thinking...",
            "Reading the prompt...",
            "Extracting information...",
            "Querying database...",
            "Fetching laminate details...",
            "Preparing results..."
        ]
        for msg in log_messages:
            log_placeholder.info(msg)
            time.sleep(2.5)

        with st.spinner("The process is running...."):
            asyncio.run(modified_laminate_agent(user_input))

        log_placeholder.success("Result ready!")