---
name: literature-review
description: Recherche des articles scientifiques en français et anglais sur HAL, OpenAlex (Persée, OpenEdition, Cairn), Semantic Scholar, Crossref, ERIC et DOAJ via l'orchestrateur modulaire search_manager.py, télécharge les PDF et rédige une synthèse.
---

# Procédure de revue de littérature multi-bases

**Règle stricte** : Utilise exclusivement l'orchestrateur persistant `/home/node/.pi/agent/skills/literature-review/scripts/search_manager.py`. N'écris pas de nouveau script de scraping.

## Choix des sources selon la demande
* **Recherche francophone / SHS (inclut HAL, Persée, OpenEdition, Cairn)** : `--sources hal openalex --lang fr`
* **Recherche internationale généraliste** : `--sources openalex crossref doaj`
* **Informatique / IA / Sciences dures** : `--sources semanticscholar openalex`
* **Sciences de l'éducation** : `--sources eric openalex`

## Étapes d'exécution

1. **Collecte des métadonnées** :
   ```bash
   python3 /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py search \
     --query "<mots-clés>" \
     --sources <sources_choisies> \
     --max-results 8 \
     --out "/workspace/<dossier_theme>/metadata.json"
   ```

2. **Filtrage et téléchargement des PDF** :
   - Lis `/workspace/<dossier_theme>/metadata.json`.
   - Sélectionne les 3 à 6 articles les plus pertinents (en privilégiant ceux ayant un `pdf_url` non vide).
   - Télécharge-les via leurs identifiants complets (`id`, ex. `hal:hal-0123456` ou `openalex:W12345678`) :
     ```bash
     python3 /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py download \
       --meta "/workspace/<dossier_theme>/metadata.json" \
       --ids "<id1>" "<id2>" "<id3>" \
       --dir "/workspace/<dossier_theme>/pdfs"
     ```

3. **Rédaction de la synthèse (`SYNTHESE.md`)** :
   - Crée `/workspace/<dossier_theme>/SYNTHESE.md` avec pour chaque article retenu : **Titre, Auteurs, Année, Base source, DOI**, nom du fichier PDF local (`suggested_filename`), problématique et résultats clés, suivi d'un **tableau comparatif**.

