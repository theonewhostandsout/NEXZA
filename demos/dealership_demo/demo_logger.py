import logging
import json
from logging.handlers import RotatingFileHandler
import os
import re

# --- Configuration ---
LOG_DIR = "demo_logs"
LOG_FILENAME = os.path.join(LOG_DIR, "twilio_demo.jsonl")
MAX_LOG_SIZE_MB = 10
MAX_LOG_FILES = 5

# --- Ensure log directory exists ---
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def mask_phone_number(phone_number: str) -> str:
    """Masks a phone number to only show the last 4 digits."""
    if not isinstance(phone_number, str):
        return "invalid_phone"
    # Use regex to find and keep only digits
    digits = re.sub(r'\D', '', phone_number)
    if len(digits) >= 4:
        return f"xxxxxx{digits[-4:]}"
    return "invalid_phone"

class JsonFormatter(logging.Formatter):
    """Formats log records into a JSON string."""
    def format(self, record):
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, 'extra_data'):
            log_object.update(record.extra_data)
        return json.dumps(log_object)

def setup_logger():
    """Sets up and returns a logger for the Twilio demo."""
    logger = logging.getLogger("TwilioDemoLogger")
    logger.setLevel(logging.INFO)
    logger.propagate = False # Avoid duplicate logs in root logger

    # Remove existing handlers to avoid duplication
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- File Handler ---
    # Use RotatingFileHandler for automatic log rotation
    handler = RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=MAX_LOG_FILES
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    return logger

# --- Global logger instance ---
demo_logger = setup_logger()

def log_api_call(from_number: str, to_number: str, user_input: str, ai_response: str, success: bool, error_message: str = None):
    """
    Logs a structured record for each API call.
    """
    extra_data = {
        "from_number_last4": mask_phone_number(from_number),
        "to_number_last4": mask_phone_number(to_number),
        "user_input": user_input,
        "ai_response": ai_response,
        "success": success,
        "error_message": error_message
    }
    demo_logger.info("API call processed", extra={'extra_data': extra_data})
