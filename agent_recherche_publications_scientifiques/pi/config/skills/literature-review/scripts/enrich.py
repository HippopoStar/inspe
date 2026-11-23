"""Étape 2b : enrichir avec OpenAlex une fois les notices notées. Les deux fonctions ne s'adressent qu'aux
notices pertinentes, d'où leur place après la notation : `complete_by_title` d'abord (elle fournit les DOI dont
`snowball` a besoin pour lire les références des notices sans DOI), puis `snowball`."""
from collections import Counter

from providers import openalex
from records import fill_gaps, match_keys

MIN_CITERS = 3   # cité par au moins 3 notices pertinentes : un seul citeur ne fait pas un classique


def complete_by_title(records: list, min_relevance: int):
    """Notices pertinentes sans DOI (ERIC) : retrouvées dans OpenAlex par leur titre, pour leurs citations et leur DOI.
    Une requête par notice, donc seulement pour celles qui peuvent être retenues.
    # ponytail: requêtes séquentielles (~1,2 s chacune, 35 notices ≈ 45 s) ; à grouper si les recherches grossissent."""
    todo = [r for r in records if (r.get("relevance") or 0) >= min_relevance
            and not r["doi"] and r["citation_percentile"] is None]
    found = 0
    print(f"[openalex] recherche par titre de {len(todo)} notice(s) pertinente(s) sans DOI…")
    for i, rec in enumerate(todo, 1):
        if i % 10 == 0:
            print(f"[openalex] {i}/{len(todo)} cherchées par titre")
        try:
            match = openalex.find_by_title(rec["title"], rec["year"])
        except Exception as e:
            print(f"[openalex] recherche par titre interrompue : {str(e)[:160]}")
            break
        if match:
            fill_gaps(rec, match)
            found += 1
    print(f"[openalex] {found}/{len(todo)} notice(s) pertinente(s) sans DOI retrouvée(s) par leur titre (citations, DOI).")


def snowball(records: list, min_relevance: int, limit: int, min_citers: int = MIN_CITERS) -> list:
    """Nouvelles notices (à noter ensuite), au plus `limit`, chacune avec `cited_by_results` = nombre de notices
    pertinentes de la liste qui la citent. Références lues dans OpenAlex : les notices sans DOI ni id OpenAlex
    (ERIC, une partie de HAL) ne comptent pas comme citeurs."""
    relevant = [r for r in records if (r.get("relevance") or 0) >= min_relevance]
    if not limit or not relevant:
        return []
    print(f"[snowball] lecture des références des {len(relevant)} notices pertinentes…")
    try:
        found = openalex.references([r["doi"] for r in relevant if r["doi"] and r["source"] != "openalex"],
                                    [r["id"].split(":", 1)[1] for r in relevant if r["source"] == "openalex"])
        cited = {wid: refs for wid, _, refs in found}   # par id : un citeur trouvé deux fois ne compte qu'une fois
        known = set(cited) | {r["id"].split(":", 1)[1] for r in records if r["source"] == "openalex"}
        counts = Counter(ref for refs in cited.values() for ref in set(refs) if ref not in known)
        top = [wid for wid, n in counts.most_common(2 * limit) if n >= min_citers]   # marge : doublons écartés plus bas
        candidates = openalex.works(top) if top else []
    except Exception as e:
        print(f"[snowball] impossible : {str(e)[:160]}")
        return []
    in_list = {k: r for r in records for k in match_keys(r)}
    added, completed = [], 0
    for rec in candidates:
        rec["cited_by_results"] = counts[rec["id"].split(":", 1)[1]]
        twin = next((in_list[k] for k in match_keys(rec) if k in in_list), None)
        if twin:   # déjà dans la liste sous une autre source (ERIC : ni DOI ni citations) : on la complète
            fill_gaps(twin, rec)
            twin["cited_by_results"] = rec["cited_by_results"]
            completed += 1
        else:
            added.append(rec)
    added = sorted(added, key=lambda r: -r["cited_by_results"])[:limit]
    print(f"[snowball] {len(added)} travail(aux) ajouté(s), {completed} déjà présent(s) complété(s) (citations, DOI), "
          f"cités par ≥ {min_citers} des {len(cited)} notices pertinentes lues.")
    return added
