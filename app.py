
import streamlit as st
from langchain_core.messages import HumanMessage
from agents.data_agent import data_agent

st.set_page_config(
    page_title="AI Data Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Data Agent")
st.caption("Ask questions about your database, extract API data, or transform datasets.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(
    "Ask about your data or request an ETL operation..."
):
    st.session_state.chat_history.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI Agent is processing your request..."):
            try:
                response = data_agent.invoke({
                    "messages": [HumanMessage(content=prompt)],
                    "route_response": ""
                })

                # Find the final assistant response
                messages = response.get("messages", [])
                answer = response.get("final_answer", "")

                if not answer:
                    for message in reversed(messages):
                        content = getattr(message, "content", "")
                        if (
                            getattr(message, "type", "") == "ai"
                            and isinstance(content, str)
                            and content.strip()
                            and not getattr(message, "tool_calls", None)
                        ):
                            answer = content
                            break

                if not answer:
                    answer = "The agent completed, but no final text response was found."

                st.markdown(answer)

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer
                })

                with st.expander("Execution details"):
                    st.write(
                        "Selected route:",
                        response.get("route_response", "Unknown")
                    )

            except Exception as e:
                st.error(f"Agent error: {e}")

if st.button("Clear chat"):
    st.session_state.chat_history = []
    st.rerun()
