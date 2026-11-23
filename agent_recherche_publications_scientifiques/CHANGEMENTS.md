# Changements de la branche `feat/selection-zotero`

**Objectif.** Pi constitue une sélection de publications sur un thème, classée par pertinence et par citations, exportable dans Zotero. Open WebUI interroge le contenu des PDF. Le tout sans temps perdu sur un HP Victus (Ryzen 5 5600H, RTX 3050 4 Go, 16 Go de RAM).

## Constats de départ (session du 23/11)

| Problème | Effet |
|---|---|
| qwen3:4b en mode réflexion | ~6 000 tokens de réflexion : 8 min 30 pour une recherche de 2,4 s |
| ~12 tokens/s au lieu de ~40 | contexte 16k : le modèle débordait probablement sur le CPU |
| le LLM relisait tout `metadata.json` | un tour de ~4 min, et seulement 5 articles affichés sur 15 |
| phrase de l'utilisateur envoyée telle quelle, en français seulement | ~la moitié des résultats hors sujet |
| ni pertinence ni citations ; notices tronquées | ni classement ni export Zotero possibles |
| PDF téléchargés mais jamais lus | « synthèse » faite sur des bouts de résumés |

## Choix et raisons

**Rapidité**
- Modèle par défaut `qwen3:4b-instruct` (Qwen3-4B-Instruct-2507), qui ne réfléchit jamais. Avec `qwen3:4b`, `/no_think`, noyé dans le long prompt système de Pi, était ignoré : 10 min de réflexion lors du premier essai.
- Contexte 8k avec cache KV `q8_0`, pour que le modèle tienne entièrement en VRAM.
- Le modèle de code qwen2.5-coder est retiré.

**Un seul appel d'outil**
- `search_manager.py review` fait tout. Le LLM ne fait que ce qui demande du jugement :
  - écrire les requêtes et le concept central (`--core`) ;
  - choisir les bases ;
  - noter la pertinence, via un appel direct et court à Ollama sans boucle d'agent.

**Français et anglais**
- `review` exige `--fr` et `--en` et n'a pas de filtre de langue.
- La consigne de notation ignore la langue.
- L'agent n'a donc rien à arbitrer.
- `AGENTS.md`, `SKILL.md` et la consigne de notation sont rédigés en anglais, car Qwen3 suit mieux des consignes en anglais. Le modèle répond dans la langue de l'utilisateur.
- Barème de notation strict (le concept central doit être étudié, au moindre doute la note basse) : au premier essai, 179 notices sur 302 avaient reçu 2, dont un article sur les poèmes d'Ossian.

**Classement**
- Score = pertinence 0-3 + poids × percentile de citations OpenAlex (corrigé de l'âge et du domaine), puis citations brutes à égalité. Poids 1 par défaut (`--citation-weight`) : une notice notée 2 ne passe jamais devant une notée 3. Un poids 2, rejoué sur le 2e essai, évinçait 13 des 15 notices notées 3 : sans DOI (ERIC) ou trop récentes, elles n'avaient pas de percentile, et non des citations faibles.
- Les classiques sont recherchés à part (`--core`) : pour le concept central et ses synonymes, les travaux les plus cités qui le portent dans leur titre. Au 2e essai, les requêtes précises avaient manqué Boud 1999, O'Donnell, Topping et Riese, trouvés au 1er essai par la requête « peer learning ». Le titre est exigé : trier la recherche plein texte d'OpenAlex par citations ramène PRISMA ou NumPy.
- Boule de neige (`--snowball`, 10 par défaut, 0 = aucune) : après la notation, les travaux cités par au moins 3 notices pertinentes sont ajoutés, puis notés. Rejoué sur le 2e essai, et sans dépendre de `--core`, cela ajoute 9 travaux sur le sujet (Topping 2005 *Trends in Peer Learning*, Rohrbeck 2003, un guide de qualité pour les études quasi-expérimentales…). Un travail déjà présent sous une autre source est complété plutôt que dupliqué : Topping 1996, présent via ERIC sans DOI ni citations, reçoit ses 1 551 citations. Seules les références des notices pertinentes comptent : avec toutes les notices, quelques articles d'IA hors sujet ramenaient LSTM et ImageNet. Les notices sans DOI ni id OpenAlex (ERIC) ne comptent pas comme citeurs.
- Les citations ne font jamais entrer une notice sous `--min-relevance` : le filtre de pertinence passe avant le classement.
- Les citations viennent toutes d'OpenAlex : des chiffres de bases différentes ne sont pas comparables.
- Les bases sans DOI ne sont pas défavorisées : ERIC n'avait ni citations ni percentile (58 notices sur 59 au 3e essai), donc aucun bonus, et passait sous toute notice mesurée. Après la notation, les notices pertinentes sans DOI sont retrouvées dans OpenAlex par leur titre exact (année ±1) : 31 sur 35 au 3e essai, avec citations et DOI. Un percentile encore inconnu vaut 0,5 (valeur attendue d'une répartition uniforme) et non 0, tandis qu'un 0 mesuré reste un 0. Rejoué sur le 3e essai, le top 20 ne change pas : les notices ERIC retrouvées ont de vrais percentiles (0,92 ; 0,89) plus bas que les 20 premières (≥ 0,95), et se classent 22e, 23e…
- Une notice sans résumé est notée 2 au plus : sur le titre seul, le modèle donnait 3 à des textes hors sujet.
- Seules les 20 mieux classées sont retenues (`--top`), et la commande n'affiche qu'un résumé. Toute sa sortie revient dans le contexte 8k de l'agent : au premier essai, 223 lignes l'avaient fait dérailler.

**Zotero**
- Chaque notice a son type, sa revue, son volume, son numéro, ses pages, sa langue, tous ses auteurs et son résumé complet.
- Export `.ris` ; le lien PDF est dans la note de chaque notice.
- Aucun PDF n'est téléchargé : le lien (légal, via OpenAlex/Unpaywall ou la base d'origine) suffit, et la commande n'a plus à affronter l'anti-robot de HAL. Pour interroger un PDF dans Open WebUI, on le télécharge soi-même depuis le lien.

**Open WebUI**
- Embeddings multilingues (`BAAI/bge-m3`) : le modèle par défaut ne gère que l'anglais.
- Le montage `workspace` dans Open WebUI est supprimé : il n'était pas indexé. Les PDF téléchargés à la main se chargent dans une collection.

**Docker**
- Les clés API sont des `secrets`, avec un fichier vide quand il n'y a pas de clé.
- `AGENTS.md` et `models.json` sont des `configs`.
- Les skills restent un montage en lecture seule : `configs` ne prend pas de dossiers.
- `workspace/` et `pi/config/sessions/` sont ignorés par git.

**Code**
- Une étape par module : `search`, `rank`, `enrich` (après la notation), `export`. L'ordre des étapes de `review` est vérifié par un test : la recherche par titre fournit les DOI dont la boule de neige a besoin.
- Moins de choses à écrire pour le petit modèle : le dossier est dérivé du premier terme de `--core` (`--dir` reste possible) au lieu d'être nommé par l'agent, qui y avait mis une date inventée ; `SKILL.md` perd environ 30 % de ses mots (un seul exemple, règles fusionnées, options rares en une ligne). Au 3e essai le modèle avait déjà rempli toute la commande du premier coup (205 tokens, 2 709 de contexte sur 8 192).
- Les tests remplacent les fonctions réseau avec `unittest.mock.patch`, qui les remet en place à la fin de chaque test.
- Format de notice commun (`records.py`) et accès réseau partagé (`net.py`).
- Un module par base, plus un registre.
- Test hors ligne (`test_search_manager.py`).

**Corrections**
- Bouton Annuler de `start-pi.sh`.
- Seuls de vrais liens PDF sont gardés.
- Dépendances Python inutilisées retirées.

## Bases de données

| Base | Statut | Remarque |
|---|---|---|
| HAL, TEL, DUMAS | sans clé | TEL et DUMAS sont des portails HAL |
| Crossref, ERIC, DOAJ | sans clé | |
| Cairn, Persée, OpenEdition, JSTOR, Taylor & Francis | sans clé, via Crossref | pas d'API publique : Crossref filtré sur leur préfixe DOI ; métadonnées seulement |
| OpenAlex | clé recommandée | sans clé, quota très réduit ; source des citations et des PDF légaux (Unpaywall) |
| Semantic Scholar, CORE | clé facultative | sans clé : 429 / service saturé |
| Springer Nature, Scopus, Web of Science | clé obligatoire | écrits d'après la documentation, **non testés** : vérifier avec `sources --check` |
| Google Scholar | non intégrée | pas d'API, bloque les robots, l'interdit dans ses conditions |
| Pascal et Francis | non intégrée | archive figée (1972-2015) sans API |
| EBSCO | non intégrée | API réservée aux établissements abonnés |
| Sci-Hub, Open-Slum | exclues | violation du droit d'auteur ; Open-Slum ne fait que surveiller ces sites. Remplacées par les PDF légaux d'OpenAlex/Unpaywall |

## Essais sur le HP Victus (23/11, peer learning)

| | Essai 1 (`qwen3:4b`) | Essai 2 (`qwen3:4b-instruct`) |
|---|---|---|
| Durée totale | 19 min, dont 10 de réflexion | 6 min, sans réflexion |
| Retenues | 223 / 302 | 20 / 188 (21 notées 3, 59 notées 2) |
| Réponse finale | hors sujet (contexte débordé) | correcte, mais 100 s à recopier le tableau |

## Tests réels (sans clé, sans Ollama)

- **Recherche :** 14 bases répondent. 54 notices uniques sur 8 bases ; OpenAlex en a complété 26 (citations ou PDF légal).
- **Échecs sans clé :** OpenAlex (erreur 525), Semantic Scholar (429), CORE (saturé).
- **HAL :** ses PDF sont derrière une page anti-robot : un navigateur les ouvre, pas un script. D'où le choix de ne donner que le lien.
- **Non testé ici :**
  - la notation par le LLM ;
  - l'import Zotero ;
  - compose avec les `secrets` (Docker n'était pas démarré, seul `docker compose config` a été validé).

## Limites connues

- Noms de famille composés mal coupés dans le `.ris` : à corriger dans Zotero.
- Année HAL parfois égale à la date de dépôt.
- Les PDF scannés téléversés dans Open WebUI restent vides sans OCR.
- 16 Go de RAM : pas de place pour un modèle plus gros.
