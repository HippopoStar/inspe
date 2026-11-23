import re
import time
import unicodedata
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PiAcademicResearch/1.0)",
    "Accept": "application/json",
}


class RateLimitedSession(requests.Session):
    """Session HTTP imposant un délai minimal entre deux requêtes et gérant les erreurs 429."""

    def __init__(self, min_delay: float = 1.2):
        super().__init__()
        self.min_delay = min_delay
        self._last_request_time = 0.0
        self.headers.update(HEADERS)

        retry_strategy = Retry(
            total=3,
            backoff_factor=2.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def request(self, method, url, *args, **kwargs):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        response = super().request(method, url, *args, **kwargs)
        self._last_request_time = time.monotonic()
        return response


HTTP_SESSION = RateLimitedSession(min_delay=1.2)


def build_url(domain: str, path: str) -> str:
    clean_domain = domain.strip().strip("/")
    clean_path = "/" + path.strip().lstrip("/") if path else ""
    return f"https://{clean_domain}{clean_path}"


def sanitize_lucene_query(query: str) -> str:
    """Nettoie les caractères réservés Solr/Lucene/Elasticsearch qui provoquent des erreurs HTTP 400."""
    cleaned = re.sub(r'["():\[\]{}!^~*?\\/]', " ", query or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def sanitize_filename(text: str, max_len: int = 50) -> str:
    text = unicodedata.normalize("NFKD", text or "untitled").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_len].strip("_") or "document"


def normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    doi = doi.lower().strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", text)


def first(value):
    """Premier élément si la valeur est une liste (les API Solr renvoient souvent des listes)."""
    if isinstance(value, list):
        return value[0] if value else ""
    return value if value is not None else ""


def make_record(source: str, doc_id: str, title: str, authors: list, year, abstract: str, pdf_url: str, doi: str = "",
                *, item_type: str = "GEN", container: str = "", volume="", issue="", pages: str = "",
                language: str = "", url: str = "", cited_by=None, citation_percentile=None) -> dict:
    """Notice normalisée. `item_type` est un code de type RIS (JOUR, THES, CHAP, BOOK, CONF, RPRT, GEN),
    réutilisé tel quel par l'export Zotero."""
    authors = [a for a in (authors or []) if a]
    first_full = authors[0] if authors else ""
    first_author = first_full.split()[-1] if first_full.strip() else "Unknown"
    year_str = str(year) if year else "0000"
    safe_title = sanitize_filename(title, 45)
    filename = f"{year_str}_{sanitize_filename(first_author, 20)}_{safe_title}.pdf"
    return {
        "id": f"{source}:{doc_id}",
        "source": source,
        "type": item_type or "GEN",
        "title": (title or "").replace("\n", " ").strip(),
        "authors": authors,  # liste complète : Zotero en a besoin
        "year": year_str,
        "container": (first(container) or "").strip(),
        "volume": str(first(volume) or ""),
        "issue": str(first(issue) or ""),
        "pages": str(first(pages) or ""),
        "language": str(first(language) or ""),
        "doi": normalize_doi(doi),
        "url": url or "",
        "abstract": (abstract or "").replace("\n", " ").strip(),  # complet ; tronqué seulement pour le LLM
        "pdf_url": pdf_url or "",
        "cited_by": cited_by,  # None = inconnu (≠ 0)
        "citation_percentile": citation_percentile,
        "suggested_filename": filename,
    }

