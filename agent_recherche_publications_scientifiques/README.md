# Agent de recherche de publications scientifiques

- **Pi** constitue une sélection de publications sur un thème, classée par pertinence et par citations, exportable dans Zotero.
- **Open WebUI** permet d'interroger un agent sur le contenu des PDF retenus.

Tout tourne en local (Ollama), réglé pour un GPU de 4 Go (RTX 3050).

## Installation

1. **GPU dans Docker** ([NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)) :
   ```
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
     && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
       sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
       sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get -y install nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
   docker run --rm --gpus all --entrypoint "" ollama/ollama nvidia-smi
   ```
2. **Clés API** (facultatives) : voir [secrets/README.md](secrets/README.md). La clé OpenAlex est fortement recommandée.
3. **Services et modèles** :
   ```
   docker compose up -d
   docker exec ollama ollama pull qwen3:4b-instruct   # modèle par défaut (sans réflexion) ; autres choix dans pi/config/models.json
   docker compose build pi
   ```

## Utilisation

```
./start-pi.sh -p "Constitue une sélection de publications sur les méthodes pour enseigner l'informatique"
```

Pi lance une seule commande (`search_manager.py review`, voir [SKILL.md](pi/config/skills/literature-review/SKILL.md)). Elle :
1. interroge les bases en français et en anglais, et ajoute les travaux les plus cités portant le concept central (`--core`) dans leur titre ;
2. fusionne les doublons ;
3. complète citations et PDF légaux via OpenAlex ;
4. note chaque résumé de 0 à 3 avec le LLM ;
   puis retrouve par leur titre dans OpenAlex les notices pertinentes sans DOI (ERIC), pour leurs citations ;
   puis ajoute (`--snowball`, 10 au plus) les travaux cités par au moins 3 notices pertinentes, qu'il note à leur tour : ce sont souvent les classiques du sujet, et la colonne « Ajouté car » du tableau dit par combien de notices ils sont cités ;
5. retient les 20 mieux classées de pertinence ≥ 2 (`--top`, `--min-relevance`) ;
6. écrit dans `workspace/AAAA-MM-JJ_HH-MM_<thème>/` (une recherche n'écrase jamais la précédente). Aucun PDF n'est téléchargé : seuls les liens sont donnés.

| Fichier | Contenu |
|---|---|
| `SELECTION.md` | tableau classé par score = pertinence (0-3) + percentile de citations (0-1) (corrigé de l'âge et du domaine), puis citations. `?` = inconnu, pas zéro. Colonne PDF : `[lien]` vers le PDF en accès libre |
| `selection.ris` | à importer dans Zotero (Fichier > Importer) ; le lien PDF est dans la note de chaque notice |
| `metadata.json` | toutes les notices, y compris celles écartées |

Le poids des citations se règle avec `--citation-weight` (1 par défaut : une notice notée 2 ne passe jamais devant une notée 3 ; au-delà, une 2 très citée le peut ; 0 = pertinence seule). Il ne fait jamais entrer une notice sous `--min-relevance`.

Vérifications :
- Pendant une réponse, `docker exec ollama ollama ps` doit afficher `100% GPU`.
- Test hors ligne : `python3 pi/config/skills/literature-review/scripts/test_search_manager.py`.

## Interroger les PDF dans Open WebUI (<http://localhost:3000>)

1. Télécharger à la main les PDF voulus depuis les liens de `SELECTION.md`. Espace de travail > Connaissances : une collection par thème, y téléverser ces PDF et `SELECTION.md`.
2. Dans une discussion, `#` puis la collection. Les réponses citent leurs passages : les vérifier.

Limites :
- Les PDF scannés n'ont pas de texte : ils restent vides sans OCR.
- Un modèle 4B répond bien sur un passage précis, mal sur « compare tous les articles ».

## Organisation du code (`pi/config/skills/literature-review/scripts/`)

| Fichier | Rôle |
|---|---|
| `search_manager.py` | ligne de commande : `review`, `search`, `rank`, `export`, `sources` |
| `search.py` | étape 1 : bases -> notices, doublons, complément OpenAlex |
| `snowball.py` | étape 1b : travaux cités par plusieurs notices pertinentes (références OpenAlex) |
| `rank.py` | étape 2 : note de pertinence par le LLM, classement |
| `export.py` | étape 3 : `selection.ris` et `SELECTION.md` |
| `records.py` | format commun d'une notice, fusion des doublons |
| `net.py` | session HTTP (délai, nouvelles tentatives), lecture des clés |
| `providers/` | un module par base + registre `__init__.py` |

Ajouter une base : écrire `providers/<base>.py` avec `search(query, max_results, lang)` qui renvoie des `make_record(...)`, puis l'inscrire dans `providers/__init__.py`.

Historique et raisons des choix : [CHANGEMENTS.md](CHANGEMENTS.md).
