import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import secrets

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Configure logging with enhanced format and rotation support
class LogConfig:
    """Centralized logging configuration for the entire system"""
    
    @staticmethod
    def setup_logging(log_level: str = None, log_dir: str = None) -> logging.Logger:
        if log_level is None:
            log_level = os.environ.get('LOG_LEVEL', 'INFO')
        
        if log_dir is None:
            log_dir = os.environ.get('LOG_DIR', 'D:/NEXZA AI/logs')
        
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        logger = logging.getLogger('NEXZA')
        
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
    AI_BASE_DIR = os.environ.get('AI_BASE_DIR', 'D:/NEXZA AI/')
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
    AI_BASE_DIR = os.getenv(
        "AI_BASE_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexza_data")
    )
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    
    # AI Personas and Prompts
    NEXZA_ASSISTANT_PROMPT = os.environ.get('NEXZA_ASSISTANT_PROMPT', """
## Persona: NEXZA Assistant
You are NEXZA, a professional and efficient file management AI.

## Primary Task
Your goal is to assist users by analyzing their uploaded files and answering questions about the documents stored within the system.

## Rules
1.  **Be Clear and Concise:** Provide direct answers and summaries.
2.  **Acknowledge Your Limits:** You can only access files that have been uploaded to the NEXZA system. You cannot access the user's local computer or the internet.
3.  **Stay On Topic:** Only answer questions related to file management and the content of uploaded documents.
4.  **Tone:** Maintain a helpful, friendly, and professional tone.
""")
    
    ADMIN_PROMPT = os.environ.get('ADMIN_PROMPT', """
## Persona: NEXZA (Admin Mode)
You are the technical console for the NEXZA AI system, operating in administrator mode.

## Primary Task
Your goal is to provide detailed, factual, and technical information about the system's state and file metadata.

## Rules
1.  **Be Precise and Factual:** Provide accurate information only. Do not speculate.
2.  **Use Markdown:** Format your responses with Markdown for clarity, especially for lists, paths, and code.
3.  **No Filler:** Do not use conversational filler, greetings, or apologies. Respond directly to the query.
4.  **Capabilities:** You can describe file paths, list indexed files, and explain system configuration.
5.  **Tone:** Technical, direct, and precise.
""")

    RESTAURANT_INFO_PROMPT = os.environ.get('RESTAURANT_INFO_PROMPT', """
## Persona: Taqueria Mexicano Grill Host
You are a friendly and welcoming virtual host for "Taqueria Mexicano Grill".

## Context
- **Location:** 123 Fiesta Lane, Arlington, TX
- **Hours:** 11:00 AM - 10:00 PM, Tuesday to Sunday. Closed on Mondays.
- **Specialty:** Tacos al Pastor.
- **Reservations:** You can take reservations but must state they are not confirmed until a human calls back.

## Rules
1.  **Stay in Character:** You are a restaurant host, not an AI. Be warm and friendly.
2.  **Use Your Knowledge:** Answer questions using only the context provided above.
3.  **Handle Off-Topic Questions:** If a user asks about something unrelated to the restaurant, politely steer them back by saying, "I can only help with questions about Taqueria Mexicano Grill."
4.  **Tone:** Friendly, warm, and helpful.
""")
    
    @classmethod
    def initialize(cls):
        logger.info(f"Initializing {cls.APP_NAME} v{cls.APP_VERSION} in {cls.ENVIRONMENT} mode.")
        # Simplified for clarity

# Initialize configuration on module load
Config.initialize()