"""
fallback_source.py - Source de repli embarquee (AD-2).

Quand News API est indisponible, sans cle, en panne ou renvoie 0 resultat, le
pipeline bascule sur ce jeu d'articles local. Objectif : garantir qu'une demo
ne tombe JAMAIS en panne a cause d'un service externe.

Le fichier de secours est au meme format que les articles News API bruts, si
bien qu'il traverse exactement le meme code de standardisation.
"""
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import FALLBACK_CONFIG

logger = logging.getLogger("factcheck")


class FallbackSource:
    """Charge des articles d'actualite depuis un fichier JSON embarque."""

    def __init__(self, sample_path=None):
        self.sample_path = Path(sample_path) if sample_path else FALLBACK_CONFIG["sample_path"]

    def fetch(self, limit=None):
        """Retourne une liste d'articles bruts (format News API). Ne plante jamais."""
        logger.info("[FALLBACK] Chargement du jeu de secours : %s", self.sample_path.name)
        try:
            with open(self.sample_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("[FALLBACK] Impossible de charger le jeu de secours : %s", exc)
            return []

        if limit is not None:
            articles = articles[:limit]
        logger.info("[FALLBACK] %d articles de secours charges", len(articles))
        return articles
