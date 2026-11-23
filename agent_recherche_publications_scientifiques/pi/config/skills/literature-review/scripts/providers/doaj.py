from urllib.parse import quote
from utils import HTTP_SESSION, build_url, make_record, sanitize_lucene_query


def search(query: str, max_results: int, lang: str = None) -> list:
    safe_query = sanitize_lucene_query(query)
    url = build_url("doaj.org", f"/api/search/articles/{quote(safe_query)}")
    params = {"pageSize": max_results}
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for item in r.json().get("results", []):
        bib = item.get("bibjson", {})
        authors = [a.get("name", "") for a in bib.get("author", [])]
        pdf_url = next((l.get("url") for l in bib.get("link", []) if l.get("type") == "fulltext"), "")
        doi = next((i.get("id") for i in bib.get("identifier", []) if i.get("type") == "doi"), "")
        results.append(make_record(
            source="doaj",
            doc_id=item.get("id", ""),
            title=bib.get("title", ""),
            authors=authors,
            year=bib.get("year"),
            abstract=bib.get("abstract", ""),
            pdf_url=pdf_url,
            doi=doi,
        ))
    return results

