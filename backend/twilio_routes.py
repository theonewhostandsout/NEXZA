# backend/twilio_routes.py
from flask import Blueprint, request, Response, jsonify
import os

from .utils import xml_escape  # keep utils light; escape for TwiML safety
from .ai_client import get_ai_response, detect_language  # AI + lang detect

# Blueprint under /twilio/*
twilio_bp = Blueprint("twilio", __name__, url_prefix="/twilio")

# Feature flag (env)
def _demo_enabled() -> bool:
    return os.getenv("TWILIO_DEMO_ENABLED", "true").lower() == "true"


@twilio_bp.route("/status", methods=["GET"])
def status():
    """Health check for Twilio demo."""
    return jsonify({"status": "ok", "demo_enabled": _demo_enabled()}), 200


def _say_twiml(text: str, lang: str = "en-US") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="{lang}">{xml_escape(text)}</Say>
</Response>"""


def _msg_twiml(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{xml_escape(text)}</Message>
</Response>"""


@twilio_bp.route("/voice", methods=["POST"])
def voice():
    """Handle inbound voice calls."""
    if not _demo_enabled():
        return Response("Feature disabled", status=503)

    try:
        from_number = request.form.get("From", "unknown")
        to_number = request.form.get("To", "unknown")

        # Twilio may provide SpeechResult or TranscriptionText
        user_input = request.form.get("SpeechResult") or request.form.get("TranscriptionText") or ""
        session_id = f"voice:{from_number}:{to_number}"

        # Call AI (string response). Language for <Say> comes from user input.
        ai_text = get_ai_response(message=user_input, session_id=session_id, persona="DEALERSHIP_AGENT", channel="voice")

        lang_code = detect_language(user_input)
        lang = "es-MX" if lang_code == "es" else "en-US"

        return Response(_say_twiml(ai_text, lang=lang), mimetype="text/xml")

    except Exception:
        # Graceful fallback (keep wording generic; tests look for "trouble")
        fallback = "I'm having trouble connecting right now. Please call back later."
        return Response(_say_twiml(fallback, lang="en-US"), mimetype="text/xml")


@twilio_bp.route("/sms", methods=["POST"])
def sms():
    """Handle inbound SMS."""
    if not _demo_enabled():
        return Response("Feature disabled", status=503)

    try:
        from_number = request.form.get("From", "unknown")
        to_number = request.form.get("To", "unknown")
        body = (request.form.get("Body") or "").strip()
        session_id = f"sms:{from_number}:{to_number}"

        ai_text = get_ai_response(message=body, session_id=session_id, persona="DEALERSHIP_AGENT", channel="sms")
        return Response(_msg_twiml(ai_text), mimetype="text/xml")

    except Exception:
        fallback = "Sorry, I'm having trouble right now. Please call us and we’ll help you directly."
        return Response(_msg_twiml(fallback), mimetype="text/xml")