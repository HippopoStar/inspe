#!/usr/bin/env python3
"""Vérifications hors ligne (aucun appel réseau) : python3 test_search_manager.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import make_record
import search_manager as sm


def rec(source, doc_id, title, doi="", pdf="", abstract="", **kw):
    return make_record(source, doc_id, title, ["Béatrice Drot-Delange", "Gabriel Parriaux"], 2013,
                       abstract, pdf, doi, **kw)


def test_dedup_merges_doi_and_title():
    hal = rec("hal", "1", "Enseigner l'informatique débranchée", abstract="résumé HAL")
    oa = rec("openalex", "W1", "Enseigner l’informatique débranchée !", doi="10.1/X", pdf="https://x/a.pdf",
             cited_by=12, citation_percentile=0.8)
    cr = rec("crossref", "10.1/x", "Autre titre", doi="https://doi.org/10.1/x")
    out = sm.deduplicate_records([hal, oa, cr])
    assert len(out) == 1, out
    r = out[0]
    assert r["pdf_url"] == "https://x/a.pdf"      # la notice avec PDF gagne
    assert r["abstract"] == "résumé HAL"           # sans perdre l'abstract de l'autre
    assert r["cited_by"] == 12 and r["doi"] == "10.1/x"


def test_parse_score():
    assert sm.parse_score('{"score": 2}') == 2
    assert sm.parse_score('{"score": 7}') == 3
    assert sm.parse_score("note : 1") == 1
    assert sm.parse_score("aucune idée") is None


def test_rank_order_and_selection():
    a = rec("hal", "a", "A", cited_by=None)
    b = rec("hal", "b", "B", cited_by=500, citation_percentile=0.99)
    c = rec("hal", "c", "C", cited_by=3, citation_percentile=0.2)
    d = rec("hal", "d", "D")
    scores = {"A": 3, "B": 2, "C": 3, "D": None}
    ranked = sm.rank_records([a, b, c, d], "sujet", lambda topic, r: scores[r["title"]])
    assert [r["title"] for r in ranked] == ["C", "A", "B", "D"], [r["title"] for r in ranked]
    assert [r["title"] for r in sm.selected(ranked, 2)] == ["C", "A", "B"]


def test_export_ris_and_markdown():
    r = rec("openalex", "W1", "Titre | avec barre", doi="10.1/x", item_type="JOUR", container="Revue",
            volume="4", issue="2", pages="10-25", cited_by=None)
    r["relevance"] = 3
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "pdfs"))
        open(os.path.join(d, "pdfs", r["suggested_filename"]), "wb").close()
        sm.export([r], d)
        ris = open(os.path.join(d, "selection.ris"), encoding="utf-8").read()
        md = open(os.path.join(d, "SELECTION.md"), encoding="utf-8").read()
    for line in ("TY  - JOUR", "AU  - Drot-Delange, Béatrice", "AU  - Parriaux, Gabriel", "PY  - 2013",
                 "T2  - Revue", "VL  - 4", "IS  - 2", "SP  - 10", "EP  - 25", "DO  - 10.1/x",
                 f"L1  - {os.path.join('pdfs', r['suggested_filename'])}", "ER  - "):
        assert line in ris, line
    assert "citations : inconnu" in ris
    assert "Titre / avec barre" in md and "| ? |" in md and "| oui |" in md


def test_secrets_drive_source_status():
    import utils
    import providers
    with tempfile.TemporaryDirectory() as d:
        old = utils.SECRETS_DIR
        utils.SECRETS_DIR = d
        try:
            os.environ.pop("SPRINGER_API_KEY", None)
            assert providers.status("springer") == "clé manquante"   # clé obligatoire absente
            assert providers.status("core") == "limité"               # clé optionnelle absente
            assert providers.status("hal") == "ok"                    # aucune clé
            assert "springer" not in providers.available()
            open(os.path.join(d, "springer_api_key"), "w").write("  abc123\n")
            assert utils.secret("springer_api_key") == "abc123"
            assert providers.status("springer") == "ok" and "springer" in providers.available()
            assert sm.resolve_sources(["all"]) == providers.available()
        finally:
            utils.SECRETS_DIR = old


def test_review_requires_both_languages():
    p = sm.build_parser()
    a = p.parse_args(["review", "--dir", "x", "--fr", "didactique", "--en", "computing education"])
    assert a.fr + a.en == ["didactique", "computing education"] and not hasattr(a, "lang")
    try:
        p.parse_args(["review", "--dir", "x", "--fr", "didactique"])
        raise AssertionError("--en devrait être obligatoire")
    except SystemExit:
        pass
    assert "La langue du document" in sm.build_prompt("sujet", {"title": "t"})


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
