# backend/ai_client.py
"""OpenAI client for generating AI responses for Twilio Voice/SMS."""

import os
import time
from typing import List, Dict

from openai import OpenAI
from .personas import PERSONAS

# ---- OpenAI client (lazy init) ------------------------------------------------

_client = None


def _init_client():
    global _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # We'll still allow the module to load; callers will hit fallback text.
        return
    _client = OpenAI(api_key=api_key)

# ---- Simple language detection ------------------------------------------------


def detect_language(text: str) -> str:
    """
    Very lightweight detector. Returns 'es' for Spanish, 'en' otherwise.
    """
    if not isinstance(text, str) or not text:
        return "en"
    text_lower = text.lower()
    spanish_indicators = [
        "hola",
        "gracias",
        "adiós",
        "por favor",
        "carro",
        "coche",
        "auto",
        "camioneta",
        "cuánto",
        "necesito",
        "quiero",
    ]
    hits = sum(1 for w in spanish_indicators if w in text_lower)
    return "es" if hits >= 2 else "en"

# ---- Public API ---------------------------------------------------------------


def get_ai_response(
    message: str,
    session_id: str,
    persona: str = "DEALERSHIP_AGENT",
    channel: str = "voice",
) -> str:
    """
    Generate an AI response using the configured persona.
    Falls back to a friendly static message if API isn't available.

    Args:
        message: user input text
        session_id: conversation/session identifier (used for future threading)
        persona: key in PERSONAS (default: DEALERSHIP_AGENT)
        channel: 'voice' or 'sms' (affects length/fallback)
    """
    # Persona config
    cfg = PERSONAS.get(persona, PERSONAS.get("DEFAULT", {}))
    system_prompt = cfg.get("system_prompt", "You are a helpful assistant.")
    temperature = cfg.get("temperature", 0.7)
    model = cfg.get("model", "gpt-4o-mini")
    max_tokens = cfg.get("max_tokens_voice" if channel == "voice" else "max_tokens_sms", 150)

    # Build messages
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for ex in cfg.get("examples", []):
        messages.append(ex)
    messages.append({"role": "user", "content": message})

    # Try calling OpenAI
    global _client
    if _client is None:
        _init_client()

    if _client is None:
        return _fallback_text(channel)

    # Retry with exponential backoff
    retries = 3
    for attempt in range(retries):
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=0.1,
                frequency_penalty=0.1,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            break

    # Final fallback on failure
    return _fallback_text(channel)


def _fallback_text(channel: str) -> str:
    if channel == "voice":
        return (
            "I'm having trouble connecting to our assistant right now. "
            "Please leave your name and number, or try again shortly."
        )
    return "Sorry, I'm having trouble right now. Please call us and we’ll help you directly."