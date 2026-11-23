
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

**Préparer l'arborescence et démarrer Ollama + Open WebUI**  
```
docker compose up -d
```

**Télécharger les modèles optimisés pour vos 4 Go de VRAM**  
```
docker exec -it ollama ollama pull qwen2.5-coder:3b
docker exec -it ollama ollama pull qwen3:4b
docker exec -it ollama ollama pull gemma4:e2b
docker exec -it ollama ollama pull phi4-mini
docker exec -it ollama ollama pull ministral-3:3b
```

**Construire l'image de Pi et lancer une session interactive**  
```
docker compose build pi
docker compose run --rm pi --model ollama/qwen2.5-coder:3b
# OU
./start-pi.sh -p "Fais une revue de littérature sur les GraphRAG récents"
```

**Accéder à Open WebUI**  
<http://localhost:3000>  

