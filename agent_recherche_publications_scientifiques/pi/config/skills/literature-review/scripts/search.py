"""Étape 1 : interroger les bases, fusionner les doublons, compléter citations et PDF via OpenAlex."""
from providers import SOURCES, available, status
from providers.openalex import lookup_dois, most_cited
from net import lucene_safe
from records import deduplicate


def usable_sources(names: list) -> list:
    """« all » = toutes les bases accessibles ; une base dont la clé obligatoire manque est ignorée."""
    names = " ".join(names).split()  # « hal tel » entre guillemets = « hal » « tel »
    names = available() if "all" in names else names
    for name in names:
        if status(name) == "clé manquante":
            print(f"[{name}] ignoré : clé manquante (secrets/{SOURCES[name]['key']})")
    return [n for n in names if status(n) != "clé manquante"]


def complete_from_openalex(records: list):
    """Une seule source de citations (sinon les chiffres de bases différentes ne sont pas comparables),
    et un PDF légal en accès libre quand la base d'origine n'en donnait pas."""
    dois = [r["doi"] for r in records if r["doi"] and (r["citation_percentile"] is None or not r["pdf_url"])]
    if not dois:
        return
    try:
        found = lookup_dois(dois)
    except Exception as e:
        print(f"[openalex] complément impossible : {e}")
        return
    for rec in records:
        extra = found.get(rec["doi"])
        if extra:
            if rec["citation_percentile"] is None:
                rec["cited_by"], rec["citation_percentile"] = extra["cited_by"], extra["citation_percentile"]
            rec["pdf_url"] = rec["pdf_url"] or extra["pdf_url"]
    print(f"[openalex] {len(found)} notice(s) complétée(s) (citations, PDF en accès libre).")


def equation(*blocks) -> str:
    """« ("a" OR "b") AND ("c" OR "d") » : OR entre synonymes contre le silence, AND entre blocs contre le bruit.
    Chaque terme est nettoyé puis mis entre guillemets : l'équation est sûre pour Solr (HAL, ERIC) et OpenAlex."""
    return " AND ".join("(" + " OR ".join(f'"{lucene_safe(t)}"' for t in block) + ")" for block in blocks)


def _ask(source: str, label: str, query: str, max_results: int, lang, **extra) -> list:
    try:
        found = SOURCES[source]["fn"](query, max_results, lang, **extra)
        print(f"[{source}] {label} : {len(found)}")
        return found
    except Exception as e:
        print(f"[{source}] erreur : {str(e)[:160]}")
        return []


def search(queries: list, sources: list, max_results: int, lang: str = None, core: list = (),
           facet: list = ()) -> list:
    raw, sources = [], usable_sources(sources)
    for source in sources:
        for query in queries:
            extra = {"core": core} if SOURCES[source]["takes_core"] and core else {}
            raw += _ask(source, f"« {query} »", query, max_results, lang, **extra)
    # Le type d'étude demandé (méta-analyses, études expérimentales…) : une équation (concepts) AND (type d'étude),
    # dans les bases qui la comprennent. Les requêtes libres restent : l'équation seule manquerait les résumés
    # qui ne nomment pas le type d'étude.
    if core and facet:
        eq = equation(core, facet)
        for source in sources:
            if SOURCES[source]["boolean"]:
                raw += _ask(source, "équation concepts ET type d'étude", eq, max_results, lang, boolean=True)
    # Les requêtes précises ne ramènent pas les classiques (2e essai : Boud 1999, Topping absents) :
    # pour chaque concept central, les travaux les plus cités qui le portent dans leur titre.
    for term in core:
        try:
            found = most_cited(term, max_results)
            print(f"[openalex, plus cités] « {term} » : {len(found)}")
            raw += found
        except Exception as e:
            print(f"[openalex, plus cités] erreur : {str(e)[:160]}")
    records = deduplicate(raw)
    print(f"{len(records)} notices uniques ({len(raw) - len(records)} doublon(s) fusionné(s)).")
    complete_from_openalex(records)
    return records
