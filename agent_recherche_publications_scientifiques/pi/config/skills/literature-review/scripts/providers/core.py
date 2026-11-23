from utils import HTTP_SESSION, build_url, make_record, secret

# CORE agrège les archives ouvertes du monde entier. Utilisable sans clé (quota bas, et le service
# renvoie parfois des 500/503 quand il est saturé) ; clé gratuite : https://core.ac.uk/services/api
TYPES = {"research": "JOUR", "thesis": "THES", "book": "BOOK", "report": "RPRT"}


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.core.ac.uk", "/v3/search/works/")
    key = secret("core_api_key")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = HTTP_SESSION.get(url, params={"q": query, "limit": max_results}, headers=headers, timeout=30)
    r.raise_for_status()

    results = []
    for w in r.json().get("results", []):
        journals = w.get("journals") or [{}]
        results.append(make_record(
            source="core",
            doc_id=str(w.get("id", "")),
            title=w.get("title", ""),
            authors=[a.get("name", "") for a in w.get("authors") or []],
            year=w.get("yearPublished"),
            abstract=w.get("abstract") or "",
            pdf_url=w.get("downloadUrl") or "",
            doi=w.get("doi") or "",
            item_type=TYPES.get((w.get("documentType") or "").lower(), "GEN"),
            container=journals[0].get("title", "") if journals else "",
            language=(w.get("language") or {}).get("code", ""),
            url=f"https://core.ac.uk/works/{w.get('id')}",
            cited_by=w.get("citationCount"),
        ))
    return results
