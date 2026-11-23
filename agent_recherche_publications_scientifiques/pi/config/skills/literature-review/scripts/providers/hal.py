from utils import HTTP_SESSION, build_url, make_record, sanitize_lucene_query


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.archives-ouvertes.fr", "/search/")
    safe_query = sanitize_lucene_query(query)
    q = f"({safe_query})"
    if lang:
        q += f" AND language_s:{lang}"

    params = {
        "q": q,
        "rows": max_results,
        "wt": "json",
        "fl": "halId_s,title_s,authFullName_s,producedDateY_i,abstract_s,fileMain_s,doiId_s",
    }
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for d in r.json().get("response", {}).get("docs", []):
        raw_title = d.get("title_s", "")
        title = next(iter(raw_title), "") if isinstance(raw_title, list) else raw_title

        raw_abstract = d.get("abstract_s", "")
        abstract = next(iter(raw_abstract), "") if isinstance(raw_abstract, list) else raw_abstract

        results.append(make_record(
            source="hal",
            doc_id=d.get("halId_s", ""),
            title=title,
            authors=d.get("authFullName_s", []),
            year=d.get("producedDateY_i"),
            abstract=abstract,
            pdf_url=d.get("fileMain_s", ""),
            doi=d.get("doiId_s", ""),
        ))
    return results

