from utils import HTTP_SESSION, build_url, make_record, secret

# Scopus Search API (Elsevier). Clé gratuite sur https://dev.elsevier.com, mais les résultats ne sont
# complets que depuis le réseau d'un établissement abonné (IP/VPN) ou avec un « insttoken » fourni
# par la bibliothèque (secret scopus_insttoken, optionnel).
# ponytail: écrit d'après la documentation, non testé faute de clé ; vérifier avec `sources --check`.
TYPES = {"ar": "JOUR", "re": "JOUR", "cp": "CONF", "ch": "CHAP", "bk": "BOOK"}


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.elsevier.com", "/content/search/scopus")
    headers = {"X-ELS-APIKey": secret("scopus_api_key")}
    token = secret("scopus_insttoken")
    if token:
        headers["X-ELS-Insttoken"] = token
    safe = query.replace('"', " ")
    r = HTTP_SESSION.get(url, params={"query": f'TITLE-ABS-KEY("{safe}")', "count": max_results},
                         headers=headers, timeout=30)
    r.raise_for_status()

    results = []
    for e in r.json().get("search-results", {}).get("entry", []):
        if "error" in e:  # Scopus renvoie une entrée « Result set was empty »
            continue
        cited = e.get("citedby-count")
        results.append(make_record(
            source="scopus",
            doc_id=(e.get("dc:identifier") or "").replace("SCOPUS_ID:", ""),
            title=e.get("dc:title", ""),
            authors=[e["dc:creator"]] if e.get("dc:creator") else [],  # vue STANDARD : 1er auteur seulement
            year=(e.get("prism:coverDate") or "")[:4],
            abstract=e.get("dc:description", ""),
            pdf_url="",
            doi=e.get("prism:doi", ""),
            item_type=TYPES.get(e.get("subtype"), "GEN"),
            container=e.get("prism:publicationName", ""),
            volume=e.get("prism:volume"),
            issue=e.get("prism:issueIdentifier"),
            pages=e.get("prism:pageRange") or "",
            url=next((l.get("@href") for l in e.get("link", []) if l.get("@ref") == "scopus"), ""),
            cited_by=int(cited) if str(cited or "").isdigit() else None,
        ))
    return results
