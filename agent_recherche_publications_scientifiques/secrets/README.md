# Clés API (docker secrets, toutes facultatives)

Un fichier par clé, nommé comme ci-dessous, contenant seulement la clé. Les fichiers sont déclarés comme
`secrets` dans `compose.yml` et lus dans `/run/secrets/<nom>`. Ce dossier est ignoré par git, sauf ce README.

`./start-pi.sh` crée les fichiers manquants, vides. Un fichier vide signifie « pas de clé ». Sans passer par
ce script : `docker compose config --format json | jq -r '.secrets[].file' | xargs touch`.

| Fichier | Base | Sans clé | Obtenir la clé (gratuite) |
|---|---|---|---|
| `openalex_api_key` | OpenAlex, et citations + PDF légaux pour toutes les bases | quota très réduit | https://openalex.org/settings/api |
| `s2_api_key` | Semantic Scholar | erreurs 429 fréquentes | https://www.semanticscholar.org/product/api#api-key-form |
| `core_api_key` | CORE | quota bas, souvent saturé | https://core.ac.uk/services/api |
| `springer_api_key` | Springer Nature | désactivée | https://dev.springernature.com |
| `scopus_api_key` | Scopus | désactivée | https://dev.elsevier.com |
| `scopus_insttoken` | Scopus hors campus | résultats partiels hors réseau de l'établissement | bibliothèque universitaire |
| `wos_api_key` | Web of Science | désactivée | https://developer.clarivate.com |

```
echo -n "ma_cle" > secrets/openalex_api_key
```

Bases accessibles avec les clés fournies, une vraie requête de test par base :
```
docker compose run --rm --entrypoint python3 pi \
  /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py sources --check
```
