import streamlit as st
import smtplib
from email.mime.text import MIMEText

from google import genai
from google.genai import types

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    SUMMARY_REQUEST_PROMPT
)


MODEL_NAME = "gemini-3-flash-preview"


st.set_page_config(
    page_title="MacroSnap",
    page_icon="🥗"
)


# API and Gmail settings
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


# Gemini client
@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()


# Display messages
def render_message(message):
    with st.chat_message(message["role"]):

        if message["kind"] == "text":
            st.write(message["content"])

        elif message["kind"] == "image":
            st.image(message["content"])


# Add message to conversation
def add_message(role, kind, content):
    st.session_state.messages.append({
        "role": role,
        "kind": kind,
        "content": content
    })


# Ask Gemini
def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text

    except Exception as error:
        return f"Sorry, something went wrong: {error}"


# Create nutrition summary
def create_summary():
    conversation = ""

    for message in st.session_state.messages:

        if message["kind"] == "text":
            conversation += (
                f'{message["role"]}: {message["content"]}\n'
            )

        elif message["kind"] == "image":
            conversation += (
                f'{message["role"]}: Shared a food photo\n'
            )

    prompt = (
        SUMMARY_REQUEST_PROMPT
        + "\n\nConversation:\n"
        + conversation
    )

    response = gemini_client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# Send email
def send_email(to_address, subject, body):

    message = MIMEText(
        body,
        "plain",
        "utf-8"
    )

    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_address

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    ) as server:

        server.login(
            GMAIL_ADDRESS,
            GMAIL_APP_PASSWORD
        )

        server.send_message(message)

    return True, "Email sent successfully"


# --------------------------------------------------
# ONBOARDING
# --------------------------------------------------

if "onboarded" not in st.session_state:

    st.title("🥗 MacroSnap")
    st.caption("Snap it. Track it. Understand it.")

    with st.form("onboarding_form"):

        name = st.text_input("Your name")

        email = st.text_input(
            "Email address",
            placeholder="you@gmail.com"
        )

        submitted = st.form_submit_button(
            "Let's go 🚀"
        )

        if submitted:

            if not name.strip() or not email.strip():

                st.warning(
                    "Please enter your name and email address."
                )

            else:

                st.session_state.name = name.strip()
                st.session_state.email = email.strip()

                st.session_state.chat = (
                    gemini_client.chats.create(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        )
                    )
                )

                st.session_state.messages = []

                st.session_state.onboarded = True

                st.rerun()

    st.stop()


# --------------------------------------------------
# MAIN CHATBOT
# --------------------------------------------------

st.title("🥗 MacroSnap")

st.caption(
    f"Welcome {st.session_state.name}! 👋"
)


# Welcome message
if not st.session_state.messages:

    add_message(
        "assistant",
        "text",
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.name
        )
    )


# Display conversation
for message in st.session_state.messages:
    render_message(message)


# --------------------------------------------------
# CHAT INPUT
# --------------------------------------------------

user_input = st.chat_input(
    "Ask about your food or attach a meal photo",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


if user_input:

    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )

    text = user_input.text

    parts = []


    # Food photo
    if photo is not None:

        photo_bytes = photo.getvalue()

        add_message(
            "user",
            "image",
            photo_bytes
        )

        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type
            )
        )


    # Text message
    if text:

        add_message(
            "user",
            "text",
            text
        )

        parts.append(text)


    # Photo without text
    elif photo is not None:

        parts.append(
            "What is this meal? Give me the calories and macros."
        )


    # Gemini response
    with st.spinner("🤖 Thinking..."):

        answer = ask_gemini(parts)


    add_message(
        "assistant",
        "text",
        answer
    )


    st.rerun()


# --------------------------------------------------
# EMAIL SUMMARY
# --------------------------------------------------

st.divider()

st.subheader("📧 Email Summary")


if st.button("Send Summary to Email"):

    with st.spinner("Preparing your summary..."):

        try:

            summary = create_summary()


            success, info = send_email(
                st.session_state.email,
                "Your MacroSnap Nutrition Summary",
                summary
            )


            if success:

                st.success(
                    "Summary sent to your email! 🎉"
                )

                st.write(summary)


            else:

                st.error(
                    f"Could not send email: {info}"
                )


        except Exception as error:

            st.error(
                f"Could not send email: {error}"
            )