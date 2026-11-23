from utils import HTTP_SESSION, build_url, make_record, secret

# Sans clé, le quota partagé renvoie souvent des 429. Clé gratuite sur demande :
# https://www.semanticscholar.org/product/api#api-key-form


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.semanticscholar.org", "/graph/v1/paper/search")
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,authors,year,abstract,openAccessPdf,externalIds,citationCount,venue,journal,url",
    }
    key = secret("s2_api_key")
    headers = {"x-api-key": key} if key else {}
    r = HTTP_SESSION.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()

    results = []
    for p in r.json().get("data", []):
        authors = [a.get("name", "") for a in p.get("authors", [])]
        pdf_url = (p.get("openAccessPdf") or {}).get("url", "")
        doi = (p.get("externalIds") or {}).get("DOI", "")
        journal = p.get("journal") or {}
        results.append(make_record(
            source="semanticscholar",
            doc_id=p.get("paperId", ""),
            title=p.get("title", ""),
            authors=authors,
            year=p.get("year"),
            abstract=p.get("abstract", ""),
            pdf_url=pdf_url,
            doi=doi,
            item_type="JOUR" if journal.get("name") else "GEN",
            container=journal.get("name") or p.get("venue") or "",
            volume=journal.get("volume"),
            pages=(journal.get("pages") or "").strip(),
            url=p.get("url", ""),
            cited_by=p.get("citationCount"),
        ))
    return results
