"""ERIC (sciences de l'éducation, sans clé)."""
from net import HTTP, lucene_safe
from records import make_record

URL = "https://api.ies.ed.gov/eric/"
FIELDS = "id,title,author,publicationdateyear,description,url,e_fulltextauth,source,publicationtype,language"
TYPES = {"Journal Articles": "JOUR", "Dissertations": "THES", "Books": "BOOK", "Reports": "RPRT"}


def _type(pub_types: list) -> str:
    joined = " ".join(pub_types or [])
    return next((ris for label, ris in TYPES.items() if label in joined), "GEN")


def search(query: str, max_results: int, lang: str = None, boolean: bool = False) -> list:
    """boolean : `query` est une équation déjà sûre (search.equation), passée telle quelle."""
    r = HTTP.get(URL, timeout=20, params={"search": query if boolean else lucene_safe(query), "rows": max_results,
                                          "format": "json", "fields": FIELDS})
    r.raise_for_status()
    results = []
    for d in r.json().get("response", {}).get("docs", []):
        eric_id = d.get("id", "")
        results.append(make_record(
            # ERIC termine une liste d'auteurs tronquée par « And Others » : ce n'est pas un auteur.
            "eric", eric_id, d.get("title"), [a for a in d.get("author") or [] if a != "And Others"],
            d.get("publicationdateyear"), d.get("description"),
            # Le champ `url` est une page éditeur, pas un PDF.
            f"https://files.eric.ed.gov/fulltext/{eric_id}.pdf" if d.get("e_fulltextauth") == 1 else "",
            item_type=_type(d.get("publicationtype")), container=d.get("source", ""),
            language=d.get("language"), url=d.get("url") or f"https://eric.ed.gov/?id={eric_id}",
        ))
    return results
