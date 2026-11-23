"""Registre des bases : fonction de recherche, clé API (nom du docker secret) et clé obligatoire ou non.
Ajouter une base = écrire son module `search(query, max_results, lang)` et l'inscrire ici."""
from functools import partial

from net import secret
from . import hal, openalex, semanticscholar, crossref, eric, doaj, core, springer, scopus, wos


def _base(label, fn, key=None, required=False, note="", takes_core=False, boolean=False):
    """takes_core : la fonction accepte `core=` (concepts centraux), pour les bases qui exigent tous les mots.
    boolean : la fonction accepte `boolean=True`, une équation « (a OR b) AND (c OR d) »."""
    return {"label": label, "fn": fn, "key": key, "required": required, "note": note, "takes_core": takes_core,
            "boolean": boolean}


def _publisher(label, doi_prefix, name):
    return _base(f"{label} (via Crossref)", partial(crossref.search, prefix=doi_prefix, source=name),
                 note="métadonnées seulement, texte souvent payant")


SOURCES = {
    "openalex": _base("OpenAlex", openalex.search, "openalex_api_key", boolean=True, note="sans clé : quota très réduit"),
    "hal": _base("HAL", hal.search, takes_core=True, boolean=True),
    "tel": _base("TEL (thèses)", partial(hal.search, portal="tel", source="tel"), takes_core=True, boolean=True),
    "dumas": _base("DUMAS (mémoires)", partial(hal.search, portal="dumas", source="dumas"), takes_core=True,
                   boolean=True),
    "crossref": _base("Crossref", crossref.search),
    "cairn": _publisher("Cairn", "10.3917", "cairn"),
    "persee": _publisher("Persée", "10.3406", "persee"),
    "openedition": _publisher("OpenEdition", "10.4000", "openedition"),
    "jstor": _publisher("JSTOR", "10.2307", "jstor"),
    "taylorfrancis": _publisher("Taylor & Francis", "10.1080", "taylorfrancis"),
    "eric": _base("ERIC", eric.search, boolean=True),
    "doaj": _base("DOAJ", doaj.search),
    "semanticscholar": _base("Semantic Scholar", semanticscholar.search, "s2_api_key",
                             note="sans clé : erreurs 429 fréquentes"),
    "core": _base("CORE", core.search, "core_api_key", note="sans clé : quota bas"),
    "springer": _base("Springer Nature", springer.search, "springer_api_key", required=True),
    "scopus": _base("Scopus", scopus.search, "scopus_api_key", required=True,
                    note="complet depuis un établissement abonné ou avec scopus_insttoken"),
    "wos": _base("Web of Science", wos.search, "wos_api_key", required=True, note="sans résumés"),
}

NOT_INTEGRATED = {
    "Google Scholar": "aucune API ; le site bloque les robots (CAPTCHA) et l'interdit dans ses conditions",
    "Pascal et Francis": "archive INIST figée (1972-2015), sans API de recherche",
    "EBSCO": "API réservée aux établissements abonnés (compte activé par EBSCO)",
    "Sci-Hub, Open-Slum": "diffusion d'articles en violation du droit d'auteur (Open-Slum ne fait que surveiller "
                          "ces sites) ; à la place, les PDF légaux en accès libre sont cherchés via OpenAlex/Unpaywall",
}


def status(name: str) -> str:
    """« ok », « limité » (clé facultative absente) ou « clé manquante » (base inutilisable)."""
    base = SOURCES[name]
    if not base["key"] or secret(base["key"]):
        return "ok"
    return "clé manquante" if base["required"] else "limité"


def available() -> list:
    return [name for name in SOURCES if status(name) != "clé manquante"]
