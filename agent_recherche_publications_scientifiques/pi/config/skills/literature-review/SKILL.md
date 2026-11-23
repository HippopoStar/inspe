---
name: literature-review
description: Constitue une sélection de publications scientifiques sur un thème (HAL, TEL, DUMAS, OpenAlex, Crossref, Cairn, Persée, OpenEdition, JSTOR, Taylor & Francis, ERIC, DOAJ, CORE, Semantic Scholar, et Springer, Scopus, Web of Science si une clé est fournie), classée par pertinence et nombre de citations, avec PDF et export Zotero (selection.ris).
---

# Sélection de publications sur un thème

**Règle stricte** : une seule commande fait tout (recherche, notation, PDF, export). Ne lis pas `metadata.json`, n'écris aucun script.

**Langue** : le français et l'anglais conviennent toujours tous les deux. Donne toujours des requêtes dans les deux langues (la commande l'exige) et ne cherche jamais à filtrer ou à préférer une langue.

## 1. Prépare la commande (sans longue réflexion)

- `<dossier>` : nom court du thème en minuscules, ex. `didactique_informatique`.
- `--topic` : le sujet de l'utilisateur en une phrase.
- `--fr` : 2 ou 3 requêtes courtes de mots-clés en français (pas la phrase de l'utilisateur).
- `--en` : les mêmes idées en anglais, 2 ou 3 requêtes.
  Exemple pour « méthodes pour enseigner l'informatique » :
  `--fr "didactique de l'informatique" "enseignement de la programmation" "pensée informatique école"`
  `--en "computing education pedagogy" "teaching programming novices"`
- `--sources` selon le domaine (les bases sans clé fournie sont ignorées automatiquement) :
  * SHS / francophone : `hal tel dumas cairn persee openedition openalex`
  * Sciences de l'éducation : `hal tel dumas eric cairn openalex`
  * Informatique / sciences dures : `openalex semanticscholar core springer scopus wos`
  * Généraliste ou doute : `all` (toutes les bases accessibles, plus long)

## 2. Lance-la

```bash
python3 /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py review \
  --dir "/workspace/<dossier>" \
  --topic "<sujet en une phrase>" \
  --fr "<requête 1>" "<requête 2>" \
  --en "<query 1>" "<query 2>" \
  --sources <sources>
```

## 3. Réponds

Recopie tel quel le tableau affiché à la fin (toutes les lignes), puis indique :
- `/workspace/<dossier>/selection.ris` à importer dans Zotero (Fichier > Importer) ;
- `/workspace/<dossier>/pdfs/` à charger dans une collection Knowledge d'Open WebUI ;
- les PDF marqués `[lien]` sont à télécharger à la main (HAL bloque les robots).

Si l'utilisateur veut plus ou moins de résultats, relance avec `--max-results` (défaut 10) ou `--min-relevance` (défaut 2).
Pour savoir quelles bases sont accessibles : `search_manager.py sources --check`.
