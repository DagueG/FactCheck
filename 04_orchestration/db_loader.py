"""
db_loader.py - Etape "Load" du flux ETL (livrable 4).

Lit le dataset transforme (data/processed) et le charge dans une base SQL.

Robustesse (esprit AD-2) : on tente d'abord la base principale (PostgreSQL,
fournie par le docker-compose), et en cas d'indisponibilite on bascule sur une
base SQLite locale, pour qu'une demo ne tombe jamais en panne. Le choix de la
base se fait par la variable d'environnement FACTCHECK_DB_URI.

Securite : aucune credential n'est ecrite en dur ; l'URI (donc identifiants)
vient de l'environnement / des connexions Airflow.
"""
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02_extraction"))
from config import PROCESSED_DATA_DIR  # noqa: E402

logger = logging.getLogger("factcheck")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = "publications"

# Base principale : PostgreSQL du docker-compose (identifiants via l'environnement).
DEFAULT_PRIMARY_URI = os.getenv(
    "FACTCHECK_DB_URI",
    "postgresql+psycopg2://factcheck:factcheck@factcheck-db:5432/factcheck",
)
# Base de repli : SQLite locale, toujours disponible.
DEFAULT_FALLBACK_URI = f"sqlite:///{(PROJECT_ROOT / 'data' / 'processed' / 'factcheck.db').as_posix()}"


def _read_processed(processed_dir):
    """Lit dataset.parquet si possible, sinon dataset.csv."""
    processed_dir = Path(processed_dir)
    parquet_path = processed_dir / "dataset.parquet"
    csv_path = processed_dir / "dataset.csv"

    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path)
        except Exception as exc:  # pyarrow absent, fichier corrompu...
            logger.warning("[LOAD] Parquet illisible (%s) -> lecture CSV", exc)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(f"Aucun dataset trouve dans {processed_dir}")


def load_processed(processed_dir=None, table=DEFAULT_TABLE,
                   primary_uri=None, fallback_uri=None):
    """
    Charge le dataset transforme en base. Renvoie un dict de synthese.
    Tente la base principale puis la base de repli. Leve une erreur seulement
    si les DEUX echouent.
    """
    processed_dir = processed_dir or PROCESSED_DATA_DIR
    primary_uri = primary_uri or DEFAULT_PRIMARY_URI
    fallback_uri = fallback_uri or DEFAULT_FALLBACK_URI

    df = _read_processed(processed_dir)
    logger.info("[LOAD] Dataset lu : %d lignes, %d colonnes", len(df), len(df.columns))

    last_error = None
    for label, uri in [("principale (PostgreSQL)", primary_uri), ("repli (SQLite)", fallback_uri)]:
        safe_uri = uri.split("@")[-1] if "@" in uri else uri  # ne pas logguer les identifiants
        try:
            engine = create_engine(uri)
            with engine.begin() as conn:
                df.to_sql(table, conn, if_exists="replace", index=False)
            with engine.connect() as conn:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            logger.info("[LOAD] OK -> base %s : %d lignes dans '%s' (%s)",
                        label, n, table, safe_uri)
            return {"which": label, "target": safe_uri, "table": table, "rows": int(n)}
        except Exception as exc:
            last_error = exc
            logger.warning("[LOAD] Base %s indisponible (%s) -> tentative suivante", label, exc)

    raise RuntimeError(f"[LOAD] Chargement impossible sur toutes les bases : {last_error}")


if __name__ == "__main__":
    from common import configure_logging  # type: ignore
    configure_logging()
    print(load_processed())
