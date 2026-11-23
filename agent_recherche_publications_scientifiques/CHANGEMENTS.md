# Changements de la branche `feat/selection-zotero`

Objectif retenu :
- **Pi** constitue une sélection de publications sur un thème, classée par pertinence et par nombre de citations, exportable dans Zotero.
- **Open WebUI** permet de parcourir ces publications et d'interroger un agent sur leur contenu.
- Le tout sans perdre de temps sur du travail inutile, sur un HP Victus (Ryzen 5 5600H, RTX 3050 Mobile 4 Go, 16 Go de RAM).

## Ce qui n'allait pas (constaté dans le journal de session du 23/11)

| Problème | Effet mesuré |
|---|---|
| qwen3:4b en mode « réflexion » | ~6 000 tokens de réflexion pour une commande et une liste : 8 min 30 pour une recherche qui prend 2,4 s |
| ~12-13 tokens/s | trop lent pour un 4B sur RTX 3050 (≈ 40 attendu) : le modèle débordait probablement sur le CPU (contexte 16k) |
| Le LLM lisait tout `metadata.json` pour le reformater | un tour complet (~4 min) ; et il n'a affiché que 5 articles sur 15, dans l'ordre du fichier |
| La phrase de l'utilisateur envoyée telle quelle comme requête, en français seulement | environ la moitié des 15 résultats hors sujet |
| Aucune note de pertinence, aucun nombre de citations | impossible de classer |
| Notices incomplètes pour Zotero (pas de type, revue, volume, pages ; auteurs coupés à 5 ; résumé coupé à 700 caractères) | export Zotero impossible proprement |
| Les PDF étaient téléchargés mais jamais lus (pypdf installé, inutilisé) | la « synthèse » se basait sur des bouts de résumés |
| OpenAlex exige une clé API depuis le 13/02/2026 | quota fortement réduit sans clé |
| Liens « PDF » qui n'en sont pas (`oa_url` d'OpenAlex = page d'accueil ou doi.org ; `url` d'ERIC = page éditeur) | mauvais choix des articles « avec PDF » |
| Open WebUI : le dossier `workspace` monté n'est pas indexé ; modèle d'embedding par défaut anglais seulement | recherche dans les PDF français médiocre |

## Les changements, fichier par fichier

### `compose.yml`
- `OLLAMA_CONTEXT_LENGTH=8192` et `OLLAMA_KV_CACHE_TYPE=q8_0` (au lieu de 16384 / q4_0).
  **Pourquoi** : 16k + q4_0 ne tenait pas entièrement dans 4 Go et q4_0 dégrade la qualité. 8k + q8_0 ≈ 3,1 Go pour qwen3:4b.
  **À vérifier** : `docker exec ollama ollama ps` pendant une réponse doit afficher `100% GPU`.
- Open WebUI : `RAG_EMBEDDING_MODEL=BAAI/bge-m3`.
  **Pourquoi** : le défaut (`all-MiniLM-L6-v2`) ne comprend que l'anglais. bge-m3 est multilingue et tourne sur CPU (la VRAM reste au LLM). Réindexer après le changement.
- Service `pi` : `OLLAMA_HOST`, `RANK_MODEL`, `OPENALEX_API_KEY`, `S2_API_KEY` (lus depuis un fichier `.env`). L'ancienne variable `OLLAMA_BASE_URL` n'était utilisée par rien.

### `pi/config/models.json` et `pi/config/AGENTS.md`
- qwen3:4b passe en `"reasoning": false` et `/no_think` est ajouté en tête de `AGENTS.md` (interrupteur reconnu par Qwen3).
  **Pourquoi** : la réflexion représentait ~90 % du temps de la session.
- `qwen2.5-coder:3b` retiré : modèle de code, faible en synthèse française.
- `contextWindow` à 8192 pour rester cohérent avec Ollama.

### `pi/Dockerfile`
- Seul `requests` reste installé. `arxiv`, `beautifulsoup4` et `pypdf` n'étaient utilisés par aucun script. La lecture des PDF est faite par Open WebUI.

### `start-pi.sh`
- Le bouton Annuler du menu fonctionne.
  **Pourquoi** : avec `set -e`, le script s'arrêtait avant d'atteindre le test `if [ $? -ne 0 ]`.

### `scripts/utils.py` et `scripts/providers/*.py`
- Chaque notice contient maintenant :
  - les champs Zotero : `type` (code RIS : JOUR, THES, CHAP, BOOK, CONF, RPRT, GEN), `container` (revue/livre), `volume`, `issue`, `pages`, `language`, `url` ;
  - `cited_by` (nombre de citations) et `citation_percentile` ;
  - la liste complète des auteurs et le résumé complet.
- OpenAlex et Semantic Scholar lisent leur clé API dans l'environnement.
- `pdf_url` ne contient plus que de vrais liens PDF : fallback `oa_url` supprimé côté OpenAlex, `url` d'ERIC déplacée dans `url`.

### `scripts/search_manager.py` (le cœur du changement)
Une commande `review` fait tout, pour que Pi n'ait qu'**un seul appel d'outil** à faire :
1. **Recherche** : plusieurs requêtes (FR + EN) sur les bases choisies.
2. **Fusion des doublons** par DOI *ou* titre ; les champs manquants sont complétés par l'autre notice (avant, l'abstract pouvait être perdu).
3. **Citations** : pour toute notice avec DOI, OpenAlex fournit le nombre de citations et le *percentile normalisé* (corrigé de l'âge et du domaine).
   **Pourquoi une seule source** : les chiffres de bases différentes ne sont pas comparables.
4. **Pertinence** : chaque titre + résumé est noté de 0 à 3 par le LLM. Le script appelle directement l'API native d'Ollama (`think: false`, réponse JSON imposée), une note courte par article, sans boucle d'agent.
5. **Classement** : pertinence, puis percentile, puis citations brutes. Une valeur inconnue passe après les valeurs connues, mais s'affiche `?` et non 0 : les publications HAL sans DOI n'ont souvent aucune donnée de citation.
6. **PDF** des publications retenues (pertinence ≥ 2 par défaut).
7. **Export** :
   - `selection.ris`, à importer dans Zotero (Fichier > Importer). Les PDF téléchargés sont joints via `L1`, et la note contient pertinence et citations.
   - `SELECTION.md`, le tableau complet, que Pi recopie tel quel.

Les étapes restent disponibles séparément : `search`, `rank`, `download`, `export` (`--help`).

### `skills/literature-review/SKILL.md`
- Réécrit pour que le LLM ne fasse que ce qui demande du jugement :
  - transformer le sujet en 3 à 5 requêtes de mots-clés FR + EN ;
  - choisir les bases ;
  - lancer `review` ;
  - recopier le tableau.
- Interdiction explicite de lire `metadata.json` ou d'écrire des scripts.

### `scripts/test_search_manager.py` (nouveau)
- Test hors ligne : fusion des doublons, lecture des notes, ordre de classement, contenu du RIS et du tableau. Lancer : `python3 test_search_manager.py`.

### `README.md` et `.gitignore`
- Clés API dans `.env` (ignoré par git), vérification GPU, description des fichiers produits, marche à suivre pour charger les PDF dans une collection Open WebUI.

## Résultats du test réel (23/11, sans clé API, sans Ollama)

- Recherche sur les 6 bases, 2 requêtes : 48 notices uniques, 6 doublons fusionnés. Champs Zotero bien remplis pour HAL, OpenAlex, Crossref et DOAJ ; ERIC sans volume ni pages.
- Le `.ris` produit est complet (type, auteurs « Nom, Prénom », revue, volume, numéro, pages, DOI, résumé).
- **Semantic Scholar** renvoie des erreurs 429 sans clé : demander une clé gratuite.
- **HAL** protège maintenant ses fichiers par une page anti-robot : le script ne peut pas télécharger ces PDF. Il l'indique (`BLOQUÉ (anti-robot)`) et `SELECTION.md` donne le lien pour les télécharger à la main.
- Les liens « fulltext » de DOAJ sont souvent des pages HTML : rejetés automatiquement.
- Le percentile OpenAlex vaut parfois 0 % pour de vieux articles pourtant cités (ex. 1990, 18 citations) : regarder aussi la colonne Citations.
- **Non testé** : la notation par le LLM (Ollama n'était pas lancé) et l'import réel dans Zotero.

## Limites connues

- Noms de famille composés sans virgule (« Djeumeni Tchamabe ») mal coupés dans le RIS : à corriger dans Zotero.
- L'année HAL peut être la date de dépôt et non de première publication.
- Les PDF scannés n'ont pas de texte : vides dans Open WebUI sans OCR.
- Un modèle 4B répond bien sur un passage précis, mal sur « compare tous les articles ».
- Avec 16 Go de RAM (dont ~7 déjà utilisés), pas de place pour un modèle plus gros réparti GPU/CPU.
