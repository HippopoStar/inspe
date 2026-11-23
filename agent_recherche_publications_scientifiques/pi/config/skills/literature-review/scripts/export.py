"""Étape 3 : selection.ris (import Zotero) et SELECTION.md (tableau lisible, avec les liens PDF)."""
import os

from rank import LABELS


def ris_author(name: str) -> str:
    # ponytail: sans virgule, le dernier mot est pris comme nom de famille ; les noms composés
    # (« Djeumeni Tchamabe ») sont alors mal coupés, à corriger dans Zotero.
    if "," in name or " " not in name.strip():
        return name.strip()
    *given, family = name.split()
    return f"{family}, {' '.join(given)}"


def to_ris(records: list) -> str:
    lines = []
    for r in records:
        sp, _, ep = r["pages"].partition("-")
        fields = [("TY", r["type"]), ("TI", r["title"]), *(("AU", ris_author(a)) for a in r["authors"]),
                  ("PY", "" if r["year"] == "0000" else r["year"]), ("T2", r["container"]),
                  ("VL", r["volume"]), ("IS", r["issue"]), ("SP", sp), ("EP", ep), ("LA", r["language"]),
                  ("DO", r["doi"]), ("UR", r["url"] or (f"https://doi.org/{r['doi']}" if r["doi"] else "")),
                  ("AB", r["abstract"]),
                  ("N1", f"Pertinence : {r.get('relevance')}/3 ; citations : "
                         f"{'inconnu' if r['cited_by'] is None else r['cited_by']} ; source : {r['id']}"
                         + (f" ; cité par {r['cited_by_results']} notices pertinentes de la liste" if r.get("cited_by_results") else "")
                         + (f" ; PDF : {r['pdf_url']}" if r["pdf_url"] else ""))]
        lines += [f"{tag}  - {value}" for tag, value in fields if value not in (None, "")] + ["ER  - ", ""]
    return "\n".join(lines)


def to_markdown(records: list) -> str:
    # « Ajouté car » : travaux ajoutés par la boule de neige, avec le nombre de notices pertinentes qui les citent.
    rows = ["| # | Pertinence | Citations | Percentile | Ajouté car | Année | Titre | Auteurs | DOI | PDF |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(records, 1):
        authors = r["authors"][0] + (" et al." if len(r["authors"]) > 1 else "") if r["authors"] else ""
        pct = r["citation_percentile"]
        pdf = f"[lien]({r['pdf_url']})" if r["pdf_url"] else "non"
        cells = (i, f"{r.get('relevance')} ({LABELS.get(r.get('relevance'), '?')})",
                 "?" if r["cited_by"] is None else r["cited_by"], "?" if pct is None else f"{round(pct * 100)} %",
                 f"cité par {r['cited_by_results']}" if r.get("cited_by_results") else "",
                 r["year"], r["title"], authors, r["doi"], pdf)
        rows.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    return "\n".join(rows) + "\n"


def write(records: list, theme_dir: str) -> str:
    """Écrit les deux fichiers et renvoie le tableau (affiché par la commande)."""
    with open(os.path.join(theme_dir, "selection.ris"), "w", encoding="utf-8") as f:
        f.write(to_ris(records))
    table = to_markdown(records)
    with open(os.path.join(theme_dir, "SELECTION.md"), "w", encoding="utf-8") as f:
        f.write(f"# Sélection ({len(records)} publications)\n\n{table}")
    return table
