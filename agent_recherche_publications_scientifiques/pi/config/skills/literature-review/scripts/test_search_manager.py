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
    records = [rec("hal", "a", "A", abstract="r"), rec("hal", "b", "B", abstract="r", cited_by=500, citation_percentile=0.99),
               rec("hal", "c", "C", abstract="r", cited_by=3, citation_percentile=0.2), rec("hal", "d", "D"),
               rec("cairn", "e", "E")]  # E : sans résumé, 3 plafonné à 2
    scores = {"A": 3, "B": 2, "C": 3, "D": None, "E": 3}
    with contextlib.redirect_stdout(io.StringIO()) as out:
        ranked = rank.rank(records, "sujet", lambda topic, r: scores[r["title"]])
    assert out.getvalue().splitlines() == ["[rank] 5/5 notées", "[rank] notes : 3 = 2, 2 = 2, 1 = 0, 0 = 0"]
    # Poids 1 par défaut : une 2 ne passe jamais une 3 (B : 2 + 0,99 < A : 3) ; à note égale, le percentile départage.
    # Sans résumé, E est plafonné à 2.
    assert [r["title"] for r in ranked] == ["C", "A", "B", "E", "D"]
    assert [r["title"] for r in rank.selected(ranked, 2)] == ["C", "A", "B", "E"]
    assert [r["title"] for r in rank.selected(ranked, 2, top=2)] == ["C", "A"]
    with contextlib.redirect_stdout(io.StringIO()):   # poids 2 : B (2 + 2 × 0,99) passe devant C (3 + 2 × 0,2) et A
        by_citations = rank.rank(records, "sujet", lambda topic, r: scores[r["title"]], citation_weight=2)
    assert [r["title"] for r in by_citations] == ["B", "C", "A", "E", "D"]
    assert "language (French or English) does not matter" in rank.PROMPT


def test_openalex_completes_citations_and_pdf():
    r = rec("cairn", "10.3917/x", "T", doi="10.3917/x", cited_by=4)
    search.lookup_dois = lambda dois: {"10.3917/x": {"cited_by": 9, "citation_percentile": 0.5, "pdf_url": "https://oa/x.pdf"}}
    with contextlib.redirect_stdout(io.StringIO()):
        search.complete_from_openalex([r])
    assert (r["cited_by"], r["citation_percentile"], r["pdf_url"]) == (9, 0.5, "https://oa/x.pdf")


def test_export_ris_and_markdown():
    r = rec("openalex", "W1", "Titre | avec barre", doi="10.1/x", item_type="JOUR", container="Revue",
            volume="4", issue="2", pages="10-25", pdf_url="https://x/a.pdf")
    r["relevance"] = 3
    with tempfile.TemporaryDirectory() as d:
        export.write([r], d)
        ris = open(os.path.join(d, "selection.ris"), encoding="utf-8").read()
        md = open(os.path.join(d, "SELECTION.md"), encoding="utf-8").read()
        assert sorted(os.listdir(d)) == ["SELECTION.md", "selection.ris"]   # aucun PDF téléchargé : liens seulement
    for line in ("TY  - JOUR", "AU  - Drot-Delange, Béatrice", "AU  - Parriaux, Gabriel", "PY  - 2013",
                 "T2  - Revue", "VL  - 4", "IS  - 2", "SP  - 10", "EP  - 25", "DO  - 10.1/x",
                 "ER  - ", "citations : inconnu ; source : openalex:W1 ; PDF : https://x/a.pdf"):
        assert line in ris, line
    assert "Titre / avec barre" in md and "| ? |" in md and "| [lien](https://x/a.pdf) |" in md


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
    a = parser.parse_args(["review", "--dir", "x", "--fr", "didactique", "--en", "computing education",
                           "--core", "didactique de l'informatique"])
    assert a.fr + a.en == ["didactique", "computing education"] and not hasattr(a, "lang")
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser.parse_args(["review", "--dir", "x", "--fr", "didactique", "--core", "didactique"])
            raise AssertionError("--en devrait être obligatoire")
        except SystemExit:
            pass
        try:
            parser.parse_args(["review", "--dir", "x", "--fr", "didactique", "--en", "computing education"])
            raise AssertionError("--core devrait être obligatoire")
        except SystemExit:
            pass


def test_core_terms_add_most_cited_by_title():
    from providers import openalex
    calls = []
    work = {"id": "https://openalex.org/W1", "title": "Peer Learning and Assessment", "publication_year": 1999,
            "doi": "https://doi.org/10.1080/0260293990240405", "cited_by_count": 1423,
            "citation_normalized_percentile": {"value": 0.99}, "authorships": []}
    old = openalex._get
    openalex._get = lambda **params: calls.append(params) or [work]
    try:
        found = openalex.most_cited('peer "learning", x', 10)
    finally:
        openalex._get = old
    # Expression exacte dans le titre, triée par citations (guillemets et virgules de l'agent neutralisés).
    assert calls == [{"filter": 'title.search:"peer learning x"', "sort": "cited_by_count:desc", "per-page": 10}]
    assert found[0]["cited_by"] == 1423 and found[0]["citation_percentile"] == 0.99

    search.most_cited = lambda term, n: [rec("openalex", term, f"Classique {term}")]
    search.lookup_dois = lambda dois: {}
    with contextlib.redirect_stdout(io.StringIO()):
        out = search.search([], [], 10, core=["peer learning", "peer tutoring"])
    assert [r["title"] for r in out] == ["Classique peer learning", "Classique peer tutoring"]


def test_review_folder_is_dated():
    import re
    out = search_manager.dated("/workspace/peer_learning/")
    assert re.fullmatch(r"/workspace/\d{4}-\d\d-\d\d_\d\d-\d\d_peer_learning", out.replace(os.sep, "/")), out


def test_sources_quoted_or_not():
    parser = search_manager.build_parser()
    base = ["review", "--dir", "x", "--fr", "a", "--en", "b", "--core", "c", "--sources"]
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
