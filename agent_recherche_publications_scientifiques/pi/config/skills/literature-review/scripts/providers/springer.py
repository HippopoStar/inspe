"""Springer Nature, Meta API v2. Clé obligatoire : https://dev.springernature.com
ponytail: écrit d'après la documentation, non testé faute de clé ; vérifier avec `sources --check`."""
from net import HTTP, secret
from records import make_record

URL = "https://api.springernature.com/meta/v2/json"
TYPES = {"article": "JOUR", "chapter": "CHAP", "book": "BOOK", "conferencepaper": "CONF"}


def _text(value) -> str:
    """L'abstract peut être une chaîne, une liste ou un dict ({"h1": ..., "p": ...})."""
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return str(value or "")


def search(query: str, max_results: int, lang: str = None) -> list:
    r = HTTP.get(URL, params={"q": query, "p": max_results, "api_key": secret("springer_api_key")}, timeout=30)
    r.raise_for_status()
    results = []
    for rec in r.json().get("records", []):
        urls = {u.get("format"): u.get("value") for u in rec.get("url", [])}
        results.append(make_record(
            "springer", rec.get("doi") or rec.get("identifier", ""), rec.get("title"),
            [c.get("creator") for c in rec.get("creators", [])],  # déjà « Nom, Prénom »
            rec.get("publicationDate"), _text(rec.get("abstract")),
            urls.get("pdf", "") if rec.get("openaccess") == "true" else "", rec.get("doi", ""),
            item_type=TYPES.get((rec.get("contentType") or "").lower().replace(" ", ""), "GEN"),
            container=rec.get("publicationName", ""), volume=rec.get("volume"), issue=rec.get("number"),
            pages="-".join(p for p in (rec.get("startingPage"), rec.get("endingPage")) if p),
            language=rec.get("language", ""), url=urls.get("html", ""),
        ))
    return results
