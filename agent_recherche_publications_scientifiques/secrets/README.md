# Clés API (facultatives)

Un fichier par clé, contenant seulement la clé, nommé exactement comme ci-dessous. Ce dossier est
ignoré par git (sauf ce README) et monté en lecture seule dans `/run/secrets` du conteneur `pi`.

| Fichier | Base | Sans ce fichier | Obtenir la clé (gratuite) |
|---|---|---|---|
| `openalex_api_key` | OpenAlex (+ citations de toutes les bases) | quota très réduit, erreurs possibles | https://openalex.org/settings/api |
| `s2_api_key` | Semantic Scholar | erreurs 429 fréquentes | https://www.semanticscholar.org/product/api#api-key-form |
| `core_api_key` | CORE | quota bas | https://core.ac.uk/services/api |
| `springer_api_key` | Springer Nature | base désactivée | https://dev.springernature.com |
| `scopus_api_key` | Scopus | base désactivée | https://dev.elsevier.com |
| `scopus_insttoken` | Scopus (accès complet hors campus) | résultats partiels hors réseau de l'établissement | à demander à la bibliothèque |
| `wos_api_key` | Web of Science (Starter) | base désactivée | https://developer.clarivate.com |

Exemple :
```
echo -n "ma_cle" > secrets/openalex_api_key
chmod 644 secrets/openalex_api_key   # lisible par l'utilisateur du conteneur (UID 1000)
```

Vérifier les bases accessibles avec les clés fournies :
```
docker compose run --rm --entrypoint python3 pi \
  /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py sources --check
```
