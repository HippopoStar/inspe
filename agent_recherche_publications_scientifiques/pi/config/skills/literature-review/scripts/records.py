"""La notice : format commun à toutes les bases, et fusion des doublons."""
import re
import unicodedata

# Types RIS, repris tels quels par l'export Zotero.
RIS_TYPES = ("JOUR", "THES", "CHAP", "BOOK", "CONF", "RPRT", "GEN")


def first(value):
    """Premier élément si `value` est une liste (les API Solr renvoient souvent des listes)."""
    if isinstance(value, list):
        return value[0] if value else ""
    return "" if value is None else value


def ascii_slug(text: str, max_len: int) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[-\s]+", "_", re.sub(r"[^\w\s-]", "", text).strip())
    return text[:max_len].strip("_") or "document"


def normalize_doi(doi: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").lower().strip())


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", ascii_slug(title, 10_000).lower())


def make_record(source: str, doc_id: str, title: str, authors: list, year, abstract: str = "",
                pdf_url: str = "", doi: str = "", *, item_type: str = "GEN", container="", volume="",
                issue="", pages="", language="", url: str = "", cited_by=None, citation_percentile=None) -> dict:
    authors = [a for a in (authors or []) if a]
    year = str(year)[:4] if year else "0000"
    return {
        "id": f"{source}:{doc_id}",
        "source": source,
        "type": item_type if item_type in RIS_TYPES else "GEN",
        "title": " ".join((first(title) or "").split()),
        "authors": authors,
        "year": year,
        "container": str(first(container) or "").strip(),
        "volume": str(first(volume) or ""),
        "issue": str(first(issue) or ""),
        "pages": str(first(pages) or ""),
        "language": str(first(language) or ""),
        "doi": normalize_doi(doi),
        "url": url or "",
        "abstract": " ".join((abstract or "").split()),
        "pdf_url": pdf_url or "",
        "cited_by": cited_by,                        # None = inconnu, différent de 0
        "citation_percentile": citation_percentile,  # 0-1, corrigé de l'âge et du domaine (OpenAlex)
    }


def _fill_gaps(target: dict, other: dict):
    for key, value in other.items():
        if target.get(key) in (None, "", []) and value not in (None, "", []):
            target[key] = value


def deduplicate(records: list) -> list:
    """Fusionne les notices de même DOI ou de même titre ; garde celle qui a un PDF et complète ses champs vides."""
    unique, position = [], {}
    for rec in records:
        keys = [k for k in (f"doi:{rec['doi']}" if rec["doi"] else "",
                            f"title:{normalize_title(rec['title'])}" if rec["title"] else "") if k]
        pos = next((position[k] for k in keys if k in position), None)
        if pos is None:
            pos = len(unique)
            unique.append(rec)
        else:
            kept = unique[pos]
            if rec["pdf_url"] and not kept["pdf_url"]:
                kept, rec = rec, kept
                unique[pos] = kept
            _fill_gaps(kept, rec)
        for k in keys:
            position[k] = pos
    return unique
