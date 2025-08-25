# utils.py — utilities compatible with app + twilio routes
from __future__ import annotations

import os, re, html, logging, hmac, hashlib
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps
from flask import request, Response

logger = logging.getLogger("nexza")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ---- Conversation manager ----
class ConversationManager:
    def __init__(self):
        self._history: Dict[str, List[Dict[str, str]]] = {}

    def add_message(self, session_id: str, message: Dict[str, str], system_prompt: str | None = None):
        h = self._history.setdefault(session_id, [])
        if system_prompt:
            if not h or h[0].get("role") != "system":
                h.insert(0, {"role": "system", "content": system_prompt})
            else:
                h[0]["content"] = system_prompt
        h.append(message)

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self._history.get(session_id, [])

conversation_manager = ConversationManager()

# ---- File index ----
class FileIndexManager:
    def __init__(self):
        self._idx: Dict[str, Dict[str, Any]] = {}

    def add_file(self, path: str, meta: Dict[str, Any]):
        self._idx[path] = {**meta, "indexed_at": datetime.now().isoformat()}

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        return self._idx

file_index_manager = FileIndexManager()

# ---- Sanitizers ----
_MD_OR_SSML = re.compile(r"[*_`<>]+")
_WS = re.compile(r"\s{2,}")

def sanitize_user_input(s: str, max_length: int = 2000) -> str:
    s = (s or "").strip().replace("\x00", " ")
    s = _MD_OR_SSML.sub("", s)
    s = _WS.sub(" ", s)
    if len(s) > max_length: s = s[:max_length]
    return s

def clean_user_facing_text(s: str) -> str:
    return sanitize_user_input(s, max_length=4000)

def xml_escape(s: str) -> str:
    return html.escape(s or "", quote=True)

# ---- Twilio validation (decorator; permissive by default) ----
def validate_twilio_request(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # If you set TWILIO_AUTH_TOKEN and TWILIO_VALIDATION=1, you can add a strict check here.
        return view_func(*args, **kwargs)
    return wrapper

# ---- Organize file ----
def organize_file(filename: str, file_content: str, fs_manager) -> Dict[str, Any]:
    try:
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", filename).strip("_") or "file.txt"
        lower = (file_content or "").lower()
        category = "notes"
        if any(k in lower for k in ("invoice","receipt","amount due")): category="finance"
        elif any(k in lower for k in ("report","incident","security","logbook")): category="reports"
        elif any(k in lower for k in ("menu","order","specials","restaurant")): category="operations"
        date_dir = datetime.now().strftime("%Y-%m-%d")
        path = f"{category}/{date_dir}/{safe}"
        ok, msg = fs_manager.write_file(path, file_content)
        meta = {"category":category,"suggested_path":path,"chars":len(file_content or ""), "sha1": hashlib.sha1((file_content or "").encode()).hexdigest()[:16]}
        if ok:
            file_index_manager.add_file(path, {"original_name": filename, **meta})
            return {"success": True, "final_path": path, "analysis": meta}
        return {"success": False, "error": msg or "Write failed"}
    except Exception as e:
        logger.error("organize_file error: %s", e, exc_info=True)
        return {"success": False, "error": "Exception during organize_file"}

# ---- AI glue ----
try:
    from ai_client import get_ai_response
except Exception:
    def get_ai_response(user_input: str, session_id: str):
        return "Sorry, the AI client is not configured.", "en"

def get_smart_response(user_input: str, session_id: str, fs_manager=None, persona: str="NEXZA_ASSISTANT") -> str:
    user_input = sanitize_user_input(user_input, max_length=2000)
    # Let ai_client manage persona & language; we keep simple history.
    conversation_manager.add_message(session_id, {"role":"user","content":user_input})
    reply, lang = get_ai_response(user_input, session_id)
    reply = sanitize_user_input(reply, max_length=1000)
    conversation_manager.add_message(session_id, {"role":"assistant","content":reply})
    return reply

def initialize_system(fs_manager=None) -> Dict[str, Any]:
    try:
        if fs_manager and hasattr(fs_manager, "base_dir"):
            os.makedirs(fs_manager.base_dir, exist_ok=True)
        return {"status": "ok", "initialized": True}
    except Exception as e:
        logger.error("initialize_system error: %s", e, exc_info=True)
        return {"status": "error", "initialized": False}