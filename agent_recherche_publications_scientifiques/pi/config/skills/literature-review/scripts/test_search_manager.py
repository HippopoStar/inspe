#!/usr/bin/env python3
"""Vérifications hors ligne (aucun appel réseau) : python3 test_search_manager.py"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import export
import net
import providers
import rank
import search
import search_manager
from records import make_record, deduplicate


def rec(source, doc_id, title, **kw):
    return make_record(source, doc_id, title, ["Béatrice Drot-Delange", "Gabriel Parriaux"], 2013, **kw)


def test_dedup_merges_doi_and_title():
    hal = rec("hal", "1", "Enseigner l'informatique débranchée", abstract="résumé HAL")
    oa = rec("openalex", "W1", "Enseigner l’informatique débranchée !", doi="10.1/X", pdf_url="https://x/a.pdf",
             cited_by=12, citation_percentile=0.8)
    cr = rec("crossref", "10.1/x", "Autre titre", doi="https://doi.org/10.1/x")
    out = deduplicate([hal, oa, cr])
    assert len(out) == 1, out
    assert out[0]["pdf_url"] == "https://x/a.pdf"    # la notice avec PDF gagne
    assert out[0]["abstract"] == "résumé HAL"         # sans perdre les champs de l'autre
    assert out[0]["cited_by"] == 12 and out[0]["doi"] == "10.1/x"


def test_parse_score():
    assert rank.parse_score('{"score": 2}') == 2
    assert rank.parse_score('{"score": 7}') == 3
    assert rank.parse_score("note : 1") == 1
    assert rank.parse_score("aucune idée") is None


def test_rank_order_and_selection():
    records = [rec("hal", "a", "A"), rec("hal", "b", "B", cited_by=500, citation_percentile=0.99),
               rec("hal", "c", "C", cited_by=3, citation_percentile=0.2), rec("hal", "d", "D")]
    scores = {"A": 3, "B": 2, "C": 3, "D": None}
    with contextlib.redirect_stdout(io.StringIO()) as out:
        ranked = rank.rank(records, "sujet", lambda topic, r: scores[r["title"]])
    assert out.getvalue().splitlines() == ["[rank] 4/4 notées", "[rank] notes : 3 = 2, 2 = 1, 1 = 0, 0 = 0"]
    assert [r["title"] for r in ranked] == ["C", "A", "B", "D"]
    assert [r["title"] for r in rank.selected(ranked, 2)] == ["C", "A", "B"]
    assert [r["title"] for r in rank.selected(ranked, 2, top=2)] == ["C", "A"]
    assert "La langue du document" in rank.PROMPT


def test_openalex_completes_citations_and_pdf():
    r = rec("cairn", "10.3917/x", "T", doi="10.3917/x", cited_by=4)
    search.lookup_dois = lambda dois: {"10.3917/x": {"cited_by": 9, "citation_percentile": 0.5, "pdf_url": "https://oa/x.pdf"}}
    with contextlib.redirect_stdout(io.StringIO()):
        search.complete_from_openalex([r])
    assert (r["cited_by"], r["citation_percentile"], r["pdf_url"]) == (9, 0.5, "https://oa/x.pdf")


def test_export_ris_and_markdown():
    r = rec("openalex", "W1", "Titre | avec barre", doi="10.1/x", item_type="JOUR", container="Revue",
            volume="4", issue="2", pages="10-25")
    r["relevance"] = 3
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "pdfs"))
        open(os.path.join(d, "pdfs", r["suggested_filename"]), "wb").close()
        export.write([r], d)
        ris = open(os.path.join(d, "selection.ris"), encoding="utf-8").read()
        md = open(os.path.join(d, "SELECTION.md"), encoding="utf-8").read()
    for line in ("TY  - JOUR", "AU  - Drot-Delange, Béatrice", "AU  - Parriaux, Gabriel", "PY  - 2013",
                 "T2  - Revue", "VL  - 4", "IS  - 2", "SP  - 10", "EP  - 25", "DO  - 10.1/x",
                 f"L1  - {os.path.join('pdfs', r['suggested_filename'])}", "ER  - ", "citations : inconnu"):
        assert line in ris, line
    assert "Titre / avec barre" in md and "| ? |" in md and "| oui |" in md


def test_secrets_drive_source_status():
    with tempfile.TemporaryDirectory() as d:
        old, net.SECRETS_DIR = net.SECRETS_DIR, d
        os.environ.pop("SPRINGER_API_KEY", None)
        try:
            assert providers.status("springer") == "clé manquante"   # clé obligatoire absente
            assert providers.status("core") == "limité"               # clé facultative absente
            assert providers.status("hal") == "ok"                    # pas de clé
            open(os.path.join(d, "springer_api_key"), "w").write("")  # fichier vide (placeholder) = pas de clé
            assert providers.status("springer") == "clé manquante"
            open(os.path.join(d, "springer_api_key"), "w").write("  abc123\n")
            assert net.secret("springer_api_key") == "abc123" and providers.status("springer") == "ok"
            with contextlib.redirect_stdout(io.StringIO()):
                assert search.usable_sources(["all"]) == providers.available()
        finally:
            net.SECRETS_DIR = old


def test_review_requires_both_languages():
    parser = search_manager.build_parser()
    a = parser.parse_args(["review", "--dir", "x", "--fr", "didactique", "--en", "computing education"])
    assert a.fr + a.en == ["didactique", "computing education"] and not hasattr(a, "lang")
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser.parse_args(["review", "--dir", "x", "--fr", "didactique"])
            raise AssertionError("--en devrait être obligatoire")
        except SystemExit:
            pass


def test_sources_quoted_or_not():
    parser = search_manager.build_parser()
    base = ["review", "--dir", "x", "--fr", "a", "--en", "b", "--sources"]
    for argv in (["hal tel", "eric"], ["hal", "tel", "eric"]):
        with contextlib.redirect_stdout(io.StringIO()):
            assert search.usable_sources(parser.parse_args(base + argv).sources) == ["hal", "tel", "eric"]
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser.parse_args(base + ["hal scihub"])
            raise AssertionError("base inconnue acceptée")
        except SystemExit:
            pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
