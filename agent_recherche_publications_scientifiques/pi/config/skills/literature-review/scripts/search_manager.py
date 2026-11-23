#!/usr/bin/env python3
"""Sélection de publications : recherche multi-bases -> notation de pertinence -> PDF -> export Zotero.

Tout le travail déterministe est ici ; le LLM de Pi ne fait que choisir les mots-clés et lancer `review`.
Un dossier de thème contient : metadata.json, pdfs/, selection.ris (import Zotero), SELECTION.md.
"""
import argparse
import json
import os
import re
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils import HTTP_SESSION, normalize_doi, normalize_title
from providers import PROVIDERS
from providers.openalex import citations_by_doi

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
RANK_MODEL = os.environ.get("RANK_MODEL", "qwen3:4b")
RELEVANCE_LABELS = {0: "hors sujet", 1: "lien indirect", 2: "pertinent", 3: "au cœur du sujet"}


# ---------------------------------------------------------------- fichiers

def meta_path(theme_dir: str) -> str:
    return os.path.join(theme_dir, "metadata.json")


def load(theme_dir: str) -> list:
    with open(meta_path(theme_dir), "r", encoding="utf-8") as f:
        return json.load(f)


def save(theme_dir: str, records: list):
    os.makedirs(theme_dir, exist_ok=True)
    with open(meta_path(theme_dir), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------- recherche

def _merge(keep: dict, other: dict):
    """Complète les champs vides de `keep` avec ceux de `other` (abstract, citations, revue…)."""
    for k, v in other.items():
        if keep.get(k) in (None, "", []) and v not in (None, "", []):
            keep[k] = v


def deduplicate_records(records: list) -> list:
    """Fusionne les doublons (même DOI OU même titre normalisé) ; garde de préférence la notice avec PDF."""
    unique, index = [], {}
    for rec in records:
        keys = [f"title:{normalize_title(rec.get('title', ''))}"]
        if rec.get("doi"):
            keys.append(f"doi:{normalize_doi(rec['doi'])}")
        keys = [k for k in keys if k != "title:"]
        pos = next((index[k] for k in keys if k in index), None)
        if pos is None:
            pos = len(unique)
            unique.append(rec)
        else:
            existing = unique[pos]
            if not existing.get("pdf_url") and rec.get("pdf_url"):
                unique[pos] = rec
                _merge(rec, existing)
            else:
                _merge(existing, rec)
        for k in keys:
            index[k] = pos
    return unique


def enrich_citations(records: list):
    """Prend les citations d'OpenAlex pour toute notice avec DOI sans percentile (HAL, Crossref, S2, DOAJ…) :
    une seule source de comptage, sinon les chiffres de bases différentes ne sont pas comparables."""
    missing = [r["doi"] for r in records if r.get("doi") and r.get("citation_percentile") is None]
    if not missing:
        return
    try:
        found = citations_by_doi(missing)
    except Exception as e:
        print(f"[citations] OpenAlex indisponible : {e}")
        return
    for r in records:
        if r.get("doi") in found and r.get("citation_percentile") is None:
            r["cited_by"], r["citation_percentile"] = found[r["doi"]]
    print(f"[citations] {len(found)}/{len(set(missing))} notices complétées via OpenAlex.")


def run_search(queries: list, sources: list, lang, max_results: int) -> list:
    raw = []
    for query in queries:
        for src in sources:
            try:
                res = PROVIDERS[src](query, max_results, lang)
                print(f"[{src}] « {query} » : {len(res)} résultats.")
                raw.extend(res)
            except Exception as e:
                extra = ""
                if getattr(e, "response", None) is not None:
                    extra = f" | HTTP {e.response.status_code}: {e.response.text[:150]!r}"
                print(f"[{src}] Erreur API : {e}{extra}")
    records = deduplicate_records(raw)
    print(f"TOTAL : {len(records)} notices uniques ({len(raw) - len(records)} doublon(s) fusionné(s)).")
    enrich_citations(records)
    return records


# ---------------------------------------------------------------- pertinence

def build_prompt(topic: str, rec: dict) -> str:
    return (
        f"Sujet de recherche : {topic}\n\n"
        f"Titre : {rec.get('title', '')}\n"
        f"Résumé : {(rec.get('abstract') or '(aucun)')[:1500]}\n\n"
        "Note la pertinence de ce document pour le sujet :\n"
        "0 = hors sujet ; 1 = lien indirect ; 2 = pertinent ; 3 = au cœur du sujet.\n"
        "Un document qui reprend les mots du sujet sans le traiter vaut 0 ou 1.\n"
        'Réponds uniquement en JSON : {"score": <0-3>}'
    )


def parse_score(text: str):
    try:
        score = int(json.loads(text)["score"])
    except (ValueError, KeyError, TypeError):
        m = re.search(r"[0-3]", text or "")
        if not m:
            return None
        score = int(m.group())
    return max(0, min(3, score))


def ollama_scorer(model: str):
    def score(topic: str, rec: dict):
        r = requests.post(f"{OLLAMA_HOST}/api/chat", timeout=180, json={
            "model": model,
            "messages": [{"role": "user", "content": build_prompt(topic, rec)}],
            "stream": False,
            "think": False,  # pas de « réflexion » : une note courte suffit
            "format": {"type": "object", "properties": {"score": {"type": "integer"}}, "required": ["score"]},
            "options": {"temperature": 0},
        })
        r.raise_for_status()
        return parse_score(r.json()["message"]["content"])
    return score


def sort_key(rec: dict):
    # ponytail: tri lexicographique pertinence > percentile > citations brutes ; inconnu (None) passe
    # après les valeurs connues. Remplacer par un score pondéré si le classement ne convient pas.
    def val(x):
        return -1 if x is None else x
    return (val(rec.get("relevance")), val(rec.get("citation_percentile")), val(rec.get("cited_by")))


def rank_records(records: list, topic: str, scorer) -> list:
    for i, rec in enumerate(records, 1):
        try:
            rec["relevance"] = scorer(topic, rec)
        except Exception as e:
            print(f"[rank] {rec['id']} : échec ({e})")
            rec["relevance"] = None
        print(f"[rank] {i}/{len(records)} {rec['relevance']} {rec['title'][:70]}")
    return sorted(records, key=sort_key, reverse=True)


def selected(records: list, min_relevance: int) -> list:
    return [r for r in records if (r.get("relevance") or 0) >= min_relevance]


# ---------------------------------------------------------------- PDF

def download_pdfs(records: list, pdf_dir: str):
    os.makedirs(pdf_dir, exist_ok=True)
    ok = 0
    for item in records:
        filepath = os.path.join(pdf_dir, item["suggested_filename"])
        if os.path.exists(filepath):
            ok += 1
            continue
        if not item.get("pdf_url"):
            continue
        try:
            resp = HTTP_SESSION.get(item["pdf_url"], timeout=30, allow_redirects=True)
            resp.raise_for_status()
            if b"%PDF" not in resp.content[:1024]:
                if b"not a bot" in resp.content[:2000]:
                    # HAL protège ses fichiers par une page anti-robot : téléchargement manuel (lien dans SELECTION.md)
                    print(f"BLOQUÉ (anti-robot) : {item['id']} -> à télécharger à la main : {item['pdf_url']}")
                else:
                    print(f"IGNORÉ (contenu non-PDF) : {item['id']}")
                continue
            with open(filepath, "wb") as f:
                f.write(resp.content)
            ok += 1
        except Exception as e:
            print(f"ÉCHEC {item['id']} : {e}")
    print(f"PDF : {ok}/{len(records)} disponibles dans {pdf_dir}")


# ---------------------------------------------------------------- export

def ris_author(name: str) -> str:
    # ponytail: le dernier mot est pris comme nom de famille ; les noms composés sans virgule
    # (« Djeumeni Tchamabe ») sont mal coupés, à corriger dans Zotero si besoin.
    if "," in name or " " not in name.strip():
        return name.strip()
    *given, family = name.split()
    return f"{family}, {' '.join(given)}"


def to_ris(records: list, theme_dir: str) -> str:
    lines = []
    for r in records:
        def add(tag, value):
            if value not in (None, ""):
                lines.append(f"{tag}  - {value}")
        add("TY", r.get("type") or "GEN")
        add("TI", r.get("title"))
        for a in r.get("authors", []):
            add("AU", ris_author(a))
        add("PY", r.get("year") if r.get("year") != "0000" else "")
        add("T2", r.get("container"))
        add("VL", r.get("volume"))
        add("IS", r.get("issue"))
        if r.get("pages"):
            sp, _, ep = r["pages"].partition("-")
            add("SP", sp)
            add("EP", ep)
        add("LA", r.get("language"))
        add("DO", r.get("doi"))
        add("UR", r.get("url") or (f"https://doi.org/{r['doi']}" if r.get("doi") else ""))
        add("AB", r.get("abstract"))
        add("N1", f"Pertinence : {r.get('relevance')}/3 ; citations : "
                  f"{'inconnu' if r.get('cited_by') is None else r['cited_by']} ; source : {r.get('id')}")
        pdf = os.path.join("pdfs", r["suggested_filename"])
        if os.path.exists(os.path.join(theme_dir, pdf)):
            add("L1", pdf)  # chemin relatif au fichier .ris : Zotero joint le PDF à l'import
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)


def to_markdown(records: list, theme_dir: str) -> str:
    def cell(s):
        return str(s).replace("|", "/").replace("\n", " ")
    rows = ["| # | Pertinence | Citations | Percentile | Année | Titre | Auteurs | DOI | PDF |",
            "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(records, 1):
        authors = r.get("authors", [])
        auth = authors[0] + (" et al." if len(authors) > 1 else "") if authors else ""
        pct = r.get("citation_percentile")
        has_pdf = os.path.exists(os.path.join(theme_dir, "pdfs", r["suggested_filename"]))
        rows.append("| " + " | ".join(cell(x) for x in (
            i,
            f"{r.get('relevance')} ({RELEVANCE_LABELS.get(r.get('relevance'), '?')})",
            "?" if r.get("cited_by") is None else r["cited_by"],
            "?" if pct is None else f"{round(pct * 100)} %",
            r.get("year"), r.get("title"), auth, r.get("doi") or "",
            "oui" if has_pdf else (f"[lien]({r['pdf_url']})" if r.get("pdf_url") else "non"),
        )) + " |")
    return "\n".join(rows) + "\n"


def export(records: list, theme_dir: str) -> str:
    with open(os.path.join(theme_dir, "selection.ris"), "w", encoding="utf-8") as f:
        f.write(to_ris(records, theme_dir))
    table = to_markdown(records, theme_dir)
    with open(os.path.join(theme_dir, "SELECTION.md"), "w", encoding="utf-8") as f:
        f.write(f"# Sélection ({len(records)} publications)\n\n" + table)
    return table


# ---------------------------------------------------------------- commandes

def cmd_search(a):
    save(a.dir, run_search(a.query, a.sources, a.lang, a.max_results))


def cmd_rank(a):
    save(a.dir, rank_records(load(a.dir), a.topic, ollama_scorer(a.model)))


def cmd_download(a):
    records = load(a.dir)
    if a.ids:
        records = [r for r in records if r["id"] in set(a.ids)]
    else:
        records = selected(records, a.min_relevance)
    download_pdfs(records, os.path.join(a.dir, "pdfs"))


def cmd_export(a):
    print(export(selected(load(a.dir), a.min_relevance), a.dir))


def cmd_review(a):
    """Tout en une commande : un seul appel d'outil pour l'agent."""
    records = run_search(a.query, a.sources, a.lang, a.max_results)
    records = rank_records(records, a.topic or " / ".join(a.query), ollama_scorer(a.model))
    save(a.dir, records)
    keep = selected(records, a.min_relevance)
    download_pdfs(keep, os.path.join(a.dir, "pdfs"))
    print(f"\n{len(keep)} publication(s) retenue(s) sur {len(records)} (pertinence ≥ {a.min_relevance}).")
    print(f"Zotero : importer {os.path.join(a.dir, 'selection.ris')}\n")
    print(export(keep, a.dir))


def build_parser():
    parser = argparse.ArgumentParser(description="Sélection de publications scientifiques")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p, search=False, rank=False, select=False):
        p.add_argument("--dir", required=True, help="Dossier du thème, ex. /workspace/mon_theme")
        if search:
            p.add_argument("--query", nargs="+", required=True, help="Une ou plusieurs requêtes (FR et EN)")
            p.add_argument("--sources", nargs="+", default=["openalex", "hal"], choices=list(PROVIDERS))
            p.add_argument("--lang", default=None, help="Filtre langue ISO (fr, en) ; omettre pour tout garder")
            p.add_argument("--max-results", type=int, default=10, help="Résultats max par requête et par base")
        if rank:
            p.add_argument("--topic", help="Le sujet en une phrase (défaut : les requêtes)")
            p.add_argument("--model", default=RANK_MODEL)
        if select:
            p.add_argument("--min-relevance", type=int, default=2, help="Note minimale (0-3) pour être retenu")

    common(sub.add_parser("review", help="search + rank + download + export"), search=True, rank=True, select=True)
    common(sub.add_parser("search"), search=True)
    p = sub.add_parser("rank")
    common(p, rank=True)
    p.set_defaults(topic=None)
    p = sub.add_parser("download")
    common(p, select=True)
    p.add_argument("--ids", nargs="+", help="Télécharger ces id précis au lieu de la sélection")
    common(sub.add_parser("export"), select=True)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.cmd == "rank" and not args.topic:
        sys.exit("rank : --topic est obligatoire")
    {"review": cmd_review, "search": cmd_search, "rank": cmd_rank,
     "download": cmd_download, "export": cmd_export}[args.cmd](args)
