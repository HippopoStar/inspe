#!/usr/bin/env python3
"""Sélection de publications sur un thème : search -> snowball -> rank -> export.

`review` enchaîne tout en une commande (un seul appel d'outil pour l'agent). Dossier de thème produit :
metadata.json (toutes les notices), selection.ris (import Zotero), SELECTION.md (tableau avec liens).
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import export
import rank
import search
import snowball
from providers import SOURCES, NOT_INTEGRATED, available, status


def load(theme_dir: str) -> list:
    with open(os.path.join(theme_dir, "metadata.json"), encoding="utf-8") as f:
        return json.load(f)


def save(theme_dir: str, records: list):
    os.makedirs(theme_dir, exist_ok=True)
    with open(os.path.join(theme_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def dated(path: str) -> str:
    """/workspace/x -> /workspace/2026-11-23_20-14_x : une recherche n'écrase jamais la précédente."""
    head, name = os.path.split(os.path.normpath(path))
    return os.path.join(head, f"{datetime.now():%Y-%m-%d_%H-%M}_{name}")


def cmd_review(a):
    a.dir = dated(a.dir)
    # Requêtes FR et EN obligatoires, sans filtre de langue : les deux langues conviennent toujours.
    queries = a.fr + a.en
    topic, scorer = a.topic or " / ".join(queries), rank.ollama_scorer(a.model)
    records = search.search(queries, a.sources, a.max_results, core=a.core)
    rank.grade(records, topic, scorer)
    added = snowball.snowball(records, a.min_relevance, a.snowball)   # classiques cités par les notices pertinentes
    rank.grade(added, topic, scorer)
    records = rank.order(records + added, a.citation_weight)
    save(a.dir, records)
    keep = rank.selected(records, a.min_relevance, a.top)
    print(f"\n{len(keep)}/{len(records)} publication(s) retenue(s) (pertinence ≥ {a.min_relevance}, {a.top} au plus). "
          f"Dossier : {a.dir}\n")
    print(export.write(keep, a.dir))


def cmd_search(a):
    save(a.dir, search.search(a.query, a.sources, a.max_results, a.lang))


def cmd_rank(a):
    save(a.dir, rank.rank(load(a.dir), a.topic, rank.ollama_scorer(a.model), a.citation_weight))


def cmd_export(a):
    print(export.write(rank.selected(load(a.dir), a.min_relevance, a.top), a.dir))


def cmd_sources(a):
    """Bases accessibles selon les clés fournies ; --check fait une vraie requête par base."""
    for name, base in SOURCES.items():
        line = f"{name:16} {status(name):14} {(base['key'] or '-') + (' (obligatoire)' if base['required'] else ''):32} {base['note']}"
        if a.check and status(name) != "clé manquante":
            try:
                line += f"  -> test OK ({len(base['fn']('education', 1, None))} résultat)"
            except Exception as e:
                line += f"  -> test ÉCHEC {str(e)[:90]}"
        print(line)
    print("\nNon intégrées :\n" + "\n".join(f"  {k} : {v}" for k, v in NOT_INTEGRATED.items()))
    print(f"\nAccessibles ({len(available())}) : {' '.join(available())}")


def source_names(value: str) -> str:
    """Accepte aussi « --sources "hal tel" » : l'agent met parfois la liste entre guillemets."""
    unknown = [n for n in value.split() if n not in SOURCES and n != "all"]
    if unknown:
        raise argparse.ArgumentTypeError(f"base inconnue : {' '.join(unknown)} (choix : {' '.join(SOURCES)} all)")
    return value


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def command(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        if name != "sources":
            p.add_argument("--dir", required=True, help="dossier du thème, ex. /workspace/mon_theme")
        return p

    def search_options(p):
        p.add_argument("--sources", nargs="+", default=["openalex", "hal", "crossref"], type=source_names,
                       help=f"parmi : {' '.join(SOURCES)} ; « all » = toutes les bases accessibles")
        p.add_argument("--max-results", type=int, default=10, help="par requête et par base")

    def rank_options(p, topic_required):
        p.add_argument("--topic", required=topic_required, help="le sujet en une phrase")
        p.add_argument("--model", default=rank.RANK_MODEL)
        p.add_argument("--citation-weight", type=float, default=rank.CITATION_WEIGHT,
                       help="poids des citations : score = pertinence + poids × percentile de citations (0 = pertinence seule)")

    def selection_option(p):
        p.add_argument("--min-relevance", type=int, default=2, help="note minimale (0-3) pour être retenu")
        p.add_argument("--top", type=int, default=20, help="nombre maximal de publications retenues (les mieux classées)")

    p = command("review", cmd_review, "search + rank + export")
    p.add_argument("--fr", nargs="+", required=True, help="requêtes en français")
    p.add_argument("--en", nargs="+", required=True, help="requêtes en anglais")
    p.add_argument("--core", nargs="+", required=True,
                   help="concept central et synonymes, 1 à 3 mots chacun, FR et EN : leurs travaux les plus cités sont ajoutés")
    p.add_argument("--snowball", type=int, default=10,
                   help="nombre maximal de travaux ajoutés parce que plusieurs notices pertinentes les citent (0 = aucun)")
    search_options(p)
    rank_options(p, False)
    selection_option(p)

    p = command("search", cmd_search, "recherche seule -> metadata.json")
    p.add_argument("--query", nargs="+", required=True)
    p.add_argument("--lang", help="filtre de langue ISO (fr, en), HAL et OpenAlex seulement")
    search_options(p)

    rank_options(command("rank", cmd_rank, "noter et classer metadata.json"), True)

    selection_option(command("export", cmd_export, "selection.ris + SELECTION.md"))

    command("sources", cmd_sources, "bases accessibles selon les clés").add_argument(
        "--check", action="store_true", help="tester chaque base par une vraie requête")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.fn(args)
