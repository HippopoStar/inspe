"""Étape 4 : selection.ris (import Zotero, PDF joints) et SELECTION.md (tableau lisible)."""
import os

from pdf import pdf_path
from rank import LABELS


def ris_author(name: str) -> str:
    # ponytail: sans virgule, le dernier mot est pris comme nom de famille ; les noms composés
    # (« Djeumeni Tchamabe ») sont alors mal coupés, à corriger dans Zotero.
    if "," in name or " " not in name.strip():
        return name.strip()
    *given, family = name.split()
    return f"{family}, {' '.join(given)}"


def to_ris(records: list, theme_dir: str) -> str:
    lines = []
    for r in records:
        sp, _, ep = r["pages"].partition("-")
        fields = [("TY", r["type"]), ("TI", r["title"]), *(("AU", ris_author(a)) for a in r["authors"]),
                  ("PY", "" if r["year"] == "0000" else r["year"]), ("T2", r["container"]),
                  ("VL", r["volume"]), ("IS", r["issue"]), ("SP", sp), ("EP", ep), ("LA", r["language"]),
                  ("DO", r["doi"]), ("UR", r["url"] or (f"https://doi.org/{r['doi']}" if r["doi"] else "")),
                  ("AB", r["abstract"]),
                  ("N1", f"Pertinence : {r.get('relevance')}/3 ; citations : "
                         f"{'inconnu' if r['cited_by'] is None else r['cited_by']} ; source : {r['id']}")]
        if os.path.exists(pdf_path(theme_dir, r)):
            fields.append(("L1", os.path.join("pdfs", r["suggested_filename"])))  # relatif au .ris : Zotero joint le PDF
        lines += [f"{tag}  - {value}" for tag, value in fields if value not in (None, "")] + ["ER  - ", ""]
    return "\n".join(lines)


def to_markdown(records: list, theme_dir: str) -> str:
    rows = ["| # | Pertinence | Citations | Percentile | Année | Titre | Auteurs | DOI | PDF |",
            "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(records, 1):
        authors = r["authors"][0] + (" et al." if len(r["authors"]) > 1 else "") if r["authors"] else ""
        pct = r["citation_percentile"]
        pdf = "oui" if os.path.exists(pdf_path(theme_dir, r)) else (f"[lien]({r['pdf_url']})" if r["pdf_url"] else "non")
        cells = (i, f"{r.get('relevance')} ({LABELS.get(r.get('relevance'), '?')})",
                 "?" if r["cited_by"] is None else r["cited_by"], "?" if pct is None else f"{round(pct * 100)} %",
                 r["year"], r["title"], authors, r["doi"], pdf)
        rows.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    return "\n".join(rows) + "\n"


def write(records: list, theme_dir: str) -> str:
    """Écrit les deux fichiers et renvoie le tableau (affiché tel quel par l'agent)."""
    with open(os.path.join(theme_dir, "selection.ris"), "w", encoding="utf-8") as f:
        f.write(to_ris(records, theme_dir))
    table = to_markdown(records, theme_dir)
    with open(os.path.join(theme_dir, "SELECTION.md"), "w", encoding="utf-8") as f:
        f.write(f"# Sélection ({len(records)} publications)\n\n{table}")
    return table
