from utils import HTTP_SESSION, build_url, make_record, secret

# Springer Nature Meta API v2. Clé gratuite obligatoire : https://dev.springernature.com
# ponytail: écrit d'après la documentation, non testé faute de clé ; vérifier avec `sources --check`.
TYPES = {"article": "JOUR", "chapter": "CHAP", "book": "BOOK", "conferencepaper": "CONF"}


def _text(value) -> str:
    if isinstance(value, dict):  # l'abstract est parfois {"h1": ..., "p": ...}
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return str(value or "")


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.springernature.com", "/meta/v2/json")
    params = {"q": query, "p": max_results, "api_key": secret("springer_api_key")}
    r = HTTP_SESSION.get(url, params=params, timeout=30)
    r.raise_for_status()

    results = []
    for rec in r.json().get("records", []):
        urls = {u.get("format"): u.get("value") for u in rec.get("url", [])}
        pages = "-".join(p for p in (rec.get("startingPage"), rec.get("endingPage")) if p)
        results.append(make_record(
            source="springer",
            doc_id=rec.get("doi") or rec.get("identifier", ""),
            title=rec.get("title", ""),
            authors=[c.get("creator", "") for c in rec.get("creators", [])],  # déjà « Nom, Prénom »
            year=(rec.get("publicationDate") or "")[:4],
            abstract=_text(rec.get("abstract")),
            pdf_url=urls.get("pdf", "") if rec.get("openaccess") == "true" else "",
            doi=rec.get("doi", ""),
            item_type=TYPES.get((rec.get("contentType") or "").lower().replace(" ", ""), "GEN"),
            container=rec.get("publicationName", ""),
            volume=rec.get("volume"),
            issue=rec.get("number"),
            pages=pages,
            language=rec.get("language", ""),
            url=urls.get("html", ""),
        ))
    return results
