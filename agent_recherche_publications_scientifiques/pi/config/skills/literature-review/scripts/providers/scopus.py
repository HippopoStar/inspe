"""Scopus (Elsevier). Clé obligatoire (https://dev.elsevier.com) ; résultats complets seulement depuis le
réseau d'un établissement abonné ou avec le secret facultatif scopus_insttoken (fourni par la bibliothèque).
ponytail: écrit d'après la documentation, non testé faute de clé ; vérifier avec `sources --check`."""
from net import HTTP, secret
from records import make_record

URL = "https://api.elsevier.com/content/search/scopus"
TYPES = {"ar": "JOUR", "re": "JOUR", "cp": "CONF", "ch": "CHAP", "bk": "BOOK"}


def search(query: str, max_results: int, lang: str = None) -> list:
    headers = {"X-ELS-APIKey": secret("scopus_api_key")}
    if secret("scopus_insttoken"):
        headers["X-ELS-Insttoken"] = secret("scopus_insttoken")
    r = HTTP.get(URL, headers=headers, timeout=30, params={
        "query": f'TITLE-ABS-KEY("{query.replace(chr(34), " ")}")', "count": max_results})
    r.raise_for_status()
    results = []
    for e in r.json().get("search-results", {}).get("entry", []):
        if "error" in e:  # entrée factice « Result set was empty »
            continue
        cited = str(e.get("citedby-count") or "")
        results.append(make_record(
            "scopus", (e.get("dc:identifier") or "").replace("SCOPUS_ID:", ""), e.get("dc:title"),
            [e["dc:creator"]] if e.get("dc:creator") else [],  # vue STANDARD : premier auteur seulement
            e.get("prism:coverDate"), e.get("dc:description"), "", e.get("prism:doi", ""),
            item_type=TYPES.get(e.get("subtype"), "GEN"), container=e.get("prism:publicationName", ""),
            volume=e.get("prism:volume"), issue=e.get("prism:issueIdentifier"), pages=e.get("prism:pageRange"),
            url=next((l.get("@href") for l in e.get("link", []) if l.get("@ref") == "scopus"), ""),
            cited_by=int(cited) if cited.isdigit() else None,
        ))
    return results
