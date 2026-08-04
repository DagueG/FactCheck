# Livrable 4 — Flux ETL avec Apache Airflow (Docker)

Automatisation du pipeline multimodal en trois tâches distinctes :

```
extract  →  transform  →  load
```

- **extract** : News API `/everything` si une clé est disponible, sinon repli. → `data/raw/etl_articles.json`
- **transform** : nettoyage / normalisation / enrichissement. → `data/processed/dataset.{csv,parquet}`
- **load** : chargement dans **PostgreSQL** (`factcheck-db`), repli **SQLite** si indisponible. → table `publications`

Les tâches **réutilisent directement** les fonctions des étapes 2 et 3 (aucune duplication de code).

---

## 1. Prérequis

- **Docker Desktop** installé et démarré.
- Se placer dans le dossier `04_orchestration/`.
- Copier la config d'environnement :
  ```powershell
  copy .env.example .env
  ```
  (Windows/macOS : laisser `AIRFLOW_UID=50000`. Linux : mettre le résultat de `id -u`.)

> La clé News API n'est **pas** nécessaire ici : sans clé, l'extraction bascule sur le repli et le flux
> se déroule quand même de bout en bout. Si ton fichier `../.env` contient `API_KEY_NEWS_API`, il est
> monté dans le conteneur et l'extraction se fera en **live**.

---

## 2. Démarrer la stack

```powershell
docker compose up -d
```
Le premier lancement télécharge les images et installe quelques libs Python (≈ 1 à 3 min).

Vérifier que tout est « healthy » :
```powershell
docker compose ps
```
**Attendu :** `airflow-webserver`, `airflow-scheduler`, `airflow-postgres`, `factcheck-db` en cours d'exécution.

Ouvrir l'interface : **http://localhost:8080** — identifiants **admin / admin**.

---

## 3. Exécuter le DAG (et capturer les preuves)

Dans l'UI, active puis déclenche le DAG **`factcheck_etl`** (bouton ▶️ « Trigger DAG »).

Ou en ligne de commande :
```powershell
docker compose exec airflow-scheduler airflow dags trigger factcheck_etl
```

**Ce que tu dois voir (captures d'écran pour la soutenance) :**
1. La vue **Grid/Graph** du DAG avec les 3 tâches **`extract → transform → load`** en **vert** (succès).
2. Les **logs** de chaque tâche (clic sur une tâche → Logs) : `SYNTHESE EXTRACTION`, `SYNTHESE TRANSFORMATION`, `[LOAD] OK -> base ...`.

---

## 4. Vérifier les données chargées en base

```powershell
docker compose exec factcheck-db psql -U factcheck -d factcheck -c "SELECT COUNT(*) FROM publications;"
docker compose exec factcheck-db psql -U factcheck -d factcheck -c "SELECT domain, source_trust, is_multimodal FROM publications LIMIT 10;"
```
**Attendu :** un compte de lignes > 0 et un extrait des publications avec leur `source_trust` et `is_multimodal`.

Les fichiers intermédiaires apparaissent aussi sur ton hôte dans `../data/raw/` et `../data/processed/`.

---

## 5. Arrêter / nettoyer

```powershell
docker compose down          # arrête les conteneurs (garde les données)
docker compose down -v       # + supprime les volumes (repart de zéro)
```

---

## 6. Sécurité de la base (points de vigilance de la mission)

- **Authentification** : l'accès à `factcheck-db` se fait par utilisateur/mot de passe. L'URI (donc les
  identifiants) est fournie par **variable d'environnement** `FACTCHECK_DB_URI`, **jamais écrite en dur**
  dans le code (`db_loader.py` ne contient aucun secret ; les logs masquent les identifiants).
- **Limitation des accès / rôles** : en production, on crée un utilisateur applicatif **aux privilèges
  restreints** (INSERT/SELECT sur la table `publications` uniquement), distinct du superutilisateur.
  Ici, un compte dédié `factcheck` isole déjà les données applicatives de la base de métadonnées Airflow.
- **Chiffrement des données sensibles** : les données de ce projet (actualités publiques) ne sont pas
  sensibles. Le cas échéant, on activerait **TLS** sur la connexion PostgreSQL et on chiffrerait/hasherait
  toute donnée personnelle avant stockage. Les secrets (clé API, mots de passe) restent hors du dépôt
  (`.env` non versionné) et peuvent être gérés via les **Connections/Variables Airflow** ou un coffre.

---

## 7. Notes d'architecture (pour la soutenance)

- **Trois `PythonOperator` simples**, une responsabilité par tâche : lisible et modulaire.
- **Réutilisation** des fonctions des étapes 2/3 : le DAG orchestre, il ne réimplémente rien.
- **Choix PostgreSQL** : le dataset transformé est **tabulaire et structuré** (une ligne par publication),
  ce qui se prête au relationnel ; PostgreSQL est robuste, supporté par le provider Airflow, et déjà présent
  dans la stack. La couche `raw` reste, elle, en JSON (semi-structuré).
- **Robustesse** : si PostgreSQL est indisponible, le chargement bascule sur **SQLite** — le flux ne casse pas.
