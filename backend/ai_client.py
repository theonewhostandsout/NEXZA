import os

def get_reply(message, session_id, persona="PHONE_AGENT"):
    """Generates a reply based on the message and persona."""
    if os.getenv("OPENAI_API_KEY"):
        # Stub for provider call
        return "OK"
    else:
        return "I'm having trouble connecting to the AI model. Please try again shortly."
