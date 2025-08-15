from flask import Blueprint, request, Response
from .utils import clean_user_facing_text

twilio_bp = Blueprint('twilio', __name__)

# Helper reply function (stub)
def reply(user_input=None):
    return f"Thanks for contacting NEXZA" + (f": {user_input}" if user_input else "")

@twilio_bp.route('/voice', methods=['POST'])
def twilio_voice():
    try:
        user_input = request.form.get('SpeechResult', '')
        response_text = clean_user_facing_text(reply(user_input))
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
        response_text = clean_user_facing_text(reply(user_input))
        return Response(response_text, mimetype='text/plain')
    except Exception:
        fallback = "I'm having trouble connecting to the AI model. Please try again shortly."
        return Response(fallback, mimetype='text/plain')
