#!/usr/bin/env bash
set -e

# Se placer dans le répertoire du script (racine de ai-research-stack)
cd "$(dirname "${BASH_SOURCE}")"

MODELS_FILE="./pi/config/models.json"

# 1. Vérification des dépendances locales (jq + whiptail/dialog)
if ! command -v jq &> /dev/null; then
    echo "Erreur : 'jq' est requis (installez-le avec : sudo apt install jq)."
    exit 1
fi

if command -v whiptail &> /dev/null; then
    UI_TOOL="whiptail"
elif command -v dialog &> /dev/null; then
    UI_TOOL="dialog"
else
    echo "Erreur : installez 'whiptail' ou 'dialog' (ex: sudo apt install whiptail)."
    exit 1
fi

if [ ! -f "$MODELS_FILE" ]; then
    echo "Erreur : fichier introuvable ($MODELS_FILE)."
    exit 1
fi

# 2. Extraction dynamique des modèles depuis models.json via jq
# Format généré pour whiptail : "provider/model_id" "Nom affiché"
MENU_ITEMS=()
while IFS= read -r line; do
    MENU_ITEMS+=("$line")
done < <(jq -r '
  .providers | to_entries[] |
  .key as $provider |
  .value.models[] |
  "\($provider)/\(.id)", "\(.name)"
' "$MODELS_FILE")

# Ajout d'une option par défaut en fin de liste
MENU_ITEMS+=("default" "Dernier modèle utilisé (défaut Pi)")

# Calcul dynamique de la hauteur de la fenêtre selon le nombre de modèles
NUM_MODELS=$(( ${#MENU_ITEMS[@]} / 2 ))
MENU_HEIGHT=$(( NUM_MODELS + 7 ))

# 3. Affichage du menu interactif
CHOICE=$($UI_TOOL --title "Agent Pi — Sélection dynamique du modèle" \
    --menu "Modèles chargés depuis pi/config/models.json :" \
    "$MENU_HEIGHT" 74 "$NUM_MODELS" \
    "${MENU_ITEMS[@]}" \
    3>&1 1>&2 2>&3)

# Si l'utilisateur appuie sur Annuler / Échap
if [ $? -ne 0 ]; then
    clear
    echo "Lancement annulé."
    exit 0
fi

clear
echo "🚀 Démarrage de l'agent Pi avec : $CHOICE"

# 4. S'assurer qu'Ollama tourne en arrière-plan
docker compose up -d ollama

# 5. Lancement du conteneur éphémère Pi avec le modèle choisi (et transmission d'éventuels arguments supplémentaires)
if [ "$CHOICE" == "default" ]; then
    docker compose run --rm pi "$@"
else
    docker compose run --rm pi --model "$CHOICE" "$@"
fi

