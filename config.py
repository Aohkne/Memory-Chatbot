import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
CHAT_MODEL = os.environ.get("CHAT_MODEL")
BASE_URL = os.environ.get("BASE_URL") or None

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
STATE_PATH = DATA_DIR / "state.json"
INDEX_PATH = MEMORY_DIR / "MEMORY.md"
LOCK_PATH = MEMORY_DIR / ".consolidation.lock"

AUTODREAM_MIN_HOURS = 24
AUTODREAM_MIN_SESSIONS = 5
LOCK_STALE_MINUTES = 10
