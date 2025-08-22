# ai_client.py — OpenAI client with simple language detect + retries
from __future__ import annotations

import os, time, re, logging
from typing import Tuple, List, Dict

try:
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    client = None

from .personas import DEALERSHIP_AGENT
from .utils import conversation_manager, logger

MAX_RETRIES = 3
RETRY_DELAY_S = 1.5

def detect_language(text: str | None) -> str:
    if not text: return "en"
    s = (text or "").lower()
    if re.search(r"\b(hola|gracias|por favor|cómo|necesito|cita|servicio|vehículo)\b", s): return "es"
    return "en"

def _system_prompt(lang: str) -> str:
    return DEALERSHIP_AGENT.get(lang, DEALERSHIP_AGENT["en"])["system_prompt"]

def _fallback(lang: str) -> str:
    return DEALERSHIP_AGENT.get(lang, DEALERSHIP_AGENT["en"])["fallback_response"]

def get_ai_response(user_input: str, session_id: str) -> Tuple[str, str]:
    lang = detect_language(user_input)
    system = _system_prompt(lang)
    conversation_manager.add_message(session_id, {"role":"user","content":user_input}, system_prompt=system)
    messages: List[Dict[str,str]] = conversation_manager.get_history(session_id)

    # If OpenAI client not available, return fallback but keep flow alive
    if client is None:
        logger.warning("OpenAI client unavailable; returning fallback.")
        return _fallback(lang), lang

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("AI_TEMPERATURE", "0.4"))
    max_tokens = int(os.getenv("AI_MAX_TOKENS", "256"))

    for attempt in range(1, MAX_RETRIES+1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            msg = resp.choices[0].message.content.strip()
            if msg:
                conversation_manager.add_message(session_id, {"role":"assistant","content":msg})
                return msg, lang
            logger.warning("Empty AI response on attempt %d", attempt)
        except Exception as e:
            logger.error("OpenAI error (attempt %d/%d): %s", attempt, MAX_RETRIES, e)
        if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY_S)
    return _fallback(lang), lang
