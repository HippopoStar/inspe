"""Crossref (sans clé). Avec `prefix`, restreint à un éditeur par son préfixe DOI : c'est ainsi qu'on
interroge Cairn, Persée, OpenEdition, JSTOR ou Taylor & Francis, qui n'ont pas d'API de recherche publique."""
import re

from net import HTTP
from records import make_record, first

URL = "https://api.crossref.org/works"
TYPES = {"journal-article": "JOUR", "book-chapter": "CHAP", "proceedings-article": "CONF",
         "book": "BOOK", "monograph": "BOOK", "dissertation": "THES", "report": "RPRT"}


def search(query: str, max_results: int, lang: str = None, prefix: str = None, source: str = "crossref") -> list:
    params = {"query": query, "rows": max_results}
    if prefix:
        params["filter"] = f"prefix:{prefix}"
    r = HTTP.get(URL, params=params, timeout=20)
    r.raise_for_status()
    results = []
    for it in r.json().get("message", {}).get("items", []):
        date = first(it.get("published", {}).get("date-parts")) or [None]
        results.append(make_record(
            source, it.get("DOI", ""), it.get("title"),
            [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", [])],
            date[0], re.sub(r"<[^>]+>", "", it.get("abstract", "")),
            next((l["URL"] for l in it.get("link", []) if "pdf" in l.get("content-type", "")), ""),
            it.get("DOI", ""),
            item_type=TYPES.get(it.get("type"), "GEN"), container=it.get("container-title"),
            volume=it.get("volume"), issue=it.get("issue"), pages=it.get("page"),
            language=it.get("language"), url=it.get("URL", ""), cited_by=it.get("is-referenced-by-count"),
        ))
    return results
