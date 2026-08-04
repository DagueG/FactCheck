"""
extract.py - Orchestrateur d'extraction multimodale (livrable 2).

Enchaine, sans jamais planter (AD-2) :
  1. connexion    -> News API /everything (AD-1), avec repli sur jeu de secours
  2. parsing      -> standardisation vers le schema commun
  3. nettoyage    -> validation des liens d'image (format + accessibilite)
  4. sauvegarde   -> ecriture JSON dans data/raw/

Executable sans intervention manuelle et parametrable en ligne de commande.

Exemples :
  python 02_extraction/extract.py
  python 02_extraction/extract.py --query "sante OR vaccin" --language fr --page-size 30
  python 02_extraction/extract.py --source fallback          # force le mode secours (sans cle)
  python 02_extraction/extract.py --no-image-check           # extraction plus rapide (pas de HEAD reseau)
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import RAW_DATA_DIR, NEWS_API_CONFIG
from common import configure_logging, standardize_article
from news_api_extractor import NewsAPIExtractor
from fallback_source import FallbackSource
from image_validator import validate_articles

logger = logging.getLogger("factcheck")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Extraction multimodale d'actualites (CheckIt.AI).")
    p.add_argument("--query", default=NEWS_API_CONFIG["default_query"],
                   help="Mots-cles de recherche (endpoint /everything).")
    p.add_argument("--language", default=NEWS_API_CONFIG["language"], help="Langue (ex: fr, en).")
    p.add_argument("--page-size", type=int, default=NEWS_API_CONFIG["page_size"],
                   help="Nombre d'articles a recuperer.")
    p.add_argument("--source", choices=["auto", "newsapi", "fallback"], default="auto",
                   help="Source : auto (News API puis repli), newsapi seul, ou fallback seul.")
    p.add_argument("--no-image-check", action="store_true",
                   help="Desactive la verification reseau des images (plus rapide, hors ligne).")
    p.add_argument("--output", default="news_api_articles.json",
                   help="Nom du fichier de sortie dans data/raw/.")
    return p.parse_args(argv)


def acquire_raw(source, query, language, page_size):
    """
    Recupere les articles bruts selon la strategie choisie.
    Retourne (articles_bruts, origine_utilisee).
    """
    if source == "fallback":
        return FallbackSource().fetch(limit=page_size), "fallback"

    if source in ("auto", "newsapi"):
        extractor = NewsAPIExtractor()
        articles = extractor.fetch(query=query, language=language, page_size=page_size)
        if articles:
            return articles, "News API"
        if source == "newsapi":
            logger.warning("[ORCHESTRATION] News API vide/indisponible (mode newsapi force).")
            return [], "News API"
        # mode auto : on bascule sur le repli (AD-2)
        logger.warning("[ORCHESTRATION] News API vide/indisponible -> bascule sur le repli.")
        return FallbackSource().fetch(limit=page_size), "fallback"

    return [], "aucune"


def save_articles(articles, filename):
    output_path = RAW_DATA_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    logger.info("[SAUVEGARDE] %d articles -> %s", len(articles), output_path)
    return output_path


def run(argv=None):
    configure_logging()
    args = parse_args(argv)

    logger.info("=" * 70)
    logger.info("EXTRACTION MULTIMODALE - demarrage (source=%s)", args.source)
    logger.info("=" * 70)

    # 1. Connexion / recuperation (avec repli)
    raw_articles, origin = acquire_raw(args.source, args.query, args.language, args.page_size)
    if not raw_articles:
        logger.error("[RESULTAT] Aucun article recupere (meme via repli). Rien a sauvegarder.")
        print("[ECHEC] Aucun article extrait.")
        return 1

    # 2. Parsing / standardisation
    country = "FR" if args.language == "fr" else "XX"
    standardized = [standardize_article(a, source_origin=origin,
                                        language=args.language, country=country)
                    for a in raw_articles]

    # 3. Nettoyage / validation des images
    check_access = not args.no_image_check
    standardized, stats = validate_articles(standardized, check_access=check_access)

    # 4. Sauvegarde
    output_path = save_articles(standardized, args.output)

    # Rapport de synthese
    logger.info("[SYNTHESE] origine=%s | total=%d | avec image=%d | multimodal valides=%d",
                origin, stats["total"], stats["with_image"],
                sum(1 for a in standardized if a["validation_status"] == "valid"))
    print("\n===== SYNTHESE EXTRACTION =====")
    print(f"Origine des donnees : {origin}")
    print(f"Articles extraits    : {stats['total']}")
    print(f"Avec image exploitable : {stats['with_image']}")
    print(f"Multimodal valides   : {sum(1 for a in standardized if a['validation_status'] == 'valid')}")
    print(f"Qualite images       : ok={stats.get('ok',0)} | unreachable={stats.get('unreachable',0)} "
          f"| unknown={stats.get('unknown',0)} | invalid={stats.get('invalid_format',0)} "
          f"| sans image={stats.get('no_image',0)}")
    print(f"Fichier de sortie    : {output_path}")
    print("================================")
    return 0


if __name__ == "__main__":
    sys.exit(run())
