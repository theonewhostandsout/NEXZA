import os

def get_reply(message: str, session_id: str, persona: str = "PHONE_AGENT") -> str:
    """
    Returns a reply for Twilio voice/SMS.
    If OPENAI_API_KEY is set, pretend to call a provider (stub returns 'OK').
    Otherwise, return a helpful fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # TODO: replace stub with real provider call
        return "OK"
    base = "Thanks for contacting NEXZA"
    return f"{base}: {message}" if message else base
