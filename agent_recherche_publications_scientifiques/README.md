
<https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>  
<https://docs.nvidia.com/aerial/framework/latest/installation/docker_and_nvidia_setup.html>  
```
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get -y install nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all --entrypoint "" ollama/ollama nvidia-smi
```

**Clés API (facultatives, gratuites)**  
Un fichier par clé dans `secrets/` (ignoré par git), monté dans `/run/secrets` du conteneur `pi`. La liste, l'effet de chaque clé et où l'obtenir sont dans [secrets/README.md](secrets/README.md). La clé OpenAlex est fortement recommandée (elle sert aussi aux citations de toutes les bases).

Bases accessibles selon les clés fournies (avec une vraie requête de test par base) :
```
docker compose run --rm --entrypoint python3 pi \
  /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py sources --check
```

**Préparer l'arborescence et démarrer Ollama + Open WebUI**  
```
docker compose up -d
```

**Télécharger les modèles optimisés pour vos 4 Go de VRAM**  
```
docker exec -it ollama ollama pull qwen3:4b
docker exec -it ollama ollama pull gemma4:e2b
docker exec -it ollama ollama pull phi4-mini
docker exec -it ollama ollama pull ministral-3:3b
```

**Construire l'image de Pi et lancer une session interactive**  
```
docker compose build pi
docker compose run --rm pi --model ollama/qwen3:4b
# OU
./start-pi.sh -p "Constitue une sélection de publications sur les méthodes pour enseigner l'informatique"
```

Vérifier que le modèle tourne entièrement sur le GPU pendant une réponse (colonne PROCESSOR = `100% GPU`) :
```
docker exec ollama ollama ps
```

**Résultat d'une sélection** (`workspace/<thème>/`)  
- `SELECTION.md` : tableau classé par pertinence (0-3, notée par le LLM), puis percentile de citations (OpenAlex, corrigé de l'âge et du domaine), puis citations brutes. `?` = inconnu (fréquent pour HAL sans DOI), pas zéro.
- `selection.ris` : à importer dans Zotero (Fichier > Importer) ; les PDF téléchargés sont joints. Pour les publications avec DOI, la baguette magique de Zotero (« Ajouter un document par son identifiant ») récupère aussi des métadonnées complètes.
- `pdfs/` : PDF en accès libre des publications retenues. HAL protège ses fichiers par une page anti-robot : ces PDF-là sont à télécharger à la main (colonne PDF = `[lien]` dans `SELECTION.md`).
- `metadata.json` : toutes les notices, y compris celles écartées.

Commandes séparées si besoin : `search_manager.py search|rank|download|export --dir ...` (`--help`).  
Test hors ligne : `python3 pi/config/skills/literature-review/scripts/test_search_manager.py`

**Accéder à Open WebUI**  
<http://localhost:3000>  

**Interroger les publications dans Open WebUI**  
1. Espace de travail > Connaissances > nouvelle collection (une par thème).
2. Y téléverser le dossier `workspace/<thème>/pdfs/` et `SELECTION.md` (pour que l'agent connaisse auteurs, années et citations).
3. Dans une discussion, taper `#` puis choisir la collection (ou créer un Modèle avec la collection attachée). Les réponses citent les passages et les fichiers utilisés : toujours vérifier le passage cité.

Limites : les PDF scannés (vieux documents) n'ont pas de texte et restent vides sans OCR ; un modèle 4B répond bien sur un passage précis, mal sur « compare tous les articles ».

