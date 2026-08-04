# Rapport d'exploration de sources de données multimodales
### Projet CheckIt.AI — Pipeline d'acquisition de données pour un détecteur de fake news

**Livrable 1 — Étape 1 de la mission**
**Modalités ciblées :** texte + image (données multimodales)
**Date :** 2026-08-04

---

## 1. Objectif et cadrage

CheckIt.AI souhaite constituer un corpus **multimodal (texte + image)** de publications d'actualité pour entraîner un
détecteur automatique de désinformation. Ce rapport identifie et compare des sources exploitables, précise leurs
caractéristiques (format, langue, modalités, qualité des labels, droits d'usage) et propose pour chacune une **méthode
d'extraction**. Il fixe aussi les **champs indispensables** d'une publication et le **format de sortie** retenu.

Deux familles de sources sont distinguées, car elles ne servent pas le même but :

- **A. Sources d'acquisition « en flux »** (APIs officielles, flux RSS, réseaux sociaux) : elles fournissent des
  publications récentes, réelles, mais **sans étiquette vrai/faux**. Le label devra être **dérivé faiblement** (p. ex.
  par la fiabilité de la source) ou ajouté ultérieurement.
- **B. Jeux de données de référence labellisés** (datasets académiques) : ils fournissent la **vérité terrain**
  (vrai/faux) nécessaire à l'apprentissage supervisé, avec des images déjà associées au texte.

> **Principe méthodologique retenu :** on privilégie les **canaux officiels** (APIs, flux RSS, datasets sous licence
> claire) et on n'utilise le scraping HTML qu'en dernier recours, uniquement là où les conditions d'utilisation du site
> l'autorisent.

---

## 2. Distinction fondamentale : opinion controversée ≠ désinformation

Ce point conditionne toute la stratégie de labellisation et doit être posé avant d'extraire quoi que ce soit.

- **Opinion controversée** : un point de vue, un jugement de valeur qui divise. Il est **subjectif**, relève de la
  liberté d'expression, et n'est **pas falsifiable** objectivement (« ce film est mauvais », « telle politique est
  injuste »). Une opinion **n'est pas** une fake news, même si elle choque.
- **Désinformation** : une information **objectivement fausse**, diffusée pour tromper ou manipuler. Elle porte sur des
  faits **vérifiables** (« ce vaccin contient une puce », une image truquée présentée comme réelle).

**Conséquence pour l'extraction :** le corpus doit privilégier des contenus dont la **véracité factuelle est
vérifiable**. On ne cherchera pas à étiqueter des tribunes d'opinion comme « faux », et on préférera des labels issus de
**fact-checkers** (vérificateurs de faits) plutôt que de simples jugements de popularité.

---

## 3. Champs indispensables d'une publication

Pour qu'une entrée soit exploitable par un modèle multimodal, elle doit **impérativement** contenir :

| Champ | Rôle | Obligatoire |
|---|---|---|
| `id` | Identifiant unique de l'entrée | ✅ |
| `title` / `text` / `content` | Contenu textuel (modalité texte, pour le NLP) | ✅ |
| `image_urls` | Lien(s) vers l'image (modalité image) | ✅ |
| `published_at` | Date de publication (fraîcheur, tri, dédoublonnage) | ✅ |

Champs **secondaires mais très utiles** (à ne pas négliger) :

| Champ | Rôle |
|---|---|
| `url` | Lien source (traçabilité, dédoublonnage) |
| `source_name` / `domain` | Nom de domaine → sert au **label faible** par fiabilité |
| `language`, `country` | Filtrage, cohérence linguistique |
| `category` | Segmentation (politique, santé…) |
| `label`, `label_source`, `confidence` | Étiquette vrai/faux, sa provenance et sa fiabilité |
| `has_image`, `image_quality` | Contrôle qualité de la modalité image |

> **Point de vigilance — association texte/image :** chaque enregistrement doit lier le texte **et son image dans la
> même entrée**. Une publication sans image accessible (lien mort, format non image, vignette générique) n'est **pas**
> multimodale et devra être écartée ou marquée à l'étape de validation.

---

## 4. Sources identifiées

### Famille A — Acquisition en flux (non labellisées / label faible)

#### A1. News API — `newsapi.org` *(source déjà amorcée dans le projet)*
- **Modalités :** texte (`title`, `description`, `content`) + image (`urlToImage`).
- **Format / accès :** API REST, réponse **JSON**. Extraction via `requests` (Python).
- **Langues :** 14 langues, 55 pays (dont le français).
- **Labels :** ❌ aucun label vrai/faux → label faible à dériver par domaine de confiance.
- **Droits d'usage :** clé API gratuite (≈ 1 000 requêtes/jour) ; attribution « Powered by News API » demandée ; sur
  l'offre gratuite le contenu est **tronqué (~200 caractères)** et **différé de 24 h**.
- **⚠️ Limite majeure constatée :** l'endpoint `top-headlines?country=fr` renvoie fréquemment **0 résultat**
  (couverture « une par pays » devenue très incomplète). **Décision : basculer sur l'endpoint `/everything`**
  (recherche par mots-clés + `language=fr`), nettement plus fiable et qui renvoie bien les URLs d'images.

#### A2. NewsData.io — `newsdata.io` *(cité dans les ressources de la mission)*
- **Modalités :** texte + image (`image_url`).
- **Format / accès :** API REST **JSON** (export CSV/Excel possible). Client Python officiel `newsdataapi`.
- **Langues :** 80+ langues, très large couverture pays.
- **Labels :** ❌ aucun label vrai/faux ; propose en revanche des **datasets thématiques gratuits** sous licence
  **CC BY 4.0** (annotations tag/région/sentiment).
- **Droits d'usage :** offre gratuite ≈ 200 crédits/jour (~2 000 articles), **usage commercial autorisé** ; mais
  contenu **tronqué** et **différé de 12 h** sur le plan gratuit.
- **Intérêt :** excellente **alternative/complément** à News API pour diversifier les sources et réduire la dépendance
  à un seul fournisseur.

#### A3. The Guardian Open Platform — `open-platform.theguardian.com` *(recommandation robustesse)*
- **Modalités :** texte (article complet accessible sur ce plan) + image (via `fields=thumbnail`/`main`).
- **Format / accès :** API REST **JSON**. Extraction via `requests`.
- **Langues :** anglais.
- **Labels :** ❌ pas de label vrai/faux, mais **source de haute fiabilité** → excellente pour alimenter la **classe
  « vrai / fiable »** d'un jeu faiblement labellisé.
- **Droits d'usage :** clé gratuite avec **quota très généreux (~5 000 appels/jour)**, attribution requise.
- **Intérêt :** de loin l'API la plus **stable et généreuse** testée pour ce projet → **candidate n°1 comme source
  d'acquisition principale**, avec News API/NewsData.io en secours.

#### A4. Reddit API (via PRAW) — sous-reddits d'actualité
- **Modalités :** texte (`title`, `selftext`) + image (`url` du post).
- **Format / accès :** API REST **JSON**, wrapper Python **PRAW**. Nécessite un compte développeur Reddit
  (identifiants OAuth : `client_id`, `client_secret`).
- **Langues :** majoritairement anglais.
- **Labels :** ❌ pas de label intrinsèque, mais la **supervision distante par sous-reddit** (cf. Fakeddit, §B1) permet
  d'en dériver.
- **Droits d'usage :** API gratuite soumise à quotas et aux conditions d'utilisation de Reddit.
- **Intérêt :** capture la désinformation **telle qu'elle circule socialement** (image + texte), utile pour la
  robustesse du modèle.

#### A5. Flux RSS — Le Monde, France 24, BBC, Reuters, AP…
- **Modalités :** texte (`title`, `summary`) + image (souvent dans `media:content` / `enclosure`).
- **Format / accès :** **XML** (format RSS/Atom). Extraction via la librairie **`feedparser`**.
- **Langues :** multilingue selon les flux choisis (FR + EN).
- **Labels :** ❌ aucun ; label faible par **fiabilité du média** (domaine de confiance).
- **Droits d'usage :** flux **officiels et publics**, pensés pour la rediffusion → **canal privilégié** et sans clé API.
- **Intérêt :** repli gratuit et sans quota ; parfait comme **filet de sécurité** quand les APIs sont indisponibles.

### Famille B — Jeux de données de référence labellisés (vérité terrain)

#### B1. Fakeddit — `github.com/entitize/Fakeddit` *(recommandation n°1 pour la vérité terrain)*
- **Modalités :** **texte + image** (réellement multimodal), + métadonnées et commentaires.
- **Format / accès :** métadonnées en **TSV**, images téléchargeables via les URLs fournies.
- **Volume / langue :** **> 1 million d'échantillons**, anglais, issus de Reddit (2008–2019).
- **Labels :** ✅ **2-way** (vrai/faux), **3-way** et **6-way** (vrai, satire/parodie, contenu trompeur, contenu
  manipulé, fausse association, imposture). Labels par **supervision distante** (fiabilité moyenne, mais massive).
- **Droits d'usage :** dataset public **à usage recherche** ; ses consignes demandent de n'utiliser que certaines
  colonnes du fichier public (`clean_title`, `6_way_label`) → **à respecter**.
- **Intérêt :** le meilleur compromis **taille × multimodalité × granularité des labels** pour l'entraînement supervisé.

#### B2. FakeNewsNet (PolitiFact + GossipCop) — `github.com/KaiDMML/FakeNewsNet`
- **Modalités :** contenu d'article (texte + images) + contexte social + spatio-temporel.
- **Format / accès :** **scripts de collecte** fournis (Python), sortie **JSON/CSV**.
- **Volume / langue :** anglais ; deux sous-ensembles (politique / divertissement).
- **Labels :** ✅ **binaire vrai/faux**, adossé à des **fact-checkers** (PolitiFact, GossipCop) → **fiabilité de label
  élevée**.
- **Droits d'usage :** cadre **académique** ; la reconstitution du contexte social peut nécessiter des accès tiers
  (historiquement l'API Twitter/X), mais le contenu texte+image des articles reste exploitable.
- **Intérêt :** complément qualitatif à Fakeddit — **labels de meilleure qualité** (fact-checkés) mais volume plus
  réduit.

#### B3. Pistes complémentaires (à connaître, non retenues en priorité)
- **Kaggle / Hugging Face Datasets :** nombreux jeux « fake news », mais **souvent texte seul** (ex. LIAR, ISOT/
  « Fake and Real News »). À filtrer soigneusement : ne retenir que les jeux **avec images** pour le multimodal.
- **GDELT Project :** base d'actualité mondiale **gratuite et quasi illimitée**, mais **brute** (ingénierie de données
  nécessaire) — pertinente à plus grande échelle.
- **Google Dataset Search / `public-apis.io` :** moteurs de découverte utiles pour sourcer d'autres candidats.

---

## 5. Tableau de synthèse comparatif

| Source | Type | Modalités | Format | Langue | Labels (qualité) | Extraction | Droits |
|---|---|---|---|---|---|---|---|
| **News API** | API flux | Texte + image | JSON | FR/EN + | ❌ (faible via domaine) | `requests` | Gratuit, attribution, différé 24 h |
| **NewsData.io** | API flux | Texte + image | JSON/CSV | 80+ | ❌ (faible) | `requests`/`newsdataapi` | Gratuit, commercial OK, différé 12 h |
| **The Guardian** | API flux | Texte + image | JSON | EN | ❌ (classe « fiable ») | `requests` | Gratuit ~5000/j, attribution |
| **Reddit (PRAW)** | API sociale | Texte + image | JSON | EN | ❌ (distante) | `praw` | Gratuit, OAuth, quotas |
| **Flux RSS** | Flux officiel | Texte + image | XML | FR/EN | ❌ (faible via média) | `feedparser` | Public, sans clé |
| **Fakeddit** | Dataset | Texte + image | TSV + images | EN | ✅ 2/3/6-way (distante) | Téléchargement | Recherche, colonnes restreintes |
| **FakeNewsNet** | Dataset | Texte + image | JSON/CSV | EN | ✅ binaire (fact-check) | Scripts fournis | Académique |

---

## 6. Format de sortie retenu

Une architecture **en deux couches** est adoptée pour concilier fidélité et exploitabilité :

- **Couche `raw` (données brutes) → JSON.** Semi-structuré, il colle à la forme native des APIs, préserve tous les
  champs et reste lisible pour le débogage. C'est déjà le choix du projet (`data/raw/*.json`).
- **Couche `processed` (données nettoyées) → Parquet** (avec **CSV** en export lisible de secours). Le Parquet est
  **typé, compressé et orienté colonnes** : idéal pour l'analytique et l'entraînement ML, et bien plus efficace que le
  CSV sur de gros volumes. Le CSV reste proposé pour l'inspection humaine et la compatibilité tableur.

> **Justification :** JSON pour **ingérer sans perte**, Parquet pour **exploiter efficacement**. Cette séparation
> raw/processed rendra le pipeline de transformation (livrable 3) **reproductible** et **rejouable**.

---

## 7. Droits d'usage et fiabilité des labels — synthèse

- **Droits :** privilégier les **canaux officiels** (APIs avec clé, flux RSS publics, datasets sous licence explicite).
  Respecter les **attributions** (News API, Guardian) et les **restrictions de colonnes** (Fakeddit). Éviter le scraping
  HTML sauf autorisation.
- **Fiabilité des labels (du plus fort au plus faible) :**
  1. **Fact-checkers** (FakeNewsNet / PolitiFact) → label fort, faible volume.
  2. **Supervision distante** (Fakeddit, sous-reddits) → label moyen, gros volume.
  3. **Fiabilité de la source / domaine** (APIs de flux, RSS) → label faible, à utiliser comme signal, pas comme
     vérité absolue.

---

## 8. Stratégie recommandée pour CheckIt.AI

1. **Vérité terrain (apprentissage supervisé) :** s'appuyer sur **Fakeddit** (principal, multimodal + volumineux +
   labels granulaires) complété par **FakeNewsNet** (labels fact-checkés de meilleure qualité).
2. **Acquisition « fraîche » multimodale (flux réel) :** **The Guardian** en source principale (la plus stable),
   **News API `/everything`** et **NewsData.io** en compléments, **flux RSS** en repli — le tout **faiblement
   labellisé** par fiabilité de domaine, en attendant une labellisation dédiée.
3. **Champs et validation :** imposer le quadruplet **texte + image + date + source**, et **valider l'association
   texte/image** à l'ingestion (image accessible et de format valide).

### Décisions d'architecture (à retenir pour la soutenance)

- **AD-1 — Endpoint fiable :** utiliser `/everything` (et non `top-headlines?country=fr`, qui renvoie 0 résultat) pour
  News API.
- **AD-2 — Anti-dépendance / repli gracieux :** chaîner plusieurs sources (Guardian → News API → NewsData.io → RSS) pour
  qu'une **indisponibilité d'un service ne fasse jamais tomber la démo**.
- **AD-3 — Séparation des flux :** distinguer l'**ingestion de vérité terrain** (datasets labellisés) de l'**acquisition
  temps réel** (APIs/RSS), qui n'ont ni la même fraîcheur ni la même qualité de label.
- **AD-4 — Deux couches de stockage :** `raw` immuable en JSON, `processed` typé en Parquet/CSV.

---

## 9. Prochaine étape

Livrable 2 — **scripts d'extraction automatisée** : fiabiliser l'extraction (application de **AD-1** et **AD-2**),
structurer le code en fonctions (connexion, parsing, nettoyage, sauvegarde), ajouter logs et gestion d'erreurs, et
garantir un **repli gracieux** vérifiable même sans clé API.
