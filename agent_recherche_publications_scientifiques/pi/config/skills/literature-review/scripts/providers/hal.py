"""HAL et ses portails (portal="tel" : thèses, "dumas" : mémoires de master). Sans clé.
Attention : producedDateY_i peut être la date de dépôt plutôt que de première publication."""
from net import HTTP, lucene_safe
from records import make_record, first

URL = "https://api.archives-ouvertes.fr/search/"
TYPES = {"ART": "JOUR", "COMM": "CONF", "THESE": "THES", "HDR": "THES", "MEM": "THES",
         "OUV": "BOOK", "COUV": "CHAP", "REPORT": "RPRT"}
FIELDS = ("halId_s,title_s,authFullName_s,producedDateY_i,abstract_s,fileMain_s,doiId_s,docType_s,"
          "journalTitle_s,bookTitle_s,conferenceTitle_s,volume_s,issue_s,page_s,language_s,uri_s")


def search(query: str, max_results: int, lang: str = None, portal: str = "", source: str = "hal") -> list:
    q = f"({lucene_safe(query)})" + (f" AND language_s:{lang}" if lang else "")
    r = HTTP.get(URL + (f"{portal}/" if portal else ""), timeout=20,
                 params={"q": q, "rows": max_results, "wt": "json", "fl": FIELDS})
    r.raise_for_status()
    return [make_record(
        source, d.get("halId_s", ""), d.get("title_s"), d.get("authFullName_s"), d.get("producedDateY_i"),
        first(d.get("abstract_s")), d.get("fileMain_s", ""), d.get("doiId_s", ""),
        item_type=TYPES.get(d.get("docType_s"), "GEN"),
        container=d.get("journalTitle_s") or d.get("bookTitle_s") or d.get("conferenceTitle_s") or "",
        volume=d.get("volume_s"), issue=d.get("issue_s"), pages=d.get("page_s"),
        language=d.get("language_s"), url=d.get("uri_s", ""),
    ) for d in r.json().get("response", {}).get("docs", [])]
