"""
factcheck_etl_dag.py - DAG Airflow du flux ETL multimodal (livrable 4).

Trois taches distinctes, chacune un PythonOperator simple, qui reutilisent les
fonctions des etapes 2 et 3 :

    extract  >>  transform  >>  load

- extract   : News API (/everything) si cle dispo, sinon repli. -> data/raw
- transform : nettoyage / normalisation / enrichissement.       -> data/processed
- load      : chargement en base PostgreSQL (repli SQLite).      -> table 'publications'

Declenchement manuel (schedule=None) : adapte a une demo et aux captures d'ecran.
"""
import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Rendre les modules du projet importables dans le conteneur Airflow.
# Ce fichier est monte sous /opt/airflow/project/04_orchestration/dags/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "04_orchestration"))

from etl_tasks import task_extract, task_transform, task_load  # noqa: E402

default_args = {
    "owner": "checkit.ai",
    "retries": 1,
}

with DAG(
    dag_id="factcheck_etl",
    description="Flux ETL multimodal : extraction -> transformation -> chargement",
    default_args=default_args,
    schedule=None,                     # declenchement manuel
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["factcheck", "etl", "multimodal"],
) as dag:

    extract = PythonOperator(
        task_id="extract",
        python_callable=task_extract,
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable=task_transform,
    )

    load = PythonOperator(
        task_id="load",
        python_callable=task_load,
    )

    extract >> transform >> load
