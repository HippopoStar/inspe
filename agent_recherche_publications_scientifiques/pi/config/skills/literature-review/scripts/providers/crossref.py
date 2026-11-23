import re
from utils import HTTP_SESSION, build_url, make_record, first

TYPES = {
    "journal-article": "JOUR", "book-chapter": "CHAP", "proceedings-article": "CONF",
    "book": "BOOK", "monograph": "BOOK", "dissertation": "THES", "report": "RPRT",
}


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.crossref.org", "/works")
    params = {"query": query, "rows": max_results}
    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for item in r.json().get("message", {}).get("items", []):
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", [])
        ]

        date_parts = item.get("published", {}).get("date-parts", [])
        first_date = next(iter(date_parts), [])
        year = next(iter(first_date), None)

        pdf_url = next(
            (l.get("URL") for l in item.get("link", []) if "pdf" in l.get("content-type", "")),
            ""
        )
        abstract = re.sub(r"<[^>]+>", "", item.get("abstract", ""))

        results.append(make_record(
            source="crossref",
            doc_id=item.get("DOI", ""),
            title=first(item.get("title", "")),
            authors=authors,
            year=year,
            abstract=abstract,
            pdf_url=pdf_url,
            doi=item.get("DOI", ""),
            item_type=TYPES.get(item.get("type"), "GEN"),
            container=first(item.get("container-title", "")),
            volume=item.get("volume"),
            issue=item.get("issue"),
            pages=item.get("page"),
            language=item.get("language"),
            url=item.get("URL", ""),
            cited_by=item.get("is-referenced-by-count"),
        ))
    return results
