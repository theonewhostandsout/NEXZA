# ai_client.py — OpenAI client with simple language detect + retries
from __future__ import annotations
import os
import time
import re
from typing import Tuple, List, Dict

try:
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    client = None

from personas import DEALERSHIP_AGENT
from utils import conversation_manager, logger

def detect_language(text: str | None) -> str:
    if not text: return "en"
    s = (text or "").lower()
    if re.search(r"\b(hola|gracias|cómo)\b", s): return "es"
    return "en"

def _system_prompt(lang: str) -> str:
    return DEALERSHIP_AGENT[lang]["system_prompt"]

def get_ai_response(user_input: str, session_id: str) -> Tuple[str, str]:
    lang = detect_language(user_input)
    system = _system_prompt(lang)
    conversation_manager.add_message(session_id, {"role":"user","content":user_input}, system_prompt=system)
    messages = conversation_manager.get_history(session_id)

    if client is None:
        logger.warning("OpenAI client not configured.")
        return "The AI service is not available.", lang

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.5, max_tokens=200)
        msg = resp.choices[0].message.content.strip()
        if msg:
            conversation_manager.add_message(session_id, {"role":"assistant","content":msg})
            return msg, lang
    except Exception as e:
        logger.error("OpenAI API error: %s", e, exc_info=True)
        # Fallback response in case of API error
        return "I'm sorry, I'm having trouble connecting to the AI service right now.", lang
    
    return "I'm not sure how to respond to that.", lang