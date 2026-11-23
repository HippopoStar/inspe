from utils import HTTP_SESSION, build_url, make_record, sanitize_lucene_query, first

TYPES = {
    "ART": "JOUR", "COMM": "CONF", "THESE": "THES", "HDR": "THES", "OUV": "BOOK",
    "COUV": "CHAP", "REPORT": "RPRT", "MEM": "THES",
}


def search(query: str, max_results: int, lang: str = None, portal: str = "", source: str = "hal") -> list:
    """`portal` = portail HAL : « tel » (thèses) ou « dumas » (mémoires de master)."""
    url = build_url("api.archives-ouvertes.fr", f"/search/{portal}/" if portal else "/search/")
    safe_query = sanitize_lucene_query(query)
    q = f"({safe_query})"
    if lang:
        q += f" AND language_s:{lang}"

    params = {
        "q": q,
        "rows": max_results,
        "wt": "json",
        "fl": "halId_s,title_s,authFullName_s,producedDateY_i,abstract_s,fileMain_s,doiId_s,"
              "docType_s,journalTitle_s,bookTitle_s,conferenceTitle_s,volume_s,issue_s,page_s,language_s,uri_s",
    }
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for d in r.json().get("response", {}).get("docs", []):
        results.append(make_record(
            source=source,
            doc_id=d.get("halId_s", ""),
            title=first(d.get("title_s", "")),
            authors=d.get("authFullName_s", []),
            year=d.get("producedDateY_i"),  # attention : peut être la date de dépôt, pas de 1re publication
            abstract=first(d.get("abstract_s", "")),
            pdf_url=d.get("fileMain_s", ""),
            doi=d.get("doiId_s", ""),
            item_type=TYPES.get(d.get("docType_s"), "GEN"),
            container=first(d.get("journalTitle_s") or d.get("bookTitle_s") or d.get("conferenceTitle_s") or ""),
            volume=d.get("volume_s"),
            issue=d.get("issue_s"),
            pages=d.get("page_s"),
            language=d.get("language_s"),
            url=d.get("uri_s", ""),
        ))
    return results
