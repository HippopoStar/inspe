#!/usr/bin/env bash
# Lance l'agent Pi après choix du modèle dans un menu. Arguments supplémentaires transmis à Pi.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

for tool in jq whiptail; do
    command -v "$tool" > /dev/null || { echo "Erreur : installer $tool (sudo apt install $tool)."; exit 1; }
done

# Chaque secret déclaré dans compose.yml doit exister : on crée les fichiers manquants, vides (= pas de clé).
docker compose config --format json | jq -r '.secrets[].file' | while read -r f; do
    [ -e "$f" ] || touch "$f"
done

# Menu : « fournisseur/modèle » « nom affiché », lus dans models.json.
mapfile -t ITEMS < <(jq -r '.providers | to_entries[] | .key as $p | .value.models[] | "\($p)/\(.id)", .name' \
    pi/config/models.json)
ITEMS+=("default" "Dernier modèle utilisé (défaut Pi)")
COUNT=$(( ${#ITEMS[@]} / 2 ))

CHOICE=$(whiptail --title "Agent Pi" --menu "Modèle :" $(( COUNT + 7 )) 74 "$COUNT" "${ITEMS[@]}" \
    3>&1 1>&2 2>&3) || { clear; echo "Lancement annulé."; exit 0; }
clear

docker compose up -d ollama
if [ "$CHOICE" = "default" ]; then
    docker compose run --rm pi "$@"
else
    docker compose run --rm pi --model "$CHOICE" "$@"
fi
