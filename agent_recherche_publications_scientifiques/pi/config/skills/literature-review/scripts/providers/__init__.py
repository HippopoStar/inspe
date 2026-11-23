from . import hal, openalex, semanticscholar, crossref, eric, doaj

PROVIDERS = {
    "hal": hal.search,
    "openalex": openalex.search,
    "semanticscholar": semanticscholar.search,
    "crossref": crossref.search,
    "eric": eric.search,
    "doaj": doaj.search,
}

