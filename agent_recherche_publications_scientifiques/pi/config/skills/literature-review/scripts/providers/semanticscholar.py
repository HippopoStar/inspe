"""Semantic Scholar. Clé facultative (sans clé : erreurs 429 fréquentes) :
https://www.semanticscholar.org/product/api#api-key-form"""
from net import HTTP, secret
from records import make_record

URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "paperId,title,authors,year,abstract,openAccessPdf,externalIds,citationCount,venue,journal,url"


def search(query: str, max_results: int, lang: str = None) -> list:
    key = secret("s2_api_key")
    r = HTTP.get(URL, params={"query": query, "limit": max_results, "fields": FIELDS},
                 headers={"x-api-key": key} if key else {}, timeout=20)
    r.raise_for_status()
    results = []
    for p in r.json().get("data", []):
        journal = p.get("journal") or {}
        results.append(make_record(
            "semanticscholar", p.get("paperId", ""), p.get("title"), [a.get("name") for a in p.get("authors", [])],
            p.get("year"), p.get("abstract"), (p.get("openAccessPdf") or {}).get("url", ""),
            (p.get("externalIds") or {}).get("DOI", ""),
            item_type="JOUR" if journal.get("name") else "GEN",
            container=journal.get("name") or p.get("venue") or "",
            volume=journal.get("volume"), pages=(journal.get("pages") or "").strip(),
            url=p.get("url", ""), cited_by=p.get("citationCount"),
        ))
    return results
