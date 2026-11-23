FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir requests

# Préparation des répertoires pour l'utilisateur non-privilégié 'node' (UID 1000)
RUN mkdir -p /home/node/.npm-global /home/node/.pi/agent/skills /home/node/.pi/agent/sessions /workspace \
    && chown -R node:node /home/node /workspace

USER node
ENV HOME="/home/node"
ENV NPM_CONFIG_PREFIX="/home/node/.npm-global"
ENV PATH="/home/node/.npm-global/bin:/home/node/.pi/agent/bin:$PATH"

# Installation de Pi dans /home/node/.pi
RUN curl -fsSL https://pi.dev/install.sh | sh

WORKDIR /workspace
ENTRYPOINT ["pi"]

