from functools import partial

from utils import secret
from . import hal, openalex, semanticscholar, crossref, eric, doaj, core, springer, scopus, wos


def _src(label, fn, key=None, required=False, note=""):
    return {"label": label, "fn": fn, "key": key, "required": required, "note": note}


# Chaque base : fonction de recherche, nom du secret (fichier dans ./secrets/), clé obligatoire ou non.
SOURCES = {
    "openalex": _src("OpenAlex", openalex.search, "openalex_api_key", note="sans clé : quota très réduit"),
    "hal": _src("HAL", hal.search),
    "tel": _src("TEL (thèses, HAL)", partial(hal.search, portal="tel", source="tel")),
    "dumas": _src("DUMAS (mémoires, HAL)", partial(hal.search, portal="dumas", source="dumas")),
    "crossref": _src("Crossref", crossref.search),
    "cairn": _src("Cairn (via Crossref)", partial(crossref.search, prefix="10.3917", source="cairn"),
                  note="métadonnées seulement, textes souvent payants"),
    "persee": _src("Persée (via Crossref)", partial(crossref.search, prefix="10.3406", source="persee")),
    "openedition": _src("OpenEdition (via Crossref)", partial(crossref.search, prefix="10.4000", source="openedition")),
    "jstor": _src("JSTOR (via Crossref)", partial(crossref.search, prefix="10.2307", source="jstor"),
                  note="métadonnées seulement"),
    "taylorfrancis": _src("Taylor & Francis (via Crossref)",
                          partial(crossref.search, prefix="10.1080", source="taylorfrancis"),
                          note="métadonnées seulement"),
    "eric": _src("ERIC", eric.search),
    "doaj": _src("DOAJ", doaj.search),
    "semanticscholar": _src("Semantic Scholar", semanticscholar.search, "s2_api_key",
                            note="sans clé : erreurs 429 fréquentes"),
    "core": _src("CORE", core.search, "core_api_key", note="sans clé : quota bas, service parfois saturé"),
    "springer": _src("Springer Nature", springer.search, "springer_api_key", required=True),
    "scopus": _src("Scopus", scopus.search, "scopus_api_key", required=True,
                   note="complet seulement depuis un établissement abonné ou avec scopus_insttoken"),
    "wos": _src("Web of Science (Starter)", wos.search, "wos_api_key", required=True, note="pas de résumés"),
}

# Demandées mais non intégrées, avec la raison (affichées par `sources`).
EXCLUDED = {
    "Google Scholar": "aucune API ; le site bloque les robots (CAPTCHA) et l'interdit dans ses conditions",
    "Pascal et Francis": "base INIST figée (1972-2015), sans API de recherche publique",
    "EBSCO": "API EDS réservée aux établissements abonnés (compte activé par EBSCO) ; à ajouter si l'université fournit un accès",
    "Sci-Hub": "diffuse des articles en violation du droit d'auteur, bloqué en France par décision de justice : exclu",
}


def status(name: str) -> str:
    """'ok' (clé fournie ou inutile), 'limité' (clé optionnelle absente), 'clé manquante' (inutilisable)."""
    s = SOURCES[name]
    if not s["key"] or secret(s["key"]):
        return "ok"
    return "clé manquante" if s["required"] else "limité"


def available() -> list:
    return [n for n in SOURCES if status(n) != "clé manquante"]


PROVIDERS = {name: s["fn"] for name, s in SOURCES.items()}
