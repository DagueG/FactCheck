# Plan de monitoring du pipeline — CheckIt.AI
### Livrable 5 (partie monitoring)

Ce plan décrit comment **surveiller le pipeline en production** : quels indicateurs suivre, à partir de quels
**seuils** alerter, comment **gérer les erreurs**, et à quelle **fréquence** vérifier. Il est cohérent avec les
automatisations déjà en place (Airflow, logs, repli gracieux).

---

## 1. Objectifs

- Garantir la **qualité** des données livrées au modèle (texte + image bien associés, sources traçables).
- Détecter vite toute **dégradation** (source qui tombe, images inaccessibles, volume anormal).
- Assurer la **disponibilité** du flux ETL et la **fraîcheur** des données.

---

## 2. KPI suivis et seuils d'alerte

| KPI | Description | Seuil d'alerte | Action si franchi |
|---|---|---|---|
| **% entrées multimodales** | texte **et** image exploitables | < 80 % | Vérifier la validation d'image et l'accessibilité des URLs |
| **% images accessibles** (`ok`) | images joignables au bon format | < 85 % | Contrôler le réseau / le CDN des sources ; augmenter le timeout |
| **Volume par run** | nombre de publications extraites | < 5 ou = 0 | Vérifier l'API (quota, clé, endpoint) ; le repli a-t-il été activé ? |
| **% source de repli** | part des runs servis par le fallback | > 20 % | La source principale est instable → investiguer News API |
| **Durée du flux ETL** | temps total extract→transform→load | > 3× la médiane | Vérifier ressources / lenteur réseau / taille des lots |
| **Échecs de tâche Airflow** | tâches en `failed` | ≥ 1 | Consulter les logs de la tâche ; corriger ou relancer |
| **Fraîcheur** | ancienneté de la dernière ingestion réussie | > 24 h | Vérifier le scheduler Airflow et la connectivité |

> Les seuils sont un **point de départ** à ajuster selon l'historique réel des runs.

---

## 3. Mécanismes déjà en place (sur lesquels s'appuie le monitoring)

- **Journalisation (logging)** : chaque étape écrit dans `logs/extraction.log` et dans les logs Airflow
  (horodatage, volumes, statut API, qualité image, base cible). Base du diagnostic.
- **Repli gracieux** : si News API échoue/renvoie vide → bascule sur le jeu de secours ; si PostgreSQL est
  indisponible → bascule sur SQLite. Le flux **ne casse pas**, mais ces bascules sont **loggées** et suivies
  via le KPI « % source de repli ».
- **Retries Airflow** : chaque tâche est configurée avec `retries=1` (rejoue automatiquement une fois avant
  de déclarer un échec).
- **Validation d'image** : chaque entrée porte `image_quality` (`ok`/`unreachable`/`invalid`/`no_image`),
  ce qui alimente directement les KPI qualité.
- **Tableau de bord** (`05_dashboard/app.py`) : visualise en continu précision, rapidité et volume.

---

## 4. Fréquence des vérifications

| Quoi | Fréquence | Comment |
|---|---|---|
| Exécution du flux ETL | quotidienne (ou selon besoin métier) | Airflow (schedule) |
| Lecture du tableau de bord KPI | quotidienne | `streamlit run 05_dashboard/app.py` |
| Revue des logs d'échec | à chaque `failed` (temps réel) | UI Airflow → Logs |
| Revue des seuils d'alerte | mensuelle | ajustement selon l'historique |
| Contrôle qualité approfondi (échantillon) | hebdomadaire | inspection manuelle d'un échantillon |

---

## 5. Gestion des erreurs et escalade

1. **Niveau 1 — automatique** : retry Airflow + repli gracieux. La plupart des incidents transitoires se
   résolvent sans intervention.
2. **Niveau 2 — alerte** : si un seuil est franchi (section 2), une alerte est levée (email / message via un
   callback Airflow `on_failure_callback`, ou une règle sur les logs). L'ingénieur data consulte les logs.
3. **Niveau 3 — intervention** : diagnostic ciblé (API en panne ? quota épuisé ? source déplacée ?),
   correctif, puis relance du run concerné.

> **Principe :** on ne masque jamais une panne. Le repli garde le flux vivant, **mais** l'événement est tracé
> et remonté, pour ne pas livrer silencieusement des données dégradées au modèle.

---

## 6. Améliorations futures

- Brancher une **alerte automatique** (email/Slack) via `on_failure_callback` Airflow sur les seuils.
- Historiser les métriques de chaque run (déjà amorcé avec `run_metrics.json`) dans une table dédiée pour
  suivre les **tendances** dans le temps.
- Ajouter un **contrôle de dérive** (drift) sur la distribution des sources et des labels quand la
  labellisation sera en place.
