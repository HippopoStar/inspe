from utils import HTTP_SESSION, build_url, make_record


def _reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    words = {pos: word for word, positions in inverted_index.items() for pos in positions}
    return " ".join(words[i] for i in sorted(words))


def search(query: str, max_results: int, lang: str = None) -> list:
    url = build_url("api.openalex.org", "/works")
    params = {"search": query, "per-page": max_results}
    if lang:
        params["filter"] = f"language:{lang}"

    r = HTTP_SESSION.get(url, params=params, timeout=20)
    r.raise_for_status()

    results = []
    for w in r.json().get("results", []):
        authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])]
        oa = w.get("open_access") or {}
        best_loc = w.get("best_oa_location") or {}
        pdf_url = best_loc.get("pdf_url") or oa.get("oa_url") or ""
        results.append(make_record(
            source="openalex",
            doc_id=w.get("id", "").split("/")[-1],
            title=w.get("title", ""),
            authors=authors,
            year=w.get("publication_year"),
            abstract=_reconstruct_abstract(w.get("abstract_inverted_index")),
            pdf_url=pdf_url,
            doi=w.get("doi", ""),
        ))
    return results

