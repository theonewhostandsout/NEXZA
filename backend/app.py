# app.py  — NEXZA Flask backend (with Discord-compatible /api/discord)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os, hashlib, secrets
from datetime import datetime
from typing import Dict, Any

# ---- Your modules (unchanged) ----
from config import Config, logger
from filesystem_manager import FileSystemManager
from utils import (
    conversation_manager,
    file_index_manager,
    get_smart_response,
    organize_file,
    initialize_system,
    sanitize_user_input,
    validate_twilio_request,
)

# ---------------- Flask setup ----------------
app = Flask(__name__)
app.config.from_object(Config)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
app.config["JSON_SORT_KEYS"] = False
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(
    app,
    origins=["http://localhost:*", "http://127.0.0.1:*"],
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-ID", "X-API-Key"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    supports_credentials=True,
    max_age=3600,
)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

AI_BASE_DIR = "D:/NEXZA AI/"
fs_manager = FileSystemManager(base_dir=AI_BASE_DIR)

# Optional shared secret for bot requests (set this in your environment if you want it enforced)
DISCORD_SHARED_KEY = os.getenv("NEXZA_API_KEY", "").strip()

# --------------- Metrics ---------------
from backend.twilio_routes import twilio_bp
app.register_blueprint(twilio_bp)
class SystemMetrics:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.upload_count = 0
        self.chat_count = 0
        self.start_time = datetime.now()
        self.last_error = None
        self.active_sessions = set()

    def record_request(self):
        self.request_count += 1

    def record_error(self, error: str):
        self.error_count += 1
        self.last_error = {"message": str(error), "timestamp": datetime.now().isoformat()}

    def record_upload(self):
        self.upload_count += 1

    def record_chat(self, session_id: str):
        self.chat_count += 1
        self.active_sessions.add(session_id)

    def get_metrics(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "total_uploads": self.upload_count,
            "total_chats": self.chat_count,
            "active_sessions": len(self.active_sessions),
            "last_error": self.last_error,
            "error_rate": self.error_count / max(self.request_count, 1),
            "average_requests_per_minute": (self.request_count / max(uptime, 1)) * 60,
        }

metrics = SystemMetrics()

# --------------- Middleware / Errors ---------------
@app.before_request
def before_request_handler():
    metrics.record_request()
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    if request.method == "POST" and request.path != "/upload":
        if (request.content_type or "").split(";")[0].strip().lower() != "application/json":
            return jsonify({"error": "Content-Type must be application/json"}), 400
    request.request_id = secrets.token_hex(8)
    return None

@app.after_request
def after_request_handler(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Request-ID"] = getattr(request, "request_id", "unknown")
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'"
    )
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    metrics.record_error(str(e))
    if app.config.get("DEBUG"):
        return jsonify({"error": str(e), "type": type(e).__name__, "request_id": getattr(request, "request_id", "unknown")}), 500
    return jsonify({"error": "An internal error occurred", "request_id": getattr(request, "request_id", "unknown")}), 500

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    max_size_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
    return jsonify({"error": f"File too large. Maximum size is {max_size_mb}MB", "request_id": getattr(request, "request_id", "unknown")}), 413

@app.errorhandler(429)
def handle_rate_limit(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later.", "retry_after": e.description, "request_id": getattr(request, "request_id", "unknown")}), 429

# --------------- Health & Static ---------------
@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/health", methods=["GET"])
@limiter.exempt
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "2.0.0"}), 200

@app.route("/health/detailed", methods=["GET"])
@limiter.limit("10 per minute")
def detailed_health_check():
    try:
        fs_test = fs_manager.list_files("", include_dirs=False)
        fs_healthy = bool(fs_test)
        index_size = len(file_index_manager.get_all())
        system_metrics = metrics.get_metrics()
        return jsonify({
            "status": "healthy" if fs_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "filesystem": "healthy" if fs_healthy else "unhealthy",
                "file_index": f"{index_size} files indexed",
                "conversations": f"{len(conversation_manager._history)} active sessions",
            },
            "metrics": system_metrics,
        }), 200 if fs_healthy else 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route("/", methods=["GET"])
@limiter.exempt
def serve_index():
    try:
        return send_from_directory(".", "index.html")
    except FileNotFoundError:
        return jsonify({"error": "Frontend not found"}), 404

# --------------- Upload ---------------
@app.route("/upload", methods=["POST"])
@limiter.limit("30 per minute")
def upload_file_route():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Invalid filename"}), 400

        original_filename = file.filename
        filename = secure_filename(file.filename)
        file_content_bytes = file.read()

        if len(file_content_bytes) > app.config["MAX_CONTENT_LENGTH"]:
            return jsonify({"error": f"File too large. Maximum size is {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)}MB"}), 413

        try:
            file_content_decoded = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return jsonify({"error": "Binary files are not currently supported"}), 415

        file_content_decoded = sanitize_user_input(file_content_decoded, max_length=10 * 1024 * 1024)
        result = organize_file(filename, file_content_decoded, fs_manager)
        metrics.record_upload()

        if result.get("success"):
            return jsonify({
                "success": True,
                "message": "File uploaded successfully",
                "original_filename": original_filename,
                "final_path": result.get("final_path"),
                "analysis": result.get("analysis", {}),
                "warning": result.get("warning"),
            }), 200

        return jsonify({"error": result.get("error", "Upload failed")}), 500

    except Exception as e:
        logger.error(f"Error in file upload: {e}", exc_info=True)
        metrics.record_error(str(e))
        return jsonify({"error": "File upload failed"}), 500

# --------------- Web Chat (unchanged) ---------------
@app.route("/chat", methods=["POST"])
@limiter.limit("60 per minute")
def web_chat():
    try:
        data = request.get_json(force=True) or {}
        user_input = (data.get("message") or "").strip()
        session_id = (data.get("session_id") or "").strip()
        persona = data.get("persona", "NEXZA_ASSISTANT")

        if not session_id:
            session_id = f"web_{secrets.token_hex(8)}"
        else:
            session_id = sanitize_user_input(session_id, max_length=128)
            if not session_id or not session_id.replace("_", "").replace("-", "").isalnum():
                return jsonify({"error": "Invalid session ID"}), 400

        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        user_input = sanitize_user_input(user_input, max_length=2000)
        ai_response = get_smart_response(user_input, session_id, fs_manager, persona)
        metrics.record_chat(session_id)

        return jsonify({"response": ai_response, "session_id": session_id, "timestamp": datetime.now().isoformat()}), 200

    except Exception as e:
        logger.error(f"Error in web chat: {e}", exc_info=True)
        metrics.record_error(str(e))
        return jsonify({"error": "Chat service temporarily unavailable"}), 500

# --------------- Discord Bridge (fixed) ---------------
@app.route("/api/discord", methods=["POST"])
@limiter.limit("60 per minute")
def api_discord_chat():
    """Accepts both the bot payload and a simple test payload, returns what the bot expects."""
    try:
        # Optional shared secret
        if DISCORD_SHARED_KEY:
            if request.headers.get("X-API-Key", "") != DISCORD_SHARED_KEY:
                return jsonify({"ok": False, "error": "unauthorized"}), 401

        data = request.get_json(force=True) or {}

        # Accept either:
        #  A) From bot: {"type":"ask","prompt":"...","discord":{...}}
        #  B) From tools: {"message":"...","session_id":"...","persona":"..."}
        text = (data.get("prompt") or data.get("message") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "No message provided"}), 400

        session_id = (data.get("session_id") or f"discord_{secrets.token_hex(8)}").strip()
        persona = data.get("persona", "NEXZA_ASSISTANT")

        # Sanitize inputs
        session_id = sanitize_user_input(session_id, max_length=128)
        text = sanitize_user_input(text, max_length=2000)

        ai_response = get_smart_response(text, session_id, fs_manager, persona)
        metrics.record_chat(session_id)

        # Return shape the bot expects
        return jsonify({
            "ok": True,
            "reply": ai_response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }), 200

    except Exception as e:
        logger.error(f"Error in /api/discord: {e}", exc_info=True)
        metrics.record_error(str(e))
        return jsonify({"ok": False, "error": "Chat service temporarily unavailable"}), 500

# --------------- Startup ---------------
def initialize_application():
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting NEXZA AI Flask Backend Server v2.0")
        logger.info(f"Base directory: {AI_BASE_DIR}")
        logger.info(f"Debug mode: {Config.DEBUG}")
        logger.info(f"Max file size: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)}MB")
        logger.info("=" * 60)

        initialize_system(fs_manager)
        index_size = len(file_index_manager.get_all())
        logger.info(f"✅ File index loaded: {index_size} files")
        conversation_count = len(conversation_manager._history)
        logger.info(f"✅ Conversation history loaded: {conversation_count} sessions")
        logger.info("✅ System initialization complete")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        initialize_application()
        host, port = "0.0.0.0", 5000
        logger.info(f"Starting Flask server on {host}:{port}")
        app.run(host=host, port=port, debug=Config.DEBUG, threaded=True, use_reloader=Config.DEBUG)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        exit(1)
