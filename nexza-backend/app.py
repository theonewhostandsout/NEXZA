from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import hashlib
import secrets

from config import Config, logger
from filesystem_manager import FileSystemManager

# Import enhanced utilities
from utils import (
    conversation_manager,
    file_index_manager,
    get_smart_response,
    organize_file,
    initialize_system,
    sanitize_user_input,
    validate_twilio_request
)

# Initialize Flask application with security configurations
app = Flask(__name__)
app.config.from_object(Config)

# Enhanced security configurations
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['JSON_SORT_KEYS'] = False
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure CORS with specific origins for security
CORS(app, 
     origins=["http://localhost:*", "http://127.0.0.1:*"],  # Add production origins as needed
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
     expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
     supports_credentials=True,
     max_age=3600)

# Initialize rate limiter for DDoS protection
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Initialize file system manager
AI_BASE_DIR = "D:/NEXZA AI/"
fs_manager = FileSystemManager(base_dir=AI_BASE_DIR)

# System metrics for monitoring
class SystemMetrics:
    """Track system performance and usage metrics"""
    
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
        self.last_error = {
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        }
    
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
            "average_requests_per_minute": (self.request_count / max(uptime, 1)) * 60
        }

metrics = SystemMetrics()

# Request validation middleware
@app.before_request
def before_request_handler():
    """Validate and log incoming requests"""
    metrics.record_request()
    
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    
    if request.method == 'POST':
        if request.path != '/upload' and request.content_type != 'application/json':
            logger.warning(f"Invalid content type: {request.content_type}")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    request.request_id = secrets.token_hex(8)
    
    return None

@app.after_request
def after_request_handler(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Request-ID'] = getattr(request, 'request_id', 'unknown')
    
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )
    
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler with logging"""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    metrics.record_error(str(e))
    
    if app.config.get('DEBUG'):
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
            'request_id': getattr(request, 'request_id', 'unknown')
        }), 500
    else:
        return jsonify({
            'error': 'An internal error occurred',
            'request_id': getattr(request, 'request_id', 'unknown')
        }), 500

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    """Handle file size limit exceeded"""
    max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    return jsonify({
        'error': f'File too large. Maximum size is {max_size_mb}MB',
        'request_id': getattr(request, 'request_id', 'unknown')
    }), 413

@app.errorhandler(429)
def handle_rate_limit(e):
    """Handle rate limit exceeded"""
    return jsonify({
        'error': 'Rate limit exceeded. Please try again later.',
        'retry_after': e.description,
        'request_id': getattr(request, 'request_id', 'unknown')
    }), 429

@app.route('/favicon.ico')
def favicon():
    return '', 204

# Health check endpoints
@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    }), 200

@app.route('/health/detailed', methods=['GET'])
@limiter.limit("10 per minute")
def detailed_health_check():
    """Detailed health check with system metrics"""
    try:
        fs_test = fs_manager.list_files("", include_dirs=False)
        fs_healthy = fs_test[0] if fs_test else False
        
        index_size = len(file_index_manager.get_all())
        
        system_metrics = metrics.get_metrics()
        
        return jsonify({
            'status': 'healthy' if fs_healthy else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'filesystem': 'healthy' if fs_healthy else 'unhealthy',
                'file_index': f'{index_size} files indexed',
                'conversations': f'{len(conversation_manager._history)} active sessions'
            },
            'metrics': system_metrics
        }), 200 if fs_healthy else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# Main application routes
@app.route('/')
@limiter.exempt
def serve_index():
    """Serve the main index page"""
    try:
        return send_from_directory('.', 'index.html')
    except FileNotFoundError:
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/upload', methods=['POST'])
@limiter.limit("30 per minute")
def upload_file_route():
    """Enhanced file upload with validation"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not file.filename or file.filename == '':
            return jsonify({'error': 'Invalid filename'}), 400
        
        original_filename = file.filename
        filename = secure_filename(file.filename)
        
        file_content_bytes = file.read()
        
        if len(file_content_bytes) > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({'error': f'File too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] / (1024*1024)}MB'}), 413
        
        file_hash = hashlib.sha256(file_content_bytes).hexdigest()
        
        try:
            file_content_decoded = file_content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({'error': 'Binary files are not currently supported'}), 415
        
        file_content_decoded = sanitize_user_input(file_content_decoded, max_length=10*1024*1024)
        
        result = organize_file(filename, file_content_decoded, fs_manager)
        
        metrics.record_upload()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'File uploaded successfully',
                'original_filename': original_filename,
                'final_path': result['final_path'],
                'analysis': result.get('analysis', {}),
                'warning': result.get('warning')
            }), 200
        else:
            return jsonify({'error': result.get('error', 'Upload failed')}), 500
            
    except Exception as e:
        logger.error(f"Error in file upload: {e}", exc_info=True)
        metrics.record_error(str(e))
        return jsonify({'error': 'File upload failed'}), 500

@app.route('/chat', methods=['POST'])
@limiter.limit("60 per minute")
def web_chat():
    """Enhanced chat endpoint with session management and persona support"""
    try:
        if not request.json:
            return jsonify({'error': 'Invalid request body'}), 400
        
        data = request.json
        user_input = data.get('message', '').strip()
        session_id = data.get('session_id', '')
        persona = data.get('persona', 'NEXZA_ASSISTANT')
        
        if not session_id:
            session_id = f"web_{secrets.token_hex(8)}"
        else:
            session_id = sanitize_user_input(session_id, max_length=128)
            if not session_id or not session_id.replace('_', '').replace('-', '').isalnum():
                return jsonify({'error': 'Invalid session ID'}), 400
        
        if not user_input:
            return jsonify({'error': 'No message provided'}), 400
        
        user_input = sanitize_user_input(user_input, max_length=2000)
        
        ai_response = get_smart_response(user_input, session_id, fs_manager, persona)
        
        metrics.record_chat(session_id)
        
        return jsonify({
            'response': ai_response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in chat: {e}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Error in web chat: {e}", exc_info=True)
        metrics.record_error(str(e))
        return jsonify({'error': 'Chat service temporarily unavailable'}), 500

# ... (Omitting other routes like /files/list, /files/search for brevity, they remain unchanged)

# Startup initialization
def initialize_application():
    """Initialize the application and all subsystems"""
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

# Application entry point
if __name__ == '__main__':
    try:
        initialize_application()
        
        host = '0.0.0.0'
        port = 5000
        
        if not Config.DEBUG:
            logger.warning("Running in production mode. Consider using a production WSGI server like Gunicorn.")
        
        logger.info(f"Starting Flask server on {host}:{port}")
        app.run(
            host=host,
            port=port,
            debug=Config.DEBUG,
            threaded=True,
            use_reloader=Config.DEBUG
        )
        
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        exit(1)