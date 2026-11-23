"""Accès aux API : session HTTP polie (délai + nouvelles tentatives) et clés API."""
import os
import re
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SECRETS_DIR = os.environ.get("SECRETS_DIR", "/run/secrets")


def secret(name: str) -> str:
    """Clé API lue dans /run/secrets/<name> (docker secret), sinon dans la variable <NAME>.
    Chaîne vide = pas de clé : la base est alors limitée ou désactivée."""
    try:
        with open(os.path.join(SECRETS_DIR, name), encoding="utf-8") as f:
            value = f.read().strip()
        if value:
            return value
    except OSError:
        pass
    return os.environ.get(name.upper(), "").strip()


def lucene_safe(query: str) -> str:
    """Retire les caractères réservés Solr/Lucene (HAL, ERIC, DOAJ) qui provoquent des HTTP 400."""
    return re.sub(r"\s+", " ", re.sub(r'["():\[\]{}!^~*?\\/]', " ", query or "")).strip()


class PoliteSession(requests.Session):
    """Au plus une requête toutes les `min_delay` secondes ; 429 et 5xx retentés avec attente croissante."""

    def __init__(self, min_delay: float = 1.2):
        super().__init__()
        self.min_delay = min_delay
        self._last = 0.0
        self.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PiAcademicResearch/1.0)",
                             "Accept": "application/json"})
        retry = Retry(total=3, backoff_factor=2.0, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=("GET",), respect_retry_after_header=True)
        self.mount("https://", HTTPAdapter(max_retries=retry))
        self.mount("http://", HTTPAdapter(max_retries=retry))

    def request(self, method, url, *args, **kwargs):
        wait = self.min_delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            return super().request(method, url, *args, **kwargs)
        finally:
            self._last = time.monotonic()


HTTP = PoliteSession()
