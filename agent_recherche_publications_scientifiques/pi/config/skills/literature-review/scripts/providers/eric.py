from utils import HTTP_SESSION, build_url, make_record, sanitize_lucene_query


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.ies.ed.gov", "/eric/")
    safe_query = sanitize_lucene_query(query)
    params = {
        "search": safe_query,
        "rows": max_results,
        "format": "json",
        "fields": "id,title,author,publicationdateyear,description,url,e_fulltextauth",
    }
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for d in r.json().get("response", {}).get("docs", []):
        eric_id = d.get("id", "")
        pdf_url = build_url("files.eric.ed.gov", f"/fulltext/{eric_id}.pdf") if d.get("e_fulltextauth") == 1 else d.get("url", "")
        results.append(make_record(
            source="eric",
            doc_id=eric_id,
            title=d.get("title", ""),
            authors=d.get("author", []),
            year=d.get("publicationdateyear"),
            abstract=d.get("description", ""),
            pdf_url=pdf_url,
        ))
    return results

