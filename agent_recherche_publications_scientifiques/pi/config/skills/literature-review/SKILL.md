---
name: literature-review
description: Constitue une sélection de publications scientifiques sur un thème (HAL, OpenAlex, Semantic Scholar, Crossref, ERIC, DOAJ), classée par pertinence et nombre de citations, avec PDF et export Zotero (selection.ris).
---

# Sélection de publications sur un thème

**Règle stricte** : une seule commande fait tout (recherche, notation, PDF, export). Ne lis pas `metadata.json`, n'écris aucun script.

## 1. Prépare la commande (sans longue réflexion)

- `<dossier>` : nom court du thème en minuscules, ex. `didactique_informatique`.
- `--topic` : le sujet de l'utilisateur en une phrase.
- `--query` : 3 à 5 requêtes courtes de mots-clés (pas la phrase de l'utilisateur), en français ET en anglais, avec les termes du domaine. Exemple pour « méthodes pour enseigner l'informatique » :
  `"didactique de l'informatique" "enseignement de la programmation" "pensée informatique école" "computing education pedagogy" "teaching programming novices"`
- `--sources` selon le domaine :
  * SHS / francophone : `hal openalex`
  * Sciences de l'éducation : `hal eric openalex`
  * Informatique / sciences dures : `semanticscholar openalex`
  * Généraliste : `openalex crossref doaj`
- N'ajoute `--lang fr` que si l'utilisateur veut uniquement des textes en français.

## 2. Lance-la

```bash
python3 /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py review \
  --dir "/workspace/<dossier>" \
  --topic "<sujet en une phrase>" \
  --query "<requête 1>" "<requête 2>" "<requête 3>" \
  --sources <sources>
```

## 3. Réponds

Recopie tel quel le tableau affiché à la fin (toutes les lignes), puis indique :
- `/workspace/<dossier>/selection.ris` à importer dans Zotero (Fichier > Importer) ;
- `/workspace/<dossier>/pdfs/` à charger dans une collection Knowledge d'Open WebUI.

Si l'utilisateur veut plus ou moins de résultats, relance avec `--max-results` (défaut 10) ou `--min-relevance` (défaut 2).
