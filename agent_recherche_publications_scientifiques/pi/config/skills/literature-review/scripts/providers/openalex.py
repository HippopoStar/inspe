import os
from utils import HTTP_SESSION, build_url, make_record, normalize_doi

# Depuis le 13/02/2026, OpenAlex exige une clé API gratuite (openalex.org/settings/api) ;
# sans clé, le quota est fortement réduit. Le paramètre mailto est ignoré.
API_KEY = os.environ.get("OPENALEX_API_KEY", "")

TYPES = {
    "article": "JOUR", "review": "JOUR", "preprint": "JOUR", "letter": "JOUR", "editorial": "JOUR",
    "book": "BOOK", "book-chapter": "CHAP", "dissertation": "THES", "report": "RPRT",
}


def _params(**params) -> dict:
    if API_KEY:
        params["api_key"] = API_KEY
    return params


def _reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    words = {pos: word for word, positions in inverted_index.items() for pos in positions}
    return " ".join(words[i] for i in sorted(words))


def _percentile(w: dict):
    """Percentile de citations normalisé par année et domaine (0–1) : corrige l'avantage des vieux articles."""
    return (w.get("citation_normalized_percentile") or {}).get("value")


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.openalex.org", "/works")
    params = _params(search=query, **{"per-page": max_results})
    if lang:
        params["filter"] = f"language:{lang}"

    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for w in r.json().get("results", []):
        authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])]
        # Seulement un vrai lien PDF : oa_url pointe souvent vers une page d'accueil ou un doi.org
        pdf_url = (w.get("best_oa_location") or {}).get("pdf_url") or ""
        loc = w.get("primary_location") or {}
        biblio = w.get("biblio") or {}
        pages = "-".join(p for p in (biblio.get("first_page"), biblio.get("last_page")) if p)
        results.append(make_record(
            source="openalex",
            doc_id=w.get("id", "").split("/")[-1],
            title=w.get("title", ""),
            authors=authors,
            year=w.get("publication_year"),
            abstract=_reconstruct_abstract(w.get("abstract_inverted_index")),
            pdf_url=pdf_url,
            doi=w.get("doi", ""),
            item_type=TYPES.get(w.get("type"), "GEN"),
            container=(loc.get("source") or {}).get("display_name", ""),
            volume=biblio.get("volume"),
            issue=biblio.get("issue"),
            pages=pages,
            language=w.get("language"),
            url=loc.get("landing_page_url") or "",
            cited_by=w.get("cited_by_count"),
            citation_percentile=_percentile(w),
        ))
    return results


def citations_by_doi(dois: list) -> dict:
    """{doi: (cited_by_count, percentile)} pour compléter les notices sans citations (HAL, ERIC, DOAJ…)."""
    found = {}
    dois = sorted({normalize_doi(d) for d in dois if d})
    url = build_url("api.openalex.org", "/works")
    for i in range(0, len(dois), 50):  # 50 DOI max par filtre
        chunk = dois[i:i + 50]
        params = _params(filter="doi:" + "|".join(chunk), select="doi,cited_by_count,citation_normalized_percentile",
                         **{"per-page": 50})
        r = HTTP_SESSION.get(url, params=params, timeout=20)
        r.raise_for_status()
        for w in r.json().get("results", []):
            found[normalize_doi(w.get("doi", ""))] = (w.get("cited_by_count"), _percentile(w))
    return found
