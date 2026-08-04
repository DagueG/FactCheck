"""
etl_tasks.py - Fonctions appelees par les PythonOperator du DAG Airflow.

Chaque fonction reutilise DIRECTEMENT les modules des etapes 2 et 3 (pas de
duplication de code) et represente une tache distincte du flux ETL.

Le flux est auto-contenu par execution :
  extract -> ecrit data/raw/etl_articles.json (live si cle dispo, sinon repli)
  transform -> lit CE fichier precis -> data/processed/dataset.{csv,parquet}
  load -> charge data/processed dans la base (PostgreSQL, repli SQLite)
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("02_extraction", "03_transformation", "04_orchestration"):
    sys.path.insert(0, str(PROJECT_ROOT / _sub))

from config import RAW_DATA_DIR          # noqa: E402
from common import configure_logging     # noqa: E402
import extract                           # noqa: E402
import transform                         # noqa: E402
from db_loader import load_processed     # noqa: E402

logger = logging.getLogger("factcheck")

ETL_RAW_FILE = RAW_DATA_DIR / "etl_articles.json"


def task_extract(**_):
    """Tache 1 - Extraction (News API si cle dispo, sinon repli). Nom de fichier fixe."""
    configure_logging()
    rc = extract.run(["--source", "auto", "--page-size", "20", "--output", "etl_articles.json"])
    if rc != 0:
        raise RuntimeError("Extraction en echec")
    logger.info("[ETL] Extraction terminee -> %s", ETL_RAW_FILE)


def task_transform(**_):
    """Tache 2 - Transformation du fichier produit par l'extraction."""
    configure_logging()
    rc = transform.run(["--raw-file", str(ETL_RAW_FILE), "--basename", "dataset"])
    if rc != 0:
        raise RuntimeError("Transformation en echec")
    logger.info("[ETL] Transformation terminee")


def task_load(**_):
    """Tache 3 - Chargement du dataset transforme en base."""
    configure_logging()
    result = load_processed()
    logger.info("[ETL] Chargement termine : %s", result)
    return result


if __name__ == "__main__":
    # Permet de tester la chaine ETL complete SANS Airflow.
    configure_logging()
    task_extract()
    task_transform()
    print(task_load())
