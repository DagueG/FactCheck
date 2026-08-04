"""
common.py - Fonctions partagees par les differentes sources d'extraction.

Contient :
- configure_logging()   : configuration idempotente du logging (fichier + console).
- get_domain()          : extrait le nom de domaine d'une URL.
- standardize_article() : convertit un article brut (format News API) vers le
                          schema standard commun du projet.

Le schema standard est volontairement identique quelle que soit la source, pour
que l'etape de transformation (livrable 3) n'ait qu'un seul format a traiter.
"""
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Permettre `import config` quand le script est lance depuis la racine du projet
sys.path.insert(0, str(Path(__file__).parent))
from config import LOGGING_CONFIG


def configure_logging():
    """Configure le logging une seule fois (evite les lignes de log dupliquees)."""
    root = logging.getLogger()
    if root.handlers:  # deja configure
        return logging.getLogger("factcheck")

    logging.basicConfig(
        level=LOGGING_CONFIG["level"],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOGGING_CONFIG["log_file"], encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("factcheck")


def get_domain(url):
    """Retourne le domaine (sans 'www.') d'une URL, ou '' si non parsable."""
    if not url:
        return ""
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def standardize_article(article, source_origin="News API", language="fr", country="FR"):
    """
    Convertit un article brut (forme News API) vers le schema standard du projet.

    Les champs `has_image`, `image_quality` et `validation_status` sont initialises
    ici puis affines par l'etape de validation d'image.
    """
    url = article.get("url", "") or ""
    image_url = article.get("urlToImage")
    source_obj = article.get("source") or {}
    source_name = source_obj.get("name") if isinstance(source_obj, dict) else None
    content = article.get("content") or ""

    return {
        "id": str(uuid.uuid4()),
        "source_origin": source_origin,
        "source_name": source_name,
        "domain": get_domain(url),
        "title": article.get("title", "") or "",
        "description": article.get("description", "") or "",
        "content": content,
        "author": article.get("author", None),
        "image_urls": [image_url] if image_url else [],
        "image_paths": [],
        "published_at": article.get("publishedAt", "") or "",
        "scraped_at": _utcnow_iso(),
        "url": url,
        "language": language,
        "country": country,
        "category": "News",
        "label": None,
        "confidence": 0.0,
        "label_source": None,
        "text_length": len(content),
        "has_image": bool(image_url),
        "image_quality": "unknown",
        "validation_status": "pending",
    }
