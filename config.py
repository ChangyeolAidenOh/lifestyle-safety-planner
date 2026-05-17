"""Central configuration for Lifestyle Safety Planner."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"

# Database
USE_CSV_FALLBACK = os.getenv("USE_CSV_FALLBACK", "true").lower() == "true"
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5434")),
    "dbname": os.getenv("POSTGRES_DB", "safety_planner"),
    "user": os.getenv("POSTGRES_USER", "sp_admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "sp_secret"),
}

# LLM
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")  # ollama | anthropic
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Public Data API Keys
DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
AIRKOREA_API_KEY = os.getenv("AIRKOREA_API_KEY", "")

# Safety scoring weights (time-weighted average)
LOCATION_WEIGHTS = {
    "home": 0.50,
    "work": 0.30,
    "commute": 0.15,
    "other": 0.05,
}

# Safety categories
SAFETY_CATEGORIES = [
    "traffic",
    "crime",
    "flood",
    "air_quality",
    "medical_access",
    "fire",
]

# Safety level thresholds (percentile-based)
LEVEL_THRESHOLDS = {
    "green": (0, 33),    # safe
    "yellow": (33, 66),  # caution
    "red": (66, 100),    # alert
}
