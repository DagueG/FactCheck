"""
config.py - Configuration centralisee du pipeline d'extraction.

Decisions d'architecture appliquees ici :
- AD-1 : on cible l'endpoint News API `/everything` (fiable) et NON
         `top-headlines?country=fr` (qui renvoie 0 resultat).
- AD-2 : la config NE plante PLUS si la cle API est absente. Le pipeline
         doit pouvoir tourner en mode repli (fallback) meme sans cle.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger .env depuis la racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Chemins ---
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
IMAGES_DIR = DATA_DIR / "images"
FALLBACK_DIR = DATA_DIR / "fallback"
LOGS_DIR = PROJECT_ROOT / "logs"

for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, IMAGES_DIR, FALLBACK_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# --- News API ---
NEWS_API_KEY = os.getenv("API_KEY_NEWS_API")  # peut etre None : gere par le fallback (AD-2)
NEWS_API_BASE_URL = "https://newsapi.org/v2"

# Requete par defaut pour /everything : large, en francais, pour garantir des resultats.
DEFAULT_QUERY = "France OR gouvernement OR sante OR desinformation OR economie"

NEWS_API_CONFIG = {
    "base_url": NEWS_API_BASE_URL,
    "api_key": NEWS_API_KEY,
    "endpoint": "everything",       # AD-1
    "language": "fr",
    "sort_by": "publishedAt",
    "page_size": 20,
    "timeout": 10,
    "default_query": DEFAULT_QUERY,
}

def has_news_api_key() -> bool:
    """True si une cle News API est disponible."""
    return bool(NEWS_API_KEY)

# --- Source de repli (AD-2) ---
FALLBACK_CONFIG = {
    "sample_path": FALLBACK_DIR / "sample_articles.json",
}

# --- Validation des images ---
IMAGE_CONFIG = {
    "validate_access": True,        # verifier l'accessibilite reseau (HEAD) pour les sources live
    "timeout": 5,
    "valid_extensions": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"],
    "valid_content_types": ["image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"],
}

# --- Domaines de confiance (sert au label faible, etapes suivantes) ---
TRUSTED_DOMAINS = [
    "theguardian.com", "bbc.com", "reuters.com", "apnews.com",
    "france24.com", "lemonde.fr", "20minutes.fr", "liberation.fr",
]

# --- Logging ---
LOGGING_CONFIG = {
    "level": "INFO",
    "log_file": LOGS_DIR / "extraction.log",
}
