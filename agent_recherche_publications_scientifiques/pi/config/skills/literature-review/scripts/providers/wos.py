from utils import HTTP_SESSION, build_url, make_record, secret

# Web of Science Starter API (Clarivate). Clé gratuite (quota limité) : https://developer.clarivate.com
# ponytail: écrit d'après la documentation, non testé faute de clé ; vérifier avec `sources --check`.


def _type(types: list) -> str:
    t = " ".join(types or []).lower()
    if "article" in t or "review" in t:
        return "JOUR"
    if "proceedings" in t:
        return "CONF"
    if "book chapter" in t:
        return "CHAP"
    if "book" in t:
        return "BOOK"
    return "GEN"


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.clarivate.com", "/apis/wos-starter/v1/documents")
    safe = query.replace('"', " ")
    r = HTTP_SESSION.get(url, params={"q": f'TS=("{safe}")', "limit": max_results, "db": "WOS"},
                         headers={"X-ApiKey": secret("wos_api_key")}, timeout=30)
    r.raise_for_status()

    results = []
    for h in r.json().get("hits", []):
        src = h.get("source") or {}
        cites = next((c.get("count") for c in h.get("citations") or [] if c.get("db") == "WOS"), None)
        results.append(make_record(
            source="wos",
            doc_id=h.get("uid", ""),
            title=h.get("title", ""),
            authors=[a.get("wosStandard") or a.get("displayName", "") for a in (h.get("names") or {}).get("authors", [])],
            year=src.get("publishYear"),
            abstract="",  # l'API Starter ne fournit pas les résumés
            pdf_url="",
            doi=(h.get("identifiers") or {}).get("doi", ""),
            item_type=_type(h.get("types")),
            container=src.get("sourceTitle", ""),
            volume=src.get("volume"),
            issue=src.get("issue"),
            pages=(src.get("pages") or {}).get("range", ""),
            url=(h.get("links") or {}).get("record", ""),
            cited_by=cites,
        ))
    return results
