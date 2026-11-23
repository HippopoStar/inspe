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
        journal = bib.get("journal", {})
        authors = [a.get("name", "") for a in bib.get("author", [])]
        # Le lien « fulltext » de DOAJ est souvent une page HTML ; download vérifie la signature %PDF
        fulltext = next((l.get("url") for l in bib.get("link", []) if l.get("type") == "fulltext"), "")
        doi = next((i.get("id") for i in bib.get("identifier", []) if i.get("type") == "doi"), "")
        pages = "-".join(p for p in (bib.get("start_page"), bib.get("end_page")) if p)
        results.append(make_record(
            source="doaj",
            doc_id=item.get("id", ""),
            title=bib.get("title", ""),
            authors=authors,
            year=bib.get("year"),
            abstract=bib.get("abstract", ""),
            pdf_url=fulltext,
            doi=doi,
            item_type="JOUR",
            container=journal.get("title", ""),
            volume=journal.get("volume"),
            issue=journal.get("number"),
            pages=pages,
            language=journal.get("language"),
            url=fulltext,
        ))
    return results
