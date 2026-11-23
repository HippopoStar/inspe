"""CORE (archives ouvertes du monde entier). Clé facultative : sans clé, quota bas et service
parfois saturé (500/503). Clé : https://core.ac.uk/services/api"""
from net import HTTP, secret
from records import make_record

URL = "https://api.core.ac.uk/v3/search/works/"
TYPES = {"research": "JOUR", "thesis": "THES", "book": "BOOK", "report": "RPRT"}


def search(query: str, max_results: int, lang: str = None) -> list:
    key = secret("core_api_key")
    r = HTTP.get(URL, params={"q": query, "limit": max_results},
                 headers={"Authorization": f"Bearer {key}"} if key else {}, timeout=30)
    r.raise_for_status()
    return [make_record(
        "core", str(w.get("id", "")), w.get("title"), [a.get("name") for a in w.get("authors") or []],
        w.get("yearPublished"), w.get("abstract"), w.get("downloadUrl") or "", w.get("doi") or "",
        item_type=TYPES.get((w.get("documentType") or "").lower(), "GEN"),
        container=((w.get("journals") or [{}])[0] or {}).get("title", ""),
        language=(w.get("language") or {}).get("code", ""),
        url=f"https://core.ac.uk/works/{w.get('id')}", cited_by=w.get("citationCount"),
    ) for w in r.json().get("results", [])]
