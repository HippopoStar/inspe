from utils import HTTP_SESSION, build_url, make_record, sanitize_lucene_query


def _type(pub_types: list) -> str:
    joined = " ".join(pub_types or [])
    if "Journal Articles" in joined:
        return "JOUR"
    if "Dissertations" in joined:
        return "THES"
    if "Books" in joined:
        return "BOOK"
    if "Reports" in joined:
        return "RPRT"
    return "GEN"


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.ies.ed.gov", "/eric/")
    safe_query = sanitize_lucene_query(query)
    params = {
        "search": safe_query,
        "rows": max_results,
        "format": "json",
        "fields": "id,title,author,publicationdateyear,description,url,e_fulltextauth,source,publicationtype,language",
    }
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for d in r.json().get("response", {}).get("docs", []):
        eric_id = d.get("id", "")
        # Le champ url est une page éditeur, pas un PDF : on ne le met donc pas dans pdf_url
        pdf_url = build_url("files.eric.ed.gov", f"/fulltext/{eric_id}.pdf") if d.get("e_fulltextauth") == 1 else ""
        results.append(make_record(
            source="eric",
            doc_id=eric_id,
            title=d.get("title", ""),
            authors=d.get("author", []),
            year=d.get("publicationdateyear"),
            abstract=d.get("description", ""),
            pdf_url=pdf_url,
            item_type=_type(d.get("publicationtype")),
            container=d.get("source", ""),
            language=d.get("language"),
            url=d.get("url") or f"https://eric.ed.gov/?id={eric_id}",
        ))
    return results
