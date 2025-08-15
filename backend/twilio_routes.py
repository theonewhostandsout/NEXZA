from flask import Blueprint, request, Response
from .utils import clean_user_facing_text
from .ai_client import get_reply

twilio_bp = Blueprint('twilio', __name__)

@twilio_bp.route('/voice', methods=['POST'])
def twilio_voice():
    try:
        user_input = request.form.get('SpeechResult', '')
        from_ = request.form.get('From', '')
        response_text = clean_user_facing_text(get_reply(user_input, f"voice:{from_}", "PHONE_AGENT"))
        twiml = f"<Response><Say>{response_text}</Say></Response>"
        return Response(twiml, mimetype='text/xml')
    except Exception:
        fallback = "I'm having trouble connecting to the AI model. Please try again shortly."
        twiml = f"<Response><Say>{fallback}</Say></Response>"
        return Response(twiml, mimetype='text/xml')

@twilio_bp.route('/sms', methods=['POST'])
def twilio_sms():
    try:
        user_input = request.form.get('Body', '')
        from_ = request.form.get('From', '')
        response_text = clean_user_facing_text(get_reply(user_input, f"sms:{from_}", "PHONE_AGENT"))
        return Response(response_text, mimetype='text/plain')
    except Exception:
        fallback = "I'm having trouble connecting to the AI model. Please try again shortly."
        return Response(fallback, mimetype='text/plain')
