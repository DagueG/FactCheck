"""
config.py - Configuration centralisée
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger depuis la racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Chemins
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
IMAGES_DIR = DATA_DIR / "images"
LOGS_DIR = PROJECT_ROOT / "logs"

for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, IMAGES_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# News API
NEWS_API_KEY = os.getenv("API_KEY_NEWS_API")
if not NEWS_API_KEY:
    raise ValueError("❌ API_KEY_NEWS_API manquante dans .env")

NEWS_API_BASE_URL = "https://newsapi.org/v2"

NEWS_API_CONFIG = {
    "base_url": NEWS_API_BASE_URL,
    "api_key": NEWS_API_KEY,
    "language": "fr",
    "sort_by": "publishedAt",
    "page_size": 100,
    "timeout": 10,
}

TRUSTED_DOMAINS = [
    "theguardian.com", "bbc.com", "reuters.com", "apnews.com",
    "france24.com", "lemonde.fr", "20minutes.fr", "liberation.fr"
]

LOGGING_CONFIG = {
    "level": "INFO",
    "log_file": LOGS_DIR / "extraction.log",
}