# config.py — configuration + logging
from __future__ import annotations
import os, logging

try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass

# Logging
logger = logging.getLogger("nexza")
if not logger.handlers:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class Config:
    DEBUG = os.getenv("FLASK_ENV","development") != "production"
    SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24).hex()
