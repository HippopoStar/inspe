#!/usr/bin/env python3
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils import HTTP_SESSION, normalize_doi, normalize_title
from providers import PROVIDERS


def deduplicate_records(records: list[dict]) -> list[dict]:
    """Fusionne les doublons (par DOI ou titre normalisé) en privilégiant ceux avec un PDF."""
    seen = {}
    unique_records = []

    for rec in records:
        doi_key = f"doi:{normalize_doi(rec.get('doi', ''))}" if rec.get("doi") else ""
        title_key = f"title:{normalize_title(rec.get('title', ''))}"
        key = doi_key or title_key

        if not key or key == "title:":
            unique_records.append(rec)
            continue

        if key not in seen:
            seen[key] = len(unique_records)
            unique_records.append(rec)
        else:
            existing_idx = seen[key]
            existing = unique_records[existing_idx]
            # Remplace l'existant si le nouveau possède un lien PDF alors que l'ancien n'en a pas
            if not existing.get("pdf_url") and rec.get("pdf_url"):
                unique_records[existing_idx] = rec
            # Sinon, complète l'abstract s'il était vide
            elif not existing.get("abstract") and rec.get("abstract"):
                existing["abstract"] = rec["abstract"]

    return unique_records


def cmd_search(args):
    raw_results = []
    for src in args.sources:
        search_fn = PROVIDERS.get(src)
        if not search_fn:
            print(f"[{src}] Connecteur introuvable.")
            continue
        try:
            res = search_fn(args.query, args.max_results, args.lang)
            print(f"[{src}] {len(res)} résultats trouvés.")
            raw_results.extend(res)
        except Exception as e:
            extra = ""
            if hasattr(e, "response") and e.response is not None:
                extra = f" | HTTP {e.response.status_code}: {e.response.text[:150]!r}"
            print(f"[{src}] Erreur API : {e}{extra}")

    final_results = deduplicate_records(raw_results)
    duplicates_removed = len(raw_results) - len(final_results)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    print(f"TOTAL : {len(final_results)} articles uniques enregistrés ({duplicates_removed} doublon(s) filtré(s)) dans {args.out}")


def cmd_download(args):
    with open(args.meta, "r", encoding="utf-8") as f:
        papers = json.load(f)

    target_ids = set(args.ids)
    os.makedirs(args.dir, exist_ok=True)
    downloaded = 0

    for item in papers:
        if item["id"] in target_ids:
            filepath = os.path.join(args.dir, item["suggested_filename"])
            if os.path.exists(filepath):
                print(f"DÉJÀ PRÉSENT : {filepath}")
                downloaded += 1
                continue

            pdf_url = item.get("pdf_url")
            if not pdf_url:
                print(f"IGNORÉ (aucun lien PDF) : {item['id']}")
                continue

            try:
                # Utilise HTTP_SESSION (délai automatique entre téléchargements + gestion 429)
                resp = HTTP_SESSION.get(pdf_url, timeout=30, allow_redirects=True)
                resp.raise_for_status()
                if b"%PDF" not in resp.content[:1024]:
                    print(f"IGNORÉ (contenu non-PDF) : {item['id']} -> {pdf_url}")
                    continue
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"TÉLÉCHARGÉ : {filepath}")
                downloaded += 1
            except Exception as e:
                print(f"ÉCHEC {item['id']} : {e}")

    print(f"Terminé : {downloaded}/{len(target_ids)} PDF disponibles dans {args.dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrateur de recherche académique modulaire")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_s = sub.add_parser("search")
    p_s.add_argument("--query", required=True, help="Requête de recherche")
    p_s.add_argument(
        "--sources", nargs="+", default=["openalex", "hal"],
        choices=list(PROVIDERS.keys()),
        help="Bases à interroger"
    )
    p_s.add_argument("--lang", default=None, help="Filtre langue ISO (ex: fr, en)")
    p_s.add_argument("--max-results", type=int, default=8, help="Résultats max par base")
    p_s.add_argument("--out", required=True, help="Chemin du fichier JSON de sortie")

    p_d = sub.add_parser("download")
    p_d.add_argument("--meta", required=True, help="Fichier JSON généré par search")
    p_d.add_argument("--ids", nargs="+", required=True, help="Liste des champs 'id' à télécharger")
    p_d.add_argument("--dir", required=True, help="Dossier de destination des PDF")

    parsed = parser.parse_args()
    if parsed.cmd == "search":
        cmd_search(parsed)
    elif parsed.cmd == "download":
        cmd_download(parsed)

