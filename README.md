# FactCheck — Pipeline d'extraction de données multimodales (CheckIt.AI)

Pipeline d'acquisition de publications d'actualité **multimodales (texte + image)**, destiné à entraîner
un détecteur de fake news. Chaîne complète : **extraction → transformation → orchestration ETL → stockage → dashboard KPI**.

---

## Structure du projet

| Dossier | Rôle | Livrable |
|---|---|---|
| `01_exploration/` | Rapport d'exploration des sources | Rapport (Markdown) |
| `02_extraction/` | Scripts d'extraction (News API + repli) | Scripts d'extraction |
| `03_transformation/` | Pipeline de nettoyage/normalisation + schéma | Pipeline + schéma Mermaid |
| `04_orchestration/` | DAG Airflow + docker-compose (PostgreSQL) | Flux ETL |
| `05_dashboard/` | Dashboard Streamlit + plan de monitoring | Dashboard KPI + monitoring |
| `data/` | `raw/` (JSON brut), `processed/` (CSV/Parquet), `fallback/` (secours) | — |
| `logs/` | Journaux d'exécution | — |

---

## Prérequis (à faire une seule fois)

1. **Environnement Python** (déjà présent dans `.venv`). Installer les dépendances :
   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements-base.txt
   .venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
   ```
2. **Clé News API** : créer un fichier `.env` à la racine contenant :
   ```
   API_KEY_NEWS_API=ta_cle_ici
   ```
   > Sans clé, l'extraction bascule automatiquement sur le jeu de secours (le pipeline fonctionne quand même).
3. **Docker Desktop** installé et démarré (pour l'étape ETL Airflow).

---

## Exécution complète, dans l'ordre

> Toutes les commandes se lancent depuis la racine `FactCheck/`, sauf indication contraire.

### 1. Extraction (News API → `data/raw/`)
```powershell
.venv\Scripts\python.exe 02_extraction\extract.py --query "France OR sante OR desinformation" --language fr --page-size 10
```
Attendu : `Origine des donnees : News API`, des articles `avec image exploitable`.

### 2. Transformation (`data/raw/` → `data/processed/`)
```powershell
del data\raw\etl_articles.json    # supprime un éventuel résidu du run Airflow (évite le mélange)
.venv\Scripts\python.exe 03_transformation\transform.py
```
Attendu : un `dataset.csv` **et** un `dataset.parquet` dans `data/processed/`.

### 3. Flux ETL Airflow (Docker → PostgreSQL)
```powershell
cd 04_orchestration
copy .env.example .env            # première fois seulement
docker compose up -d
docker compose ps                 # attendre que les services soient "healthy" / "Up"
```
Déclencher le DAG puis vérifier son état :
```powershell
docker compose exec airflow-scheduler airflow dags unpause factcheck_etl
docker compose exec airflow-scheduler airflow dags trigger factcheck_etl
docker compose exec airflow-scheduler airflow dags list-runs -d factcheck_etl
```
Attendu : le run passe à l'état `success` (après ~30 s).

Interface web : **http://localhost:8080** — identifiants **admin / admin**.

Vérifier les données chargées en base :
```powershell
docker compose exec factcheck-db psql -U factcheck -d factcheck -c "SELECT COUNT(*) FROM publications;"
docker compose exec factcheck-db psql -U factcheck -d factcheck -c "SELECT domain, source_trust, is_multimodal FROM publications LIMIT 10;"
```
Attendu : un `COUNT` > 0.

### 4. Dashboard KPI (Streamlit)
```powershell
cd ..
.venv\Scripts\python.exe -m streamlit run 05_dashboard\app.py
```
Attendu : le dashboard s'ouvre sur **http://localhost:8501** (KPI, graphiques, run chronométré).

---

## Arrêt / nettoyage
```powershell
# arrêter le dashboard : Ctrl+C dans le terminal Streamlit
cd 04_orchestration
docker compose down        # arrête Airflow (garde les données)
docker compose down -v     # + supprime les volumes (repart de zéro)
```

---

## Décisions d'architecture (repères)

- **AD-1** : extraction via l'endpoint News API `/everything` (fiable), et non `top-headlines?country=fr` (renvoie 0).
- **AD-2** : repli gracieux à chaque dépendance externe (News API → jeu de secours ; PostgreSQL → SQLite) : la démo ne tombe jamais en panne.
- **AD-3** : séparation ingestion labellisée (vérité terrain) / acquisition temps réel.
- **AD-4** : stockage en deux couches — `raw` (JSON) puis `processed` (Parquet/CSV).
- `source_trust` = **signal faible** de fiabilité de la source, **≠** label vrai/faux (laissé aux jeux labellisés Fakeddit / FakeNewsNet).
