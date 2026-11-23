"""Étape 2 : noter la pertinence (0-3) de chaque notice avec le LLM local, puis classer."""
import json
import os
import re

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
RANK_MODEL = os.environ.get("RANK_MODEL", "qwen3:4b-instruct")
LABELS = {0: "hors sujet", 1: "lien indirect", 2: "pertinent", 3: "au cœur du sujet"}

PROMPT = """Sujet de recherche : {topic}

Titre : {title}
Résumé : {abstract}

Note la pertinence de ce document pour le sujet :
0 = hors sujet ; 1 = lien indirect ; 2 = pertinent ; 3 = au cœur du sujet.
Un document qui reprend les mots du sujet sans le traiter vaut 0 ou 1.
La langue du document (français ou anglais) ne compte pas : seul le contenu est noté.
Réponds uniquement en JSON : {{"score": <0-3>}}"""


def parse_score(text: str):
    try:
        score = int(json.loads(text)["score"])
    except (ValueError, KeyError, TypeError):
        digit = re.search(r"[0-3]", text or "")
        if not digit:
            return None
        score = int(digit.group())
    return max(0, min(3, score))


def ollama_scorer(model: str = RANK_MODEL):
    """Appel direct à l'API native d'Ollama : pas de « réflexion », réponse JSON imposée, température 0."""
    def score(topic: str, rec: dict):
        prompt = PROMPT.format(topic=topic, title=rec["title"], abstract=(rec["abstract"] or "(aucun)")[:1500])
        r = requests.post(f"{OLLAMA_HOST}/api/chat", timeout=180, json={
            "model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False,
            "format": {"type": "object", "properties": {"score": {"type": "integer"}}, "required": ["score"]},
            "options": {"temperature": 0}})
        r.raise_for_status()
        return parse_score(r.json()["message"]["content"])
    return score


def sort_key(rec: dict):
    # ponytail: ordre pertinence > percentile de citations > citations brutes ; une valeur inconnue (None)
    # passe après les connues. Remplacer par un score pondéré si ce classement ne convient pas.
    return tuple(-1 if rec.get(k) is None else rec[k] for k in ("relevance", "citation_percentile", "cited_by"))


def rank(records: list, topic: str, scorer) -> list:
    for i, rec in enumerate(records, 1):
        try:
            rec["relevance"] = scorer(topic, rec)
        except Exception as e:
            rec["relevance"] = None
            print(f"[rank] {rec['id']} : échec ({e})")
        if i % 25 == 0 or i == len(records):  # peu de lignes : toute la sortie revient dans le contexte de l'agent
            print(f"[rank] {i}/{len(records)} notées")
    print("[rank] notes : " + ", ".join(f"{k} = {sum(r['relevance'] == k for r in records)}" for k in (3, 2, 1, 0)))
    return sorted(records, key=sort_key, reverse=True)


def selected(records: list, min_relevance: int, top: int = None) -> list:
    """Les `top` meilleures notices (déjà classées) de pertinence ≥ min_relevance."""
    return [r for r in records if (r.get("relevance") or 0) >= min_relevance][:top]
