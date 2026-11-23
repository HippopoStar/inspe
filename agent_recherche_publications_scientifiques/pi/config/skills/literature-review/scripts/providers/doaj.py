"""DOAJ (revues en accès libre, sans clé). Le lien « fulltext » est souvent une page HTML :
le téléchargement le rejette alors (signature %PDF vérifiée)."""
from urllib.parse import quote

from net import HTTP, lucene_safe
from records import make_record

URL = "https://doaj.org/api/search/articles/"


def search(query: str, max_results: int, lang: str = None) -> list:
    r = HTTP.get(URL + quote(lucene_safe(query)), params={"pageSize": max_results}, timeout=20)
    r.raise_for_status()
    results = []
    for item in r.json().get("results", []):
        bib = item.get("bibjson", {})
        journal = bib.get("journal", {})
        fulltext = next((l.get("url") for l in bib.get("link", []) if l.get("type") == "fulltext"), "")
        results.append(make_record(
            "doaj", item.get("id", ""), bib.get("title"), [a.get("name") for a in bib.get("author", [])],
            bib.get("year"), bib.get("abstract"), fulltext,
            next((i.get("id") for i in bib.get("identifier", []) if i.get("type") == "doi"), ""),
            item_type="JOUR", container=journal.get("title", ""),
            volume=journal.get("volume"), issue=journal.get("number"),
            pages="-".join(p for p in (bib.get("start_page"), bib.get("end_page")) if p),
            language=journal.get("language"), url=fulltext,
        ))
    return results
