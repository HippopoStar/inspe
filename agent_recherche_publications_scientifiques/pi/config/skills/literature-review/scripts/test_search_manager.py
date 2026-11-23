#!/usr/bin/env python3
"""Vérifications hors ligne (aucun appel réseau) : python3 test_search_manager.py"""
import contextlib
import io
import os
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import enrich
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
               rec("cairn", "e", "E"),   # E : sans résumé, 3 plafonné à 2
               rec("cairn", "f", "F", abstract="r", cited_by=1, citation_percentile=0.0)]   # F : 0 % mesuré
    scores = {"A": 3, "B": 2, "C": 3, "D": None, "E": 3, "F": 3}
    with contextlib.redirect_stdout(io.StringIO()) as out:
        ranked = rank.rank(records, "sujet", lambda topic, r: scores[r["title"]])
    assert out.getvalue().splitlines() == ["[rank] 6/6 notées", "[rank] notes : 3 = 3, 2 = 2, 1 = 0, 0 = 0"]
    # Poids 1 par défaut, percentile inconnu = 0,5 : A (3 + 0,5) devant C (3 + 0,2) et F (3 + 0 mesuré) ;
    # une 2 ne passe jamais une 3 mesurée (B : 2 + 0,99 < F : 3) ; sans résumé, E est plafonné à 2.
    assert [r["title"] for r in ranked] == ["A", "C", "F", "B", "E", "D"]
    assert [r["title"] for r in rank.selected(ranked, 2)] == ["A", "C", "F", "B", "E"]
    assert [r["title"] for r in rank.selected(ranked, 2, top=2)] == ["A", "C"]
    with contextlib.redirect_stdout(io.StringIO()):   # poids 2 : B (2 + 2 × 0,99) passe devant C (3 + 2 × 0,2)
        by_citations = rank.rank(records, "sujet", lambda topic, r: scores[r["title"]], citation_weight=2)
    assert [r["title"] for r in by_citations] == ["A", "B", "C", "F", "E", "D"]
    assert "language (French or English) does not matter" in rank.PROMPT


def test_openalex_completes_citations_and_pdf():
    r = rec("cairn", "10.3917/x", "T", doi="10.3917/x", cited_by=4)
    found = {"10.3917/x": {"cited_by": 9, "citation_percentile": 0.5, "pdf_url": "https://oa/x.pdf"}}
    with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(search, "lookup_dois", return_value=found):
        search.complete_from_openalex([r])
    assert (r["cited_by"], r["citation_percentile"], r["pdf_url"]) == (9, 0.5, "https://oa/x.pdf")


def test_export_ris_and_markdown():
    r = rec("openalex", "W1", "Titre | avec barre", doi="10.1/x", item_type="JOUR", container="Revue",
            volume="4", issue="2", pages="10-25", pdf_url="https://x/a.pdf")
    r["relevance"], r["cited_by_results"] = 3, 7
    with tempfile.TemporaryDirectory() as d:
        export.write([r], d)
        ris = open(os.path.join(d, "selection.ris"), encoding="utf-8").read()
        md = open(os.path.join(d, "SELECTION.md"), encoding="utf-8").read()
        assert sorted(os.listdir(d)) == ["SELECTION.md", "selection.ris"]   # aucun PDF téléchargé : liens seulement
    for line in ("TY  - JOUR", "AU  - Drot-Delange, Béatrice", "AU  - Parriaux, Gabriel", "PY  - 2013",
                 "T2  - Revue", "VL  - 4", "IS  - 2", "SP  - 10", "EP  - 25", "DO  - 10.1/x",
                 "ER  - ", "citations : inconnu ; source : openalex:W1 ; cité par 7 notices pertinentes de la liste ; PDF : https://x/a.pdf"):
        assert line in ris, line
    assert "Titre / avec barre" in md and "| ? |" in md and "| [lien](https://x/a.pdf) |" in md and "| cité par 7 |" in md


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
    work = {"id": "https://openalex.org/W1", "title": "Peer Learning and Assessment", "publication_year": 1999,
            "doi": "https://doi.org/10.1080/0260293990240405", "cited_by_count": 1423,
            "citation_normalized_percentile": {"value": 0.99}, "authorships": []}
    with mock.patch.object(openalex, "_get", return_value=[work]) as get:
        found = openalex.most_cited('peer "learning", x', 10)
    # Expression exacte dans le titre, triée par citations (guillemets et virgules de l'agent neutralisés).
    get.assert_called_once_with(filter='title.search:"peer learning x"', sort="cited_by_count:desc", **{"per-page": 10})
    assert found[0]["cited_by"] == 1423 and found[0]["citation_percentile"] == 0.99

    classics = lambda term, n: [rec("openalex", term, f"Classique {term}")]
    with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(search, "most_cited", side_effect=classics), \
            mock.patch.object(search, "lookup_dois", return_value={}):
        out = search.search([], [], 10, core=["peer learning", "peer tutoring"])
    assert [r["title"] for r in out] == ["Classique peer learning", "Classique peer tutoring"]


def test_snowball_adds_works_cited_by_relevant_results():
    a = rec("openalex", "W1", "A", abstract="r"); a["relevance"] = 3
    b = rec("hal", "b", "B", doi="10.1/b"); b["relevance"] = 2
    c = rec("openalex", "W3", "C"); c["relevance"] = 0                 # hors sujet : ne cite pas pour la liste
    # A cite W9, W8 et W3 (déjà dans la liste) ; B (trouvée par DOI, id W2) cite W9, W8 et W7 ; C cite W7 mais est écartée.
    references = [("W1", "", ["W9", "W8", "W3"]), ("W2", "10.1/b", ["W9", "W8", "W7"])]
    works = [rec("openalex", w, f"Classique {w}", doi=d, cited_by=50, citation_percentile=0.9)
             for w, d in (("W9", "10.9/x"), ("W8", "10.1/b"))]   # W8 = B, déjà dans la liste
    with contextlib.redirect_stdout(io.StringIO()), \
            mock.patch.object(enrich.openalex, "references", return_value=references) as read_references, \
            mock.patch.object(enrich.openalex, "works", return_value=works):
        added = enrich.snowball([a, b, c], 2, 10, min_citers=2)
        assert enrich.snowball([a, b, c], 2, 0) == []                             # --snowball 0 : désactivé
        assert enrich.snowball([c], 2, 10) == []                                  # aucune notice pertinente
    read_references.assert_called_once_with(["10.1/b"], ["W1"])                  # relevantes seulement, A par id
    assert [(r["id"], r["cited_by_results"]) for r in added] == [("openalex:W9", 2)]
    assert (b["cited_by"], b["citation_percentile"], b["cited_by_results"]) == (50, 0.9, 2)   # B complétée, pas dupliquée


def test_title_lookup_completes_records_without_doi():
    a = rec("eric", "EJ1", "Peer Tutoring.", abstract="r"); a["relevance"] = 3     # pertinente, sans DOI : cherchée
    b = rec("eric", "EJ2", "Hors sujet"); b["relevance"] = 0                       # non pertinente : aucune requête
    c = rec("eric", "EJ3", "Inconnue", abstract="r"); c["relevance"] = 2           # pertinente, absente d'OpenAlex
    d = rec("cairn", "x", "Avec DOI", doi="10.1/d"); d["relevance"] = 3            # a un DOI : déjà traitée
    asked = []

    def lookup(title, year):
        asked.append(title)
        return rec("openalex", "W1", title, doi="10.1/pt", cited_by=45, citation_percentile=0.89) if title == "Peer Tutoring." else None

    with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(enrich.openalex, "find_by_title", side_effect=lookup):
        enrich.complete_by_title([a, b, c, d], 2)
    assert asked == ["Peer Tutoring.", "Inconnue"]
    assert (a["doi"], a["cited_by"], a["citation_percentile"]) == ("10.1/pt", 45, 0.89)
    assert c["cited_by"] is None and c["doi"] == ""


def test_find_by_title_needs_same_title_and_close_year():
    from providers import openalex
    work = lambda title, year: {"id": "https://openalex.org/W1", "title": title, "publication_year": year, "authorships": []}
    found = [work("Another paper", 1988), work("Peer tutoring as a teaching strategy", 1989)]
    with mock.patch.object(openalex, "_get", return_value=found):
        assert openalex.find_by_title("Peer Tutoring as a Teaching Strategy.", "1988")["id"] == "openalex:W1"  # ±1 an
        assert openalex.find_by_title("Peer Tutoring as a Teaching Strategy.", "1995") is None                 # année trop loin
        assert openalex.find_by_title("Peer Tutoring", "1989") is None                                         # autre titre


def test_review_steps_run_in_order():
    """La recherche par titre fournit les DOI dont la boule de neige a besoin : elle passe avant, et après la notation."""
    calls = []
    step = lambda name, result=None: mock.Mock(side_effect=lambda *a, **k: calls.append(name) or result)
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), \
            mock.patch.object(rank, "ollama_scorer", step("scorer")), mock.patch.object(search, "search", step("search", [])), \
            mock.patch.object(rank, "grade", step("grade")), mock.patch.object(enrich, "complete_by_title", step("by_title")), \
            mock.patch.object(enrich, "snowball", step("snowball", [])), mock.patch.object(export, "write", step("write", "")):
        args = search_manager.build_parser().parse_args(
            ["review", "--dir", os.path.join(d, "x"), "--fr", "a", "--en", "b", "--core", "c"])
        search_manager.cmd_review(args)
    assert calls == ["scorer", "search", "grade", "by_title", "snowball", "grade", "write"]


def test_review_folder_is_dated_and_derived_from_core():
    import re
    parser = search_manager.build_parser()
    stamped = lambda name: r"/workspace/\d{4}-\d\d-\d\d_\d\d-\d\d_" + name
    norm = lambda path: path.replace(os.sep, "/")
    for path in ("/workspace/peer_learning/", "/workspace/20240405_peer_learning", "/workspace/2024-04-05_peer_learning"):
        assert re.fullmatch(stamped("peer_learning"), norm(search_manager.dated(path))), path   # date inventée : retirée
    assert re.fullmatch(stamped("3D_printing"), norm(search_manager.dated("/workspace/3D_printing")))   # un vrai nom reste
    # Sans --dir, le dossier vient du premier terme de --core : l'agent n'a plus à le nommer.
    args = parser.parse_args(["review", "--fr", "a", "--en", "b", "--core", "Peer Learning", "peer tutoring"])
    assert re.fullmatch(stamped("peer_learning"), norm(search_manager.review_dir(args)))
    args = parser.parse_args(["review", "--dir", "/data/x", "--fr", "a", "--en", "b", "--core", "c"])
    assert re.fullmatch(r"/data/\d{4}-\d\d-\d\d_\d\d-\d\d_x", norm(search_manager.review_dir(args)))     # --dir l'emporte
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser.parse_args(["export"])
            raise AssertionError("--dir devrait rester obligatoire hors review")
        except SystemExit:
            pass


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
