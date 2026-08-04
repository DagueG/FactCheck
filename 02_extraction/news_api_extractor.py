"""
news_api_extractor.py - Extraction d'articles depuis News API.

AD-1 : on interroge l'endpoint `/everything` (fiable, images presentes), et NON
`top-headlines?country=fr` qui renvoie 0 resultat.

La classe se contente de la "connexion + recuperation brute". La standardisation
(parsing vers le schema commun) est faite par common.standardize_article, et la
validation d'image par image_validator : chaque responsabilite est isolee.
"""
import logging
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import NEWS_API_CONFIG, has_news_api_key
from common import configure_logging

logger = logging.getLogger("factcheck")


class NewsAPIExtractor:
    """Recupere des articles bruts depuis l'endpoint /everything de News API."""

    def __init__(self):
        cfg = NEWS_API_CONFIG
        self.base_url = cfg["base_url"]
        self.api_key = cfg["api_key"]
        self.language = cfg["language"]
        self.sort_by = cfg["sort_by"]
        self.page_size = cfg["page_size"]
        self.timeout = cfg["timeout"]
        self.default_query = cfg["default_query"]

    def is_available(self):
        """La source est disponible seulement si une cle API est presente."""
        return has_news_api_key()

    def fetch(self, query=None, language=None, page_size=None):
        """
        Interroge /everything et renvoie la liste d'articles bruts.
        Renvoie [] en cas d'echec (aucune exception ne remonte).
        """
        if not self.is_available():
            logger.warning("[NEWS API] Aucune cle API : source indisponible")
            return []

        query = query or self.default_query
        language = language or self.language
        page_size = page_size or self.page_size

        url = f"{self.base_url}/everything"
        params = {
            "q": query,
            "language": language,
            "pageSize": page_size,
            "sortBy": self.sort_by,
            "apiKey": self.api_key,
        }

        logger.info("[NEWS API] Requete /everything (q=%r, lang=%s, size=%d)",
                    query, language, page_size)
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("[NEWS API] Erreur reseau/HTTP : %s", exc)
            return []
        except ValueError as exc:  # JSON invalide
            logger.error("[NEWS API] Reponse non-JSON : %s", exc)
            return []

        if data.get("status") != "ok":
            logger.error("[NEWS API] Erreur API : code=%s message=%s",
                         data.get("code"), data.get("message"))
            return []

        articles = data.get("articles", [])
        logger.info("[NEWS API] status=ok | total=%s | recus=%d",
                    data.get("totalResults"), len(articles))
        return articles


if __name__ == "__main__":
    configure_logging()
    logger.info("=" * 70)
    logger.info("TEST unitaire NewsAPIExtractor")
    logger.info("=" * 70)
    extractor = NewsAPIExtractor()
    arts = extractor.fetch(page_size=5)
    print(f"[RESULTAT] {len(arts)} articles bruts recuperes "
          f"(cle presente: {extractor.is_available()})")
