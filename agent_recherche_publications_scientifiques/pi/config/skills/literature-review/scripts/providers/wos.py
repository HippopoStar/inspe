"""Web of Science, API Starter (Clarivate). Clé obligatoire (https://developer.clarivate.com). Pas de résumés :
la pertinence est alors notée sur le titre seul.
ponytail: écrit d'après la documentation, non testé faute de clé ; vérifier avec `sources --check`."""
from net import HTTP, secret
from records import make_record

URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
TYPES = {"article": "JOUR", "review": "JOUR", "proceedings": "CONF", "book chapter": "CHAP", "book": "BOOK"}


def _type(types: list) -> str:
    joined = " ".join(types or []).lower()
    return next((ris for label, ris in TYPES.items() if label in joined), "GEN")


def search(query: str, max_results: int, lang: str = None) -> list:
    r = HTTP.get(URL, headers={"X-ApiKey": secret("wos_api_key")}, timeout=30, params={
        "q": f'TS=("{query.replace(chr(34), " ")}")', "limit": max_results, "db": "WOS"})
    r.raise_for_status()
    results = []
    for h in r.json().get("hits", []):
        src = h.get("source") or {}
        results.append(make_record(
            "wos", h.get("uid", ""), h.get("title"),
            [a.get("wosStandard") or a.get("displayName") for a in (h.get("names") or {}).get("authors", [])],
            src.get("publishYear"), "", "", (h.get("identifiers") or {}).get("doi", ""),
            item_type=_type(h.get("types")), container=src.get("sourceTitle", ""),
            volume=src.get("volume"), issue=src.get("issue"), pages=(src.get("pages") or {}).get("range", ""),
            url=(h.get("links") or {}).get("record", ""),
            cited_by=next((c.get("count") for c in h.get("citations") or [] if c.get("db") == "WOS"), None),
        ))
    return results
