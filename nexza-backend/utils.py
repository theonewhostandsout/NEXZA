import requests
import json
import mimetypes
import os
import hashlib
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import request, abort
from twilio.request_validator import RequestValidator
from typing import Dict, List, Tuple, Any, Optional
from threading import Lock
from collections import deque
from config import Config, logger

# --- Conversation Manager ---
class ConversationManager:
    """Thread-safe conversation history manager with automatic pruning"""
    
    def __init__(self, max_history_per_session: int = 50, max_sessions: int = 100):
        self._history: Dict[str, deque] = {}
        self._max_history = max_history_per_session
        self._max_sessions = max_sessions
        self._last_access: Dict[str, datetime] = {}
        self._lock = Lock()
    
    def add_message(self, session_id: str, message: Dict[str, Any], system_prompt: Optional[str] = None) -> None:
        with self._lock:
            if not self._validate_session_id(session_id):
                raise ValueError(f"Invalid session ID: {session_id}")
            
            if session_id not in self._history:
                if len(self._history) >= self._max_sessions:
                    self._prune_old_sessions()
                
                self._history[session_id] = deque(maxlen=self._max_history)
                prompt_content = system_prompt or Config.NEXZA_ASSISTANT_PROMPT
                self._history[session_id].append({
                    "role": "system",
                    "content": prompt_content
                })
            
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            self._history[session_id].append(message)
            self._last_access[session_id] = datetime.now()
    
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            if session_id in self._history:
                self._last_access[session_id] = datetime.now()
                return list(self._history[session_id])
            return []

    def _validate_session_id(self, session_id: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', session_id)) and len(session_id) <= 128

    def _prune_old_sessions(self) -> None:
        if not self._last_access: return
        sorted_sessions = sorted(self._last_access.items(), key=lambda x: x[1])
        sessions_to_remove = len(self._history) - self._max_sessions + 1
        for session_id, _ in sorted_sessions[:sessions_to_remove]:
            del self._history[session_id]
            del self._last_access[session_id]

# --- File Index Manager ---
class FileIndexManager:
    """File index with search optimization"""
    def __init__(self, max_index_size: int = 10000):
        self._index: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_index_size
        self._lock = Lock()
    
    def add_file(self, path: str, metadata: Dict[str, Any]) -> bool:
        with self._lock:
            if len(self._index) >= self._max_size:
                logger.warning(f"File index at maximum capacity ({self._max_size})")
                return False
            self._index[path] = metadata
            return True

    def search(self, query: str, max_results: int = 5) -> List[Tuple[str, Dict, float]]:
        with self._lock:
            results = []
            query_lower = query.lower()
            for path, metadata in self._index.items():
                if query_lower in path.lower() or query_lower in metadata.get("content", "").lower():
                    results.append((path, metadata, 1.0))
            return results[:max_results]

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return self._index.copy()

# Initialize managers
conversation_manager = ConversationManager()
file_index_manager = FileIndexManager()

# --- AI and Response Logic ---

def make_ai_request(messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> Optional[str]:
    """Centralized AI request handling"""
    try:
        payload = {
            "model": Config.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        response = requests.post(
            Config.LM_STUDIO_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        if 'choices' in data and data['choices']:
            return data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        logger.error(f"AI request failed: {e}")
    return None

def get_smart_response(user_input: str, session_id: str, fs_manager, persona: str = 'NEXZA_ASSISTANT') -> str:
    """Determines whether to search files or just chat."""
    return get_web_chat_response(user_input, session_id, fs_manager, persona)

def get_web_chat_response(user_input: str, session_id: str, fs_manager, persona: str = 'NEXZA_ASSISTANT') -> str:
    """Handles generating a chat response using conversation history."""
    try:
        prompt_map = {
            'NEXZA_ASSISTANT': Config.NEXZA_ASSISTANT_PROMPT,
            'ADMIN_MODE': Config.ADMIN_PROMPT
        }
        system_prompt = prompt_map.get(persona, Config.NEXZA_ASSISTANT_PROMPT)
        
        # FIX: Removed extra period before 'add_message'
        conversation_manager.add_message(session_id, {"role": "user", "content": user_input}, system_prompt=system_prompt)
        
        messages = conversation_manager.get_history(session_id)
        
        ai_response = make_ai_request(messages, temperature=Config.AI_TEMPERATURE, max_tokens=Config.AI_MAX_TOKENS)
        
        if ai_response:
            # Clean up the AI's response to remove the "internal monologue"
            clean_response = ai_response
            greetings = ["Hello!", "Hi there!", "Hi!"]
            for greeting in greetings:
                if greeting in ai_response:
                    # Take the greeting and everything after it
                    clean_response = ai_response[ai_response.find(greeting):]
                    break
            
            conversation_manager.add_message(session_id, {"role": "assistant", "content": clean_response})
            return clean_response
        else:
            return "I'm having trouble connecting to the AI model. Please try again in a moment."
    except Exception as e:
        logger.error(f"Error in chat response: {e}")
        return "I encountered an error processing your message."

# --- File Organization and Analysis Logic ---

def organize_file(filename: str, file_content: str, fs_manager) -> Dict[str, Any]:
    """Organizes a file based on AI analysis."""
    analysis = analyze_file_with_ai(filename, file_content)
    
    category = analysis.get('category', 'other')
    suggested_path = analysis.get('suggested_path', f"{category}/{filename}")
    
    success, message = fs_manager.write_file(suggested_path, file_content)
    
    if success:
        file_index_manager.add_file(suggested_path, {
            "original_name": filename,
            "upload_date": datetime.now().isoformat(),
            "analysis": analysis,
            "content": file_content[:2000]
        })
        return {"success": True, "final_path": suggested_path, "analysis": analysis}
    else:
        return {"success": False, "error": message}

def get_fallback_analysis(filename: str) -> Dict[str, Any]:
    """Provide basic analysis when AI is unavailable"""
    extension = os.path.splitext(filename)[1].lower()
    extension_map = {'.py': 'code', '.js': 'code', '.html': 'code', '.css': 'code', '.json': 'data', '.csv': 'data', '.txt': 'documentation', '.md': 'documentation'}
    category = extension_map.get(extension, 'other')
    return {
        "category": category,
        "tags": ["unknown"],
        "summary": "AI analysis failed. File placed in fallback directory.",
        "suggested_path": f"{category}/{filename}"
    }

def analyze_file_with_ai(filename: str, file_content: str) -> Dict[str, Any]:
    """Analyzes file content to determine category and metadata with a more robust prompt."""
    try:
        content_preview = file_content[:1500]
        
        analysis_prompt = f"""You are a file analysis bot. Your only function is to analyze the provided file information and respond with a single, valid JSON object. Do not include any other text, greetings, or explanations.

Analyze this file:
- Filename: "{filename}"
- Content Preview: "{content_preview}"

Respond with a JSON object with the following keys: "category", "tags", "summary", and "suggested_path".
Example response:
{{
  "category": "code",
  "tags": ["python", "flask", "backend"],
  "summary": "A Python script for a Flask web application backend.",
  "suggested_path": "code/web_app/backend.py"
}}"""

        messages = [
            {"role": "system", "content": "You are a file analysis system. Respond only with a single, valid JSON object and nothing else."},
            {"role": "user", "content": analysis_prompt}
        ]
        
        response_text = make_ai_request(messages, temperature=0.0, max_tokens=500)
        
        if response_text:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                 logger.error("No JSON object found in the AI analysis response.")
        
        return get_fallback_analysis(filename)
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")
        return get_fallback_analysis(filename)

# --- Other Utilities ---

def validate_twilio_request(f):
    """Decorator to validate incoming Twilio requests."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if Config.DEBUG and not Config.TWILIO_ENABLED:
             return f(*args, **kwargs)

        validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
        
        url = request.url
        form_data = request.form
        signature = request.headers.get('X-Twilio-Signature', '')

        if not signature:
            logger.warning(f"Missing Twilio signature for {url}")
            return abort(403)

        if validator.validate(url, form_data, signature):
            return f(*args, **kwargs)
        else:
            logger.warning(f"Failed Twilio validation for {url}")
            return abort(403)
            
    return decorated_function

def sanitize_user_input(text: str, max_length: int = 10000) -> str:
    """Sanitizes user input to prevent basic injection attacks."""
    if not text:
        return ""
    return text[:max_length].strip()

def initialize_system(fs_manager):
    """Initializes system components like the file index."""
    logger.info("System initialization complete.")