from flask import Blueprint, request, Response
from .utils import clean_user_facing_text
from .ai_client import get_reply
import html

twilio_bp = Blueprint("twilio", __name__)

def _xml_escape(s: str) -> str:
    return html.escape(s or "", quote=True)

@twilio_bp.route("/voice", methods=["POST"])
def twilio_voice():
    try:
        user_input = request.form.get("SpeechResult", "") or ""
        session_id = f"voice:{request.form.get('From','unknown')}"
        raw = get_reply(user_input, session_id, "PHONE_AGENT")
        response_text = clean_user_facing_text(raw)
        twiml = f"<Response><Say>{_xml_escape(response_text)}</Say></Response>"
        return Response(twiml, mimetype="text/xml")
    except Exception:
        fallback = "I'm having trouble connecting to the AI model. Please try again shortly."
        twiml = f"<Response><Say>{_xml_escape(fallback)}</Say></Response>"
        return Response(twiml, mimetype="text/xml")

@twilio_bp.route("/sms", methods=["POST"])
def twilio_sms():
    try:
        from_ = request.form.get("From", "unknown")
        body = request.form.get("Body", "") or ""
        session_id = f"sms:{from_}"
        raw = get_reply(body, session_id, "PHONE_AGENT")
        response_text = clean_user_facing_text(raw)
        twiml = f"<Response><Message>{_xml_escape(response_text)}</Message></Response>"
        return Response(twiml, mimetype="text/xml")
    except Exception:
        fallback = "I'm having trouble connecting to the AI model. Please try again shortly."
        twiml = f"<Response><Message>{_xml_escape(fallback)}</Message></Response>"
        return Response(twiml, mimetype="text/xml")
