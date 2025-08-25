# twilio_routes.py — voice & sms routes with chunked TTS and clean prompts
from __future__ import annotations
import os
import re
from flask import Blueprint, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse

from utils import logger, clean_user_facing_text, validate_twilio_request
from ai_client import get_ai_response

twilio_bp = Blueprint("twilio_bp", __name__)

VOICE_NAME = "Polly.Matthew-Neural"
LANG = os.getenv("TWILIO_LANG", "en-US")

@twilio_bp.route("/voice", methods=["POST"])
@validate_twilio_request
def twilio_voice():
    vr = VoiceResponse()
    session_id = request.values.get("CallSid", "voice_session")
    user_text  = (request.values.get("SpeechResult") or "").strip()

    # This is the main Gather object we will use to listen for the user's next response.
    gather = Gather(input="speech", language=LANG, speech_timeout="auto", action="/twilio/voice", method="POST")

    if not user_text:
        # This is the first turn of the call.
        gather.say("Nexza Auto. How can I help you today?", voice=VOICE_NAME)
    else:
        # This is a subsequent turn. Get the AI's response.
        try:
            reply, _ = get_ai_response(user_text, session_id)
            gather.say(reply, voice=VOICE_NAME)
        except Exception as e:
            logger.error("AI error in /voice route: %s", e)
            gather.say("Sorry, an application error has occurred. Please try again later.", voice=VOICE_NAME)

    # After either the initial prompt or the AI's reply, we append the Gather to the response.
    # This waits for the user to say something next.
    vr.append(gather)

    # We also add a redirect in case the user says nothing. This will loop the call back to this function.
    vr.redirect('/twilio/voice', method='POST')

    return Response(str(vr), mimetype="application/xml")