"""
metrics.py - Calcul des KPI du pipeline (livrable 5).

Sépare la LOGIQUE (testable en pur Python) de l'AFFICHAGE (app.py / Streamlit).

Trois familles de KPI (cf. mission) :
- PRÉCISION des données : % d'entrées valides / multimodales / de source fiable...
- RAPIDITÉ : durée de chaque étape (extract, transform) via un run chronométré.
- COÛT / ressources : volume traité, taille des fichiers de sortie.

Volontairement SANS dépendance à la base ni à Airflow : le dashboard reste
lançable avec seulement pandas + streamlit + plotly.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("02_extraction", "03_transformation", "05_dashboard"):
    sys.path.insert(0, str(PROJECT_ROOT / _sub))

from config import RAW_DATA_DIR, PROCESSED_DATA_DIR  # noqa: E402

DATASET_PARQUET = PROCESSED_DATA_DIR / "dataset.parquet"
DATASET_CSV = PROCESSED_DATA_DIR / "dataset.csv"
RUN_METRICS_PATH = PROCESSED_DATA_DIR / "run_metrics.json"
ETL_FILE = "etl_articles.json"


# ---------------------------------------------------------------------------
# Chargement du dataset
# ---------------------------------------------------------------------------
def load_dataset():
    """Charge le dataset transformé (parquet sinon csv). Retourne None si absent."""
    if DATASET_PARQUET.exists():
        try:
            return pd.read_parquet(DATASET_PARQUET)
        except Exception:
            pass
    if DATASET_CSV.exists():
        return pd.read_csv(DATASET_CSV)
    return None


# ---------------------------------------------------------------------------
# KPI de précision / qualité des données
# ---------------------------------------------------------------------------
def compute_data_kpis(df):
    """Calcule les KPI qualité à partir du dataset."""
    n = len(df)
    if n == 0:
        return {"total": 0, "pct_multimodal": 0.0, "pct_trusted": 0.0,
                "pct_with_image": 0.0, "avg_text_length": 0.0,
                "n_domains": 0, "n_languages": 0}
    return {
        "total": n,
        "pct_multimodal": float(round(100 * df["is_multimodal"].mean(), 1)),
        "pct_trusted": float(round(100 * (df["source_trust"] == "trusted").mean(), 1)),
        "pct_with_image": float(round(100 * df["has_image"].mean(), 1)),
        "avg_text_length": float(round(df["text_length_clean"].mean(), 0)),
        "n_domains": int(df["domain"].nunique()),
        "n_languages": int(df["language"].nunique()),
    }


# ---------------------------------------------------------------------------
# KPI de rapidité / coût : run chronométré
# ---------------------------------------------------------------------------
def run_timed_pipeline(page_size=20):
    """
    Exécute extraction + transformation en chronométrant chaque étape, puis
    écrit run_metrics.json. Réutilise les scripts des étapes 2 et 3.
    Le flux est auto-contenu (fichier etl_articles.json + transform --raw-file).
    """
    import extract       # noqa: E402
    import transform      # noqa: E402

    timings = {}

    t0 = time.perf_counter()
    extract.run(["--source", "auto", "--page-size", str(page_size), "--output", ETL_FILE])
    timings["extract_s"] = round(time.perf_counter() - t0, 2)

    t0 = time.perf_counter()
    transform.run(["--raw-file", str(RAW_DATA_DIR / ETL_FILE), "--basename", "dataset"])
    timings["transform_s"] = round(time.perf_counter() - t0, 2)

    timings["total_s"] = round(timings["extract_s"] + timings["transform_s"], 2)

    # Coût / ressources
    df = load_dataset()
    timings["rows"] = 0 if df is None else len(df)
    timings["csv_kb"] = round(DATASET_CSV.stat().st_size / 1024, 1) if DATASET_CSV.exists() else 0
    timings["parquet_kb"] = round(DATASET_PARQUET.stat().st_size / 1024, 1) if DATASET_PARQUET.exists() else 0
    timings["ran_at"] = pd.Timestamp.now(tz="UTC").isoformat()

    RUN_METRICS_PATH.write_text(json.dumps(timings, indent=2), encoding="utf-8")
    return timings


def load_run_metrics():
    """Lit run_metrics.json si présent, sinon None."""
    if RUN_METRICS_PATH.exists():
        try:
            return json.loads(RUN_METRICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


if __name__ == "__main__":
    from common import configure_logging  # noqa: E402
    configure_logging()
    print("Run chronométré...")
    print(run_timed_pipeline())
    df = load_dataset()
    print("KPI données:", compute_data_kpis(df))
