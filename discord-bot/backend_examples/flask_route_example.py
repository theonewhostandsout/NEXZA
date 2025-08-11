# Drop this into your Flask app to handle Discord bot requests.
from flask import Blueprint, request, jsonify, current_app

discord_bp = Blueprint("discord_bp", __name__)

def verify_api_key(req):
    shared = current_app.config.get("NEXZA_API_KEY", "")
    return shared and req.headers.get("X-API-Key") == shared

@discord_bp.post("/api/discord")
def discord_router():
    if not verify_api_key(request):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    payload = request.get_json(force=True, silent=True) or {}
    typ = payload.get("type")
    meta = payload.get("discord", {})

    try:
        if typ == "ask":
            prompt = payload.get("prompt", "")
            # TODO: Call your local model / tools / RAG
            reply = f"[demo] You asked: {prompt}"
            return jsonify({"ok": True, "reply": reply})

        if typ == "note":
            # TODO: persist note
            return jsonify({"ok": True})

        if typ == "assign":
            # TODO: persist task assignment, DM assignee, etc.
            assignee = meta.get("assignee")
            task = payload.get("task", "")
            return jsonify({"ok": True, "reply": f"Task for {assignee}: {task}"})

        if typ == "summary":
            limit = int(payload.get("limit", 50))
            # TODO: pull last N messages from your own store and summarize via model
            return jsonify({"ok": True, "reply": f"[demo] Summary of last {limit} messages."})

        return jsonify({"ok": False, "error": "unknown type"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500