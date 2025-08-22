# twilio_routes.py — voice & sms routes with chunked TTS and clean prompts
from __future__ import annotations

import os, re
from flask import Blueprint, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse

from .utils import logger, clean_user_facing_text, validate_twilio_request, xml_escape
from .ai_client import get_ai_response

twilio_bp = Blueprint("twilio_bp", __name__)

VOICE_NAME = os.getenv("TWILIO_VOICE", "Polly.Joanna")
LANG       = os.getenv("TWILIO_LANG",  "en-US")
MAX_SAY_CHARS = 1400

def _chunk_text(s: str, max_len: int = MAX_SAY_CHARS):
    s = clean_user_facing_text(s)
    parts, buf, total = [], [], 0
    for tok in re.split(r"(\. |\? |! |\n)", s):
        if not tok: continue
        if total + len(tok) > max_len and buf:
            parts.append("".join(buf).strip()); buf, total = [tok], len(tok)
        else:
            buf.append(tok); total += len(tok)
    if buf: parts.append("".join(buf).strip())
    return [p for p in parts if p]

def say_clean(vr_or_gather, text: str):
    text = text or ""
    identity = re.compile(r"^\s*(hi|hello|hey)\b.*$|^\s*i\s*(am|'m)\b.*$", re.I)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not identity.match(ln)]
    text  = " ".join(lines) or text
    for part in _chunk_text(text):
        vr_or_gather.say(part, voice=VOICE_NAME, language=LANG)

@twilio_bp.route("/status", methods=["GET"])
def twilio_status():
    return {"status":"ok", "service":"twilio", "ip": request.remote_addr}

@twilio_bp.route("/voice", methods=["POST"])
@validate_twilio_request
def twilio_voice():
    vr = VoiceResponse()
    session_id = request.values.get("CallSid", "voice_session")
    user_text  = (request.values.get("SpeechResult") or "").strip()

    # First hit or no speech -> prompt
    if not user_text:
        g = Gather(
            input="speech",
            language=LANG,
            speech_timeout="auto",
            action="/twilio/voice",
            method="POST",
            action_on_empty_result=True,
        )
        say_clean(g, "Nexza Auto. How can I help you today? You can say schedule service, check inventory, or speak with sales.")
        vr.append(g)
        vr.redirect("/twilio/voice")
        return Response(str(vr), mimetype="application/xml")

    try:
        reply, lang = get_ai_response(user_text, session_id)
        if not reply:
            reply = "Got it. What can I help you with for your vehicle today?"
    except Exception as e:
        logger.exception("AI error: %s", e)
        reply = "I had a problem getting that. Could you please repeat or try a simpler request?"

    say_clean(vr, reply)
    g = Gather(
        input="speech",
        language=LANG,
        speech_timeout="auto",
        action="/twilio/voice",
        method="POST",
        action_on_empty_result=True,
    )
    say_clean(g, "Anything else?")
    vr.append(g)
    vr.redirect("/twilio/voice")
    return Response(str(vr), mimetype="application/xml")

@twilio_bp.route("/sms", methods=["POST"])
@validate_twilio_request
def twilio_sms():
    user_text  = request.values.get("Body", "") or ""
    session_id = request.values.get("From", "sms_session")
    try:
        reply, _ = get_ai_response(user_text, session_id)
    except Exception as e:
        logger.exception("AI error: %s", e)
        reply = "Sorry—something went wrong. Please try again."
    mr = MessagingResponse()
    mr.message(clean_user_facing_text(reply))
    return Response(str(mr), mimetype="application/xml")
