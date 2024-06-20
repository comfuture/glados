import asyncio
import streamlit as st
import tempfile
from ...assistant import GLaDOS
from ...util.langchain import load_documents


def explaination():
    """Explanation."""
    st.title("Explanation")
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.markdown(
            """
            Try to chat with the assistant.
            """
        )
        st.chat_message("user").write("Hello, I'm Human. What's your name?")
        st.chat_message("user").write("Write an email to my boss.")
    with col2:
        st.markdown(
            """
            You can also upload a file.
            """
        )
    with col3:
        st.markdown(
            """
            Or continue the previous session.
            """
        )


async def app():
    glados = GLaDOS()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.title("GLaDOS")
        st.header("A simple web app for text generation")

        st.divider()
        """
        ## Files
        - a.txt
        - b.txt
        - c.txt
        """

        files = st.file_uploader(
            "Upload a file",
            type=["txt", "md", "pdf", "docx"],
            accept_multiple_files=True,
        )
        if files:
            for file in files:
                # Save the file to a temporary file
                with tempfile.NamedTemporaryFile(suffix=file.name) as temp_file:
                    temp_file.write(file.read())
                    docs = load_documents(temp_file.name, split=True)
                    st.session_state.messages.append(
                        {
                            "role": "system",
                            "content": f"Reading {file.name}. {len(docs)} documents.",
                        }
                    )

                    temp_file_path = temp_file.name
                    st.write(f"Saved file to: {temp_file_path}")

    if len(st.session_state.messages) < 1:
        explaination()

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Prompt"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        rep = glados.chat(prompt)

        with st.chat_message("assistant"):
            message_holder = st.empty()
            full_message = ""
            async for chunk in rep:
                if isinstance(chunk, dict):
                    message_holder.markdown(f"**{str(chunk['event'])}**")
                else:
                    full_message += chunk
                    message_holder.markdown(full_message + "▌")
            message_holder.markdown(full_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": full_message}
            )


st.button("Send")

with st.expander("Advanced"):
    st.file_uploader("Upload a file2", type=["txt", "md"])


def run():
    # run once
    st.set_page_config(
        page_title="GLaDOS",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="auto",
        menu_items=None,
    )

    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)  # Set it as the current event loop
    try:
        loop.run_until_complete(app())
    finally:
        loop.close()


if __name__ == "__main__":
    run()
