"""Étape 1b : « boule de neige ». Ajoute les travaux que citent plusieurs notices pertinentes : les classiques
du sujet, que les requêtes manquent quand leur titre ne contient pas les mots cherchés."""
from collections import Counter

from providers import openalex
from records import fill_gaps, match_keys

MIN_CITERS = 3   # cité par au moins 3 notices pertinentes : un seul citeur ne fait pas un classique


def snowball(records: list, min_relevance: int, limit: int, min_citers: int = MIN_CITERS) -> list:
    """Nouvelles notices (à noter ensuite), au plus `limit`, chacune avec `cited_by_results` = nombre de notices
    pertinentes de la liste qui la citent. Références lues dans OpenAlex : les notices sans DOI ni id OpenAlex
    (ERIC, une partie de HAL) ne comptent pas comme citeurs."""
    relevant = [r for r in records if (r.get("relevance") or 0) >= min_relevance]
    if not limit or not relevant:
        return []
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
