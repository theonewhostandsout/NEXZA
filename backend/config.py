import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import secrets

# Define project root, which is the parent directory of this file's location (backend/ -> root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from .env file located in the project root
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Centralized AI Base Directory definition
# This is the single source of truth for the data directory.
# It defaults to `nexza_data` in the project root if not set via environment variable.
AI_BASE_DIR = os.getenv("AI_BASE_DIR") or os.path.join(PROJECT_ROOT, "nexza_data")
os.makedirs(AI_BASE_DIR, exist_ok=True)

# Configure logging with enhanced format and rotation support
class LogConfig:
    """Centralized logging configuration for the entire system"""

    @staticmethod
    def setup_logging(log_level: str = None, log_dir: str = None) -> logging.Logger:
        if log_level is None:
            log_level = os.environ.get('LOG_LEVEL', 'INFO')

        # Logs are now stored inside the AI_BASE_DIR
        if log_dir is None:
            log_dir = os.environ.get('LOG_DIR', os.path.join(AI_BASE_DIR, 'logs'))

        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        logger = logging.getLogger('NEXZA')

        # Only add file handler if one is not already present to avoid duplicate logs
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            try:
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    os.path.join(log_dir, 'nexza.log'),
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5,
                    encoding='utf-8'
                )
            except ImportError:
                file_handler = logging.FileHandler(
                    os.path.join(log_dir, 'nexza.log'),
                    encoding='utf-8'
                )

            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
            ))
            logger.addHandler(file_handler)

        return logger

# Initialize logger
logger = LogConfig.setup_logging()

class Config:
    """Enhanced configuration class for the NEXZA AI system."""

    # Environment configuration
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()
    IS_PRODUCTION = ENVIRONMENT == 'production'

    # Basic application settings
    APP_NAME = os.environ.get('APP_NAME', 'NEXZA AI')
    APP_VERSION = os.environ.get('APP_VERSION', '2.0.0')
    SECRET_KEY = os.environ.get('SECRET_KEY', None)

    if not SECRET_KEY:
        if IS_PRODUCTION:
            raise ValueError("SECRET_KEY must be set in production environment")
        else:
            SECRET_KEY = secrets.token_hex(32)
            logger.warning("Using generated SECRET_KEY - set SECRET_KEY environment variable for production")

    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't') and not IS_PRODUCTION

    # Server configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))

    # File system configuration
    # Use the centralized AI_BASE_DIR defined at the top of the file
    AI_BASE_DIR = AI_BASE_DIR
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE_MB', 10)) * 1024 * 1024

    # AI/LLM configuration
    LM_STUDIO_URL = os.environ.get('LM_STUDIO_URL', "http://localhost:1234/v1/chat/completions")
    DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', "local-model")
    AI_TEMPERATURE = float(os.environ.get('AI_TEMPERATURE', 0.7))
    AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', 800))

    # Rate limiting configuration
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() in ('true', '1', 't')

    # Twilio configuration (optional)
    TWILIO_ENABLED = os.environ.get('TWILIO_ENABLED', 'False').lower() in ('true', '1', 't')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)

    # AI Personas and Prompts
    NEXZA_ASSISTANT_PROMPT = os.environ.get('NEXZA_ASSISTANT_PROMPT', """
## Persona: NEXZA Assistant
You are NEXZA, a professional and efficient file management AI. Your goal is to assist users by analyzing their uploaded files and answering questions about the documents. Be clear, concise, and stay on topic. You can only access uploaded files. Maintain a helpful, friendly, and professional tone.
""")

    ADMIN_PROMPT = os.environ.get('ADMIN_PROMPT', """
## Persona: NEXZA (Admin Mode)
You are the technical console for the NEXZA AI system. Provide detailed, factual, and technical information about the system's state and file metadata. Use Markdown for clarity. Do not use conversational filler. Be precise and direct.
""")

    PHONE_AGENT_PROMPT = os.environ.get('PHONE_AGENT_PROMPT', """
## Persona: NEXZA Phone Agent
You are a friendly and helpful assistant speaking over the phone. Your tone should be conversational, warm, and clear. Avoid jargon. Keep your answers relatively short and easy to understand.
""")

    DISCORD_HELPER_PROMPT = os.environ.get('DISCORD_HELPER_PROMPT', """
## Persona: NEXZA Discord Helper
You are a bot in a Discord server. Be concise and direct. Use Markdown formatting where it helps, such as for lists or code blocks. Get straight to the point.
""")

    RESTAURANT_INFO_PROMPT = os.environ.get('RESTAURANT_INFO_PROMPT', """
## Persona: Taqueria Mexicano Grill Host
You are a friendly and welcoming virtual host for "Taqueria Mexicano Grill".
- **Location:** 123 Fiesta Lane, Arlington, TX
- **Hours:** 11:00 AM - 10:00 PM, Tuesday to Sunday. Closed on Mondays.
- **Specialty:** Tacos al Pastor.
- **Reservations:** You can take reservations but must state they are not confirmed until a human calls back.
Stay in character. If a user asks about something unrelated, politely steer them back to the restaurant.
""")

    @classmethod
    def initialize(cls):
        logger.info(f"Initializing {cls.APP_NAME} v{cls.APP_VERSION} in {cls.ENVIRONMENT} mode.")
        # Simplified for clarity

# Initialize configuration on module load
Config.initialize()
