# new-agent/config.py
"""Global configuration loaded from environment / .env file."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- LLM ---
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# --- Embedding ---
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", LLM_API_BASE)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", LLM_API_KEY)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
SUBJECTS_DIR = DATA_DIR / "subjects"
STUDENTS_DIR = DATA_DIR / "students"

# --- Context / History ---
MAX_HISTORY_TOKENS = int(os.getenv("MAX_HISTORY_TOKENS", "8000"))
COMPRESSION_THRESHOLD = int(os.getenv("COMPRESSION_THRESHOLD", "10"))

# --- Chunking ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
RETRIEVAL_TOP_K = 5

# --- Server ---
API_HOST = "127.0.0.1"
API_PORT = 8080

# Ensure data directories exist
SUBJECTS_DIR.mkdir(parents=True, exist_ok=True)
STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
