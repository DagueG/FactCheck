"""
image_validator.py - Verifie la presence et la validite des liens d'image.

Objectif (mission etape 2) : "verifier la presence de liens d'images
exploitables (format, accessibilite)".

Principe de robustesse : la validation ne plante JAMAIS. En cas d'erreur reseau,
l'image est classee 'unreachable'/'unknown' plutot que de faire echouer le pipeline.

Classes de qualite renvoyees :
- "no_image"       : aucune URL d'image.
- "invalid_format" : URL presente mais extension/format non image.
- "ok"             : format valide (et accessible si verification reseau activee).
- "unreachable"    : format valide mais l'image ne repond pas (reseau).
- "unknown"        : format valide, accessibilite non verifiee.
"""
import logging
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import IMAGE_CONFIG

logger = logging.getLogger("factcheck")


def _has_valid_extension(url):
    lowered = url.lower().split("?")[0]
    return any(lowered.endswith(ext) for ext in IMAGE_CONFIG["valid_extensions"])


def classify_image_url(url, check_access=None, timeout=None):
    """
    Retourne un dict : {"quality": <str>, "accessible": <bool|None>}.
    - check_access : force ou desactive la verification reseau (None = valeur config).
    - Ne leve jamais d'exception.
    """
    if check_access is None:
        check_access = IMAGE_CONFIG["validate_access"]
    if timeout is None:
        timeout = IMAGE_CONFIG["timeout"]

    if not url:
        return {"quality": "no_image", "accessible": None}

    if not (url.startswith("http://") or url.startswith("https://")):
        return {"quality": "invalid_format", "accessible": None}

    # Un lien sans extension image connue n'est pas rejete d'office (beaucoup de
    # CDN n'exposent pas l'extension) : on s'appuiera sur le content-type si on
    # verifie l'acces. Sans verification reseau, on reste prudent -> "unknown".
    format_ok = _has_valid_extension(url)

    if not check_access:
        return {"quality": "ok" if format_ok else "unknown", "accessible": None}

    # Verification d'accessibilite best-effort (HEAD), tolerante aux pannes.
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        is_image = content_type in IMAGE_CONFIG["valid_content_types"] or content_type.startswith("image/")
        if resp.status_code < 400 and (is_image or format_ok):
            return {"quality": "ok", "accessible": True}
        if resp.status_code < 400:
            # repond mais pas identifie comme image
            return {"quality": "unknown", "accessible": True}
        return {"quality": "unreachable", "accessible": False}
    except requests.exceptions.RequestException:
        # timeout, DNS, connexion refusee... on ne casse pas le pipeline
        return {"quality": "unreachable" if format_ok else "unknown", "accessible": False}


def validate_articles(articles, check_access=None):
    """
    Applique la validation d'image sur une liste d'articles standardises.
    Met a jour en place : has_image, image_quality, validation_status.
    Retourne (articles, stats).
    """
    stats = {"with_image": 0, "ok": 0, "unreachable": 0, "invalid_format": 0,
             "unknown": 0, "no_image": 0, "total": len(articles)}

    for art in articles:
        image_urls = art.get("image_urls") or []
        url = image_urls[0] if image_urls else None
        result = classify_image_url(url, check_access=check_access)
        quality = result["quality"]

        art["has_image"] = bool(url) and quality not in ("no_image", "invalid_format")
        art["image_quality"] = quality
        # multimodal exploitable seulement si texte ET image utilisable
        if art["has_image"] and art.get("text_length", 0) > 0:
            art["validation_status"] = "valid"
        else:
            art["validation_status"] = "invalid"

        stats[quality] = stats.get(quality, 0) + 1
        if art["has_image"]:
            stats["with_image"] += 1

    return articles, stats
