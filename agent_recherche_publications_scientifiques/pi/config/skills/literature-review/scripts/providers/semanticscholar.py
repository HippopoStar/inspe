from utils import HTTP_SESSION, build_url, make_record


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.semanticscholar.org", "/graph/v1/paper/search")
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,authors,year,abstract,openAccessPdf,externalIds",
    }
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for p in r.json().get("data", []):
        authors = [a.get("name", "") for a in p.get("authors", [])]
        pdf_url = (p.get("openAccessPdf") or {}).get("url", "")
        doi = (p.get("externalIds") or {}).get("DOI", "")
        results.append(make_record(
            source="semanticscholar",
            doc_id=p.get("paperId", ""),
            title=p.get("title", ""),
            authors=authors,
            year=p.get("year"),
            abstract=p.get("abstract", ""),
            pdf_url=pdf_url,
            doi=doi,
        ))
    return results

