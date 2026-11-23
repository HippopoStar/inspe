"""OpenAlex : recherche, et source unique des citations et des PDF légaux (données Unpaywall incluses).
Clé gratuite exigée depuis février 2026 (openalex.org/settings/api) ; sans clé, quota très réduit."""
from net import HTTP, secret
from records import make_record, normalize_doi

URL = "https://api.openalex.org/works"
TYPES = {"article": "JOUR", "review": "JOUR", "preprint": "JOUR", "letter": "JOUR", "editorial": "JOUR",
         "book": "BOOK", "book-chapter": "CHAP", "dissertation": "THES", "report": "RPRT"}


def _get(**params) -> list:
    if secret("openalex_api_key"):
        params["api_key"] = secret("openalex_api_key")
    r = HTTP.get(URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("results", [])


def _abstract(inverted_index: dict) -> str:
    words = {pos: word for word, positions in (inverted_index or {}).items() for pos in positions}
    return " ".join(words[i] for i in sorted(words))


def _percentile(work: dict):
    return (work.get("citation_normalized_percentile") or {}).get("value")


def _pdf(work: dict) -> str:
    # Uniquement un vrai lien PDF : open_access.oa_url pointe souvent vers une page d'accueil.
    return (work.get("best_oa_location") or {}).get("pdf_url") or ""


def _record(w: dict) -> dict:
    loc, biblio = w.get("primary_location") or {}, w.get("biblio") or {}
    return make_record(
        "openalex", w.get("id", "").rsplit("/", 1)[-1], w.get("title"),
        [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])],
        w.get("publication_year"), _abstract(w.get("abstract_inverted_index")), _pdf(w), w.get("doi"),
        item_type=TYPES.get(w.get("type"), "GEN"),
        container=(loc.get("source") or {}).get("display_name", ""),
        volume=biblio.get("volume"), issue=biblio.get("issue"),
        pages="-".join(p for p in (biblio.get("first_page"), biblio.get("last_page")) if p),
        language=w.get("language"), url=loc.get("landing_page_url") or "",
        cited_by=w.get("cited_by_count"), citation_percentile=_percentile(w),
    )


def search(query: str, max_results: int, lang: str = None) -> list:
    params = {"search": query, "per-page": max_results}
    if lang:
        params["filter"] = f"language:{lang}"
    return [_record(w) for w in _get(**params)]


def most_cited(phrase: str, max_results: int) -> list:
    """Les travaux les plus cités dont le titre contient l'expression exacte : les classiques du sujet.
    Le titre est exigé : trier la recherche plein texte par citations ramène des articles sans rapport
    (PRISMA, NumPy pour « peer learning »)."""
    phrase = " ".join(phrase.replace('"', " ").replace(",", " ").replace("|", " ").split())
    return [_record(w) for w in _get(filter=f'title.search:"{phrase}"', sort="cited_by_count:desc",
                                     **{"per-page": max_results})]


def lookup_dois(dois: list) -> dict:
    """{doi: {cited_by, citation_percentile, pdf_url}} pour une liste de DOI (50 par requête)."""
    dois, found = sorted({normalize_doi(d) for d in dois if d}), {}
    for i in range(0, len(dois), 50):
        for w in _get(filter="doi:" + "|".join(dois[i:i + 50]), **{"per-page": 50},
                      select="doi,cited_by_count,citation_normalized_percentile,best_oa_location"):
            found[normalize_doi(w.get("doi"))] = {"cited_by": w.get("cited_by_count"),
                                                  "citation_percentile": _percentile(w), "pdf_url": _pdf(w)}
    return found
