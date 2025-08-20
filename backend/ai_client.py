import os
import openai
import time
from typing import Tuple

from .personas import DEALERSHIP_AGENT
from .utils import conversation_manager, logger

# --- Configuration ---
MAX_RETRIES = 3
RETRY_DELAY_S = 2
LANGUAGE_DETECT_THRESHOLD = 0.5  # Confidence threshold for language detection

# --- OpenAI Client ---
# It's recommended to initialize the client once
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def detect_language(text: str) -> str:
    """
    Detects the language of a given text.
    Returns 'es' for Spanish, 'en' for English.
    This is a simple implementation, a more robust solution would use a dedicated library.
    """
    if not text or not isinstance(text, str):
        return 'en'

    # Simple keyword-based detection
    spanish_keywords = ['hola', 'gracias', 'adiós', 'por favor', 'coche', 'auto']
    text_lower = text.lower()

    if any(keyword in text_lower for keyword in spanish_keywords):
        return 'es'

    # A more advanced method could be used here, e.g., a compact language detection model
    # For now, we default to English
    return 'en'


def get_ai_response(user_input: str, session_id: str) -> Tuple[str, str]:
    """
    Gets an AI response from OpenAI, with retries and error handling.

    Args:
        user_input: The text from the user.
        session_id: A unique identifier for the conversation session.

    Returns:
        A tuple containing the AI's response text and the detected language ('en' or 'es').
    """
    lang = detect_language(user_input)
    persona = DEALERSHIP_AGENT[lang]

    conversation_manager.add_message(
        session_id,
        {"role": "user", "content": user_input},
        system_prompt=persona["system_prompt"]
    )

    messages = conversation_manager.get_history(session_id)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # or another suitable model
                messages=messages,
                temperature=0.7,
                max_tokens=150,
            )

            ai_response = response.choices[0].message.content.strip()

            if ai_response:
                conversation_manager.add_message(session_id, {"role": "assistant", "content": ai_response})
                return ai_response, lang

            logger.warning(f"AI returned an empty response. Attempt {attempt + 1}/{MAX_RETRIES}")

        except openai.APIError as e:
            logger.error(f"OpenAI API error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_ai_response on attempt {attempt + 1}/{MAX_RETRIES}: {e}")

        # Wait before retrying
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_S)

    # If all retries fail, return the fallback response
    logger.error(f"All {MAX_RETRIES} retries failed for session {session_id}. Returning fallback.")
    return persona["fallback_response"], lang
