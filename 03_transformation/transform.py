"""
transform.py - Pipeline de transformation reproductible (livrable 3).

Chaine, de facon journalisee et rejouable :
  1. LECTURE    -> lit les JSON bruts de data/raw/ (sortie du livrable 2)
  2. TRAITEMENT -> nettoie le texte, valide les images, normalise les dates,
                   genere des colonnes (fiabilite de source, multimodalite...)
                   et dedoublonne.
  3. EXPORT     -> ecrit data/processed/ en CSV (toujours) et Parquet (si dispo).

Principes :
- Fonctions modulaires (nettoie_texte, valide_image, normalise_date, enrichir...).
- Reproductible : meme entree -> meme sortie ; chaque etape est journalisee.
- Robuste : Parquet est optionnel (repli CSV si pyarrow absent), rien ne plante.

IMPORTANT (distinction opinion / desinformation) :
  la colonne `source_trust` est un SIGNAL FAIBLE de fiabilite de la source, ce
  n'est PAS un label vrai/faux. Les champs `label`/`label_source` restent vides,
  a remplir plus tard via les jeux labellises (Fakeddit, FakeNewsNet).
"""
import argparse
import html
import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

# Reutiliser la config et le logging du module d'extraction
sys.path.insert(0, str(Path(__file__).parent.parent / "02_extraction"))
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, TRUSTED_DOMAINS
from common import configure_logging, get_domain

logger = logging.getLogger("factcheck")

# --- Regex de nettoyage ---
_TRUNCATION_RE = re.compile(r"\s*\[\+\d+\s*chars?\]\s*$")   # marqueur "[+1234 chars]" de News API
_TAG_RE = re.compile(r"<[^>]+>")                            # balises HTML
_WS_RE = re.compile(r"\s+")                                 # espaces multiples

USABLE_IMAGE_QUALITY = {"ok", "unknown"}                    # images considerees exploitables


# ---------------------------------------------------------------------------
# 1. LECTURE
# ---------------------------------------------------------------------------
def lire_articles(input_dir=RAW_DATA_DIR, raw_file=None, include_fallback=False):
    """
    Lit un fichier JSON precis, ou tous les *.json de data/raw/. Ne plante jamais.

    Par defaut, le fichier de repli (fallback_*.json) est IGNORE : c'est une
    source de secours de demonstration, pas du corpus reel. Utiliser
    include_fallback=True pour l'inclure explicitement.
    """
    input_dir = Path(input_dir)
    if raw_file:
        fichiers = [Path(raw_file)]
    else:
        fichiers = sorted(input_dir.glob("*.json"))
        if not include_fallback:
            ignores = [f.name for f in fichiers if f.name.startswith("fallback")]
            fichiers = [f for f in fichiers if not f.name.startswith("fallback")]
            for name in ignores:
                logger.info("[LECTURE] Fichier de repli ignore : %s (utiliser --include-fallback pour l'inclure)", name)
    articles = []
    for f in fichiers:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            articles.extend(data)
            logger.info("[LECTURE] %d articles lus depuis %s", len(data), f.name)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("[LECTURE] Echec lecture %s : %s", f, exc)
    logger.info("[LECTURE] Total : %d articles bruts", len(articles))
    return articles


# ---------------------------------------------------------------------------
# 2. TRAITEMENT (fonctions unitaires)
# ---------------------------------------------------------------------------
def nettoie_texte(text):
    """Enleve HTML, entites, marqueur de troncature News API, et normalise les espaces."""
    if not text:
        return ""
    t = html.unescape(text)
    t = _TAG_RE.sub(" ", t)
    t = _TRUNCATION_RE.sub("", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def valide_image(article):
    """True si l'article possede une image exploitable (presente + qualite acceptable)."""
    if not article.get("has_image"):
        return False
    return article.get("image_quality") in USABLE_IMAGE_QUALITY


def normalise_date(published_at):
    """Convertit une date ISO en date (YYYY-MM-DD). Retourne None si invalide."""
    ts = pd.to_datetime(published_at, utc=True, errors="coerce")
    return None if pd.isna(ts) else ts.date().isoformat()


def source_trust(domain):
    """Signal FAIBLE de fiabilite : 'trusted' si domaine connu, sinon 'unknown'. (PAS un label vrai/faux.)"""
    return "trusted" if domain in TRUSTED_DOMAINS else "unknown"


def enrichir(article):
    """Construit un enregistrement propre et enrichi a partir d'un article standardise."""
    title_clean = nettoie_texte(article.get("title", ""))
    desc_clean = nettoie_texte(article.get("description", ""))
    content_clean = nettoie_texte(article.get("content", ""))
    # texte consolide pour le NLP (titre + description + contenu)
    text_clean = " ".join(p for p in [title_clean, desc_clean, content_clean] if p)

    domain = article.get("domain") or get_domain(article.get("url", ""))
    image_urls = article.get("image_urls") or []
    has_image = valide_image(article)

    return {
        # cles / tracabilite
        "id": article.get("id"),
        "url": article.get("url", ""),
        "source_origin": article.get("source_origin"),
        "source_name": article.get("source_name"),
        "domain": domain,
        # modalite texte (NLP)
        "title_clean": title_clean,
        "text_clean": text_clean,
        "text_length_clean": len(text_clean),
        # modalite image
        "image_url": image_urls[0] if image_urls else None,
        "n_images": len(image_urls),
        "has_image": has_image,
        "image_quality": article.get("image_quality"),
        # metadonnees
        "published_date": normalise_date(article.get("published_at")),
        "language": article.get("language"),
        "country": article.get("country"),
        # signaux / cible
        "source_trust": source_trust(domain),
        "is_multimodal": bool(has_image and len(text_clean) > 0),
        "label": article.get("label"),            # a remplir via jeux labellises
        "label_source": article.get("label_source"),
        "confidence": article.get("confidence", 0.0),
    }


def transforme(articles):
    """Applique l'enrichissement a tous les articles et renvoie un DataFrame."""
    logger.info("[TRAITEMENT] Nettoyage + enrichissement de %d articles...", len(articles))
    records = [enrichir(a) for a in articles]
    df = pd.DataFrame(records)
    return df


def dedoublonne(df):
    """Supprime les doublons (par url, puis par titre nettoye)."""
    avant = len(df)
    if "url" in df.columns:
        df = df[~(df["url"].duplicated() & df["url"].astype(bool))]
    df = df.drop_duplicates(subset=["title_clean"]).reset_index(drop=True)
    logger.info("[TRAITEMENT] Dedoublonnage : %d -> %d", avant, len(df))
    return df


def filtre_qualite(df):
    """Garde les entrees avec un texte non vide (le multimodal est signale, pas impose)."""
    avant = len(df)
    df = df[df["text_length_clean"] > 0].reset_index(drop=True)
    logger.info("[TRAITEMENT] Filtre texte non vide : %d -> %d", avant, len(df))
    return df


# ---------------------------------------------------------------------------
# 3. EXPORT
# ---------------------------------------------------------------------------
def exporte(df, processed_dir=PROCESSED_DATA_DIR, basename="dataset"):
    """Ecrit CSV (toujours) et Parquet (si pyarrow dispo). Renvoie la liste des chemins ecrits."""
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    ecrits = []

    csv_path = processed_dir / f"{basename}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info("[EXPORT] CSV ecrit : %s (%d lignes)", csv_path, len(df))
    ecrits.append(csv_path)

    parquet_path = processed_dir / f"{basename}.parquet"
    try:
        df.to_parquet(parquet_path, index=False)
        logger.info("[EXPORT] Parquet ecrit : %s", parquet_path)
        ecrits.append(parquet_path)
    except (ImportError, ValueError) as exc:
        logger.warning("[EXPORT] Parquet ignore (pyarrow absent ?) : %s "
                       "-> installe 'pyarrow' pour l'activer.", exc)
    return ecrits


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run(argv=None):
    configure_logging()
    parser = argparse.ArgumentParser(description="Pipeline de transformation (CheckIt.AI).")
    parser.add_argument("--raw-file", default=None, help="Fichier JSON precis a traiter (sinon tout data/raw/).")
    parser.add_argument("--basename", default="dataset", help="Nom de base des fichiers de sortie.")
    parser.add_argument("--include-fallback", action="store_true",
                        help="Inclure le fichier de repli (fallback_*.json), exclu par defaut.")
    args = parser.parse_args(argv)

    logger.info("=" * 70)
    logger.info("TRANSFORMATION - demarrage")
    logger.info("=" * 70)

    articles = lire_articles(raw_file=args.raw_file, include_fallback=args.include_fallback)
    if not articles:
        logger.error("[RESULTAT] Aucun article a transformer (data/raw vide ?).")
        print("[ECHEC] Rien a transformer. Lance d'abord l'extraction (02_extraction/extract.py).")
        return 1

    df = transforme(articles)
    df = dedoublonne(df)
    df = filtre_qualite(df)
    chemins = exporte(df, basename=args.basename)

    n_multi = int(df["is_multimodal"].sum())
    n_trusted = int((df["source_trust"] == "trusted").sum())
    logger.info("[SYNTHESE] final=%d | multimodal=%d | sources_fiables=%d",
                len(df), n_multi, n_trusted)

    print("\n===== SYNTHESE TRANSFORMATION =====")
    print(f"Articles en entree   : {len(articles)}")
    print(f"Lignes en sortie     : {len(df)}")
    print(f"Dont multimodales    : {n_multi}")
    print(f"Dont sources fiables : {n_trusted}")
    print(f"Colonnes generees    : {len(df.columns)}")
    print("Fichiers ecrits      :")
    for c in chemins:
        print(f"   - {c}")
    print("===================================")
    return 0


if __name__ == "__main__":
    sys.exit(run())
