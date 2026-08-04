"""
news_api_extractor.py - Extraction d'articles depuis News API
"""
import json
import logging
from datetime import datetime
import requests
import uuid
import sys
from pathlib import Path

# Ajouter le répertoire parent pour importer config
sys.path.insert(0, str(Path(__file__).parent))

from config import NEWS_API_CONFIG, RAW_DATA_DIR, LOGGING_CONFIG

# Configurer logging avec UTF-8 sur Windows
logging.basicConfig(
    level=LOGGING_CONFIG["level"],
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NewsAPIExtractor:
    def __init__(self):
        self.base_url = NEWS_API_CONFIG["base_url"]
        self.api_key = NEWS_API_CONFIG["api_key"]
        self.language = NEWS_API_CONFIG["language"]
        self.timeout = NEWS_API_CONFIG["timeout"]

    def extract_top_headlines(self, country="fr", page_size=20):
        """Extraire les top headlines d'un pays"""
        logger.info(f"Extraction top headlines pour {country}...")
        
        url = f"{self.base_url}/top-headlines"
        params = {
            "country": country,
            "pageSize": page_size,
            "apiKey": self.api_key,
            "sortBy": "publishedAt"
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # DEBUG: Afficher la réponse complète
            logger.info(f"Status: {data.get('status')}")
            logger.info(f"Total Results: {data.get('totalResults')}")
            if data.get('code'):
                logger.error(f"API Code: {data.get('code')}")
            if data.get('message'):
                logger.error(f"API Message: {data.get('message')}")
            
            if data["status"] == "ok":
                logger.info(f"[OK] {len(data['articles'])} articles reçus")
                return data["articles"]
            else:
                logger.error(f"[ERREUR API] {data.get('message', 'Erreur inconnue')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[ERREUR REQUETE] {e}")
            return []

    def standardize_article(self, article):
        """Convertir article News API au format standard"""
        return {
            "id": str(uuid.uuid4()),
            "source_origin": "News API",
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "content": article.get("content", ""),
            "author": article.get("author", None),
            "image_urls": [article.get("urlToImage")] if article.get("urlToImage") else [],
            "image_paths": [],
            "published_at": article.get("publishedAt", ""),
            "scraped_at": datetime.utcnow().isoformat(),
            "url": article.get("url", ""),
            "language": "fr",
            "country": "FR",
            "category": "News",
            "label": None,
            "confidence": 0.0,
            "label_source": None,
            "text_length": len(article.get("content", "")),
            "has_image": bool(article.get("urlToImage")),
            "image_quality": "unknown",
            "validation_status": "pending"
        }

    def save_articles(self, articles, filename="news_api_articles.json"):
        """Sauvegarder les articles en JSON"""
        if not articles:
            logger.warning("Aucun article a sauvegarder")
            return None
        
        output_path = RAW_DATA_DIR / filename
        standardized = [self.standardize_article(article) for article in articles]
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(standardized, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[SAUVEGARDE] {len(standardized)} articles -> {output_path}")
        return output_path


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("EXTRACTION NEWS API - Test")
    logger.info("=" * 70)
    
    extractor = NewsAPIExtractor()
    articles = extractor.extract_top_headlines(country="fr", page_size=5)
    
    if articles:
        extractor.save_articles(articles)
        print(f"\n[SUCCES] {len(articles)} articles extraits!")
    else:
        print("[ERREUR] Pas d'articles extraits")