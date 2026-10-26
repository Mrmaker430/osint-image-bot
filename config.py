"""Environment configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required")

# --- Method 2: face search ---
FACECHECK_API_KEY = os.getenv("FACECHECK_API_KEY", "")
PIMEYES_API_KEY = os.getenv("PIMEYES_API_KEY", "")

# --- Method 3: reverse search ---
SAUCENAO_KEY = os.getenv("SAUCENAO_KEY", "")

# --- Limits ---
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))
FACE_SEARCH_COOLDOWN = int(os.getenv("FACE_SEARCH_COOLDOWN", "60"))
FACE_SEARCH_TIMEOUT = int(os.getenv("FACE_SEARCH_TIMEOUT", "90"))
