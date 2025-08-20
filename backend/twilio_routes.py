from flask import Blueprint, request, Response, jsonify
from os import getenv

from .utils import validate_twilio_request, xml_escape, clean_user_facing_text, logger
from .ai_client import get_ai_response
from .demo_logger import log_api_call
from .personas import DEALERSHIP_AGENT

twilio_bp = Blueprint("twilio", __name__)

@twilio_bp.route("/status", methods=["GET"])
def twilio_status():
    """Health check endpoint for the Twilio demo."""
    return jsonify({"status": "ok", "message": "Twilio demo is running"}), 200

@twilio_bp.route("/voice", methods=["POST"])
@validate_twilio_request
def twilio_voice():
    """Handles incoming voice calls from Twilio."""
    if not getenv("TWILIO_DEMO_ENABLED") == "true":
        return Response("<Response><Say>This feature is not enabled.</Say></Response>", mimetype="text/xml")

    from_number = request.form.get("From", "unknown")
    to_number = request.form.get("To", "unknown")

    # Twilio can send transcription in either SpeechResult or TranscriptionText
    user_input = request.form.get("SpeechResult", "") or request.form.get("TranscriptionText", "")
    session_id = f"voice:{from_number}"

    ai_response, lang = get_ai_response(user_input, session_id)

    # Clean up response for TTS
    response_text = clean_user_facing_text(ai_response)

    # Set voice based on language
    voice = "es-MX" if lang == "es" else "en-US"

    log_api_call(
        from_number=from_number,
        to_number=to_number,
        user_input=user_input,
        ai_response=response_text,
        success=True
    )

    twiml = f'<Response><Say voice="{voice}">{xml_escape(response_text)}</Say></Response>'
    return Response(twiml, mimetype="text/xml")

@twilio_bp.route("/sms", methods=["POST"])
@validate_twilio_request
def twilio_sms():
    """Handles incoming SMS messages from Twilio."""
    if not getenv("TWILIO_DEMO_ENABLED") == "true":
        return Response("<Response><Message>This feature is not enabled.</Message></Response>", mimetype="text/xml")

    from_number = request.form.get("From", "unknown")
    to_number = request.form.get("To", "unknown")
    user_input = request.form.get("Body", "")
    session_id = f"sms:{from_number}"

    ai_response, _ = get_ai_response(user_input, session_id)

    # Clean up response for SMS
    response_text = clean_user_facing_text(ai_response)

    log_api_call(
        from_number=from_number,
        to_number=to_number,
        user_input=user_input,
        ai_response=response_text,
        success=True
    )

    twiml = f'<Response><Message>{xml_escape(response_text)}</Message></Response>'
    return Response(twiml, mimetype="text/xml")

@twilio_bp.errorhandler(Exception)
def handle_error(e):
    """Generic error handler for Twilio routes."""
    logger.error(f"An unhandled exception occurred: {e}", exc_info=True)

    from_number = request.form.get("From", "unknown")
    to_number = request.form.get("To", "unknown")

    log_api_call(
        from_number=from_number,
        to_number=to_number,
        user_input=request.form.get("Body") or request.form.get("SpeechResult"),
        ai_response="",
        success=False,
        error_message=str(e)
    )

    # Determine if it's a voice or SMS request to provide the correct TwiML response
    if "voice" in request.path:
        fallback_response = DEALERSHIP_AGENT['en']['fallback_response']
        twiml = f'<Response><Say>{xml_escape(fallback_response)}</Say></Response>'
    else:
        fallback_response = DEALERSHIP_AGENT['en']['fallback_response']
        twiml = f'<Response><Message>{xml_escape(fallback_response)}</Message></Response>'

    return Response(twiml, mimetype="text/xml")
