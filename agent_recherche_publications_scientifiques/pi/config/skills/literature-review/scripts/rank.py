"""Étape 2 : noter la pertinence (0-3) de chaque notice avec le LLM local, puis classer."""
import json
import os
import re

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
RANK_MODEL = os.environ.get("RANK_MODEL", "qwen3:4b-instruct")
CITATION_WEIGHT = 1.0   # voir sort_key ; 0 = classement par pertinence seule
LABELS = {0: "hors sujet", 1: "lien indirect", 2: "pertinent", 3: "au cœur du sujet"}

# En anglais : Qwen3 suit mieux des consignes en anglais. Barème strict : au premier essai, la quasi-totalité
# des notices (même un article sur Ossian) recevait 2 avec un barème plus vague.
PROMPT = """Research topic: {topic}

Title: {title}
Abstract: {abstract}

Rate how relevant this document is to the research topic:
3 = the topic's core concept is the document's main subject;
2 = the document studies the core concept, but as a secondary aspect;
1 = same broad field, but the core concept is not studied;
0 = off topic.
A document that shares only generic words with the topic (e.g. "process", "learning", "comparative", "pedagogy") is worth 0.
If unsure between two scores, give the lower one.
The document's language (French or English) does not matter.
Answer only in JSON: {{"score": <0-3>}}"""


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
        prompt = PROMPT.format(topic=topic, title=rec["title"], abstract=(rec["abstract"] or "(none)")[:1500])
        r = requests.post(f"{OLLAMA_HOST}/api/chat", timeout=180, json={
            "model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False,
            "format": {"type": "object", "properties": {"score": {"type": "integer"}}, "required": ["score"]},
            "options": {"temperature": 0}})
        r.raise_for_status()
        return parse_score(r.json()["message"]["content"])
    return score


def sort_key(rec: dict, citation_weight: float):
    """Score = pertinence (0-3) + poids × percentile de citations (0-1), puis citations brutes à égalité.
    Poids 1 (défaut) : les citations départagent les notices de même note et choisissent les notées 2 qui complètent
    la liste ; une 2 ne passe jamais devant une 3 (2 + 0,99 < 3). Au-delà de 1, une 2 très citée passe devant une 3 :
    au 2e essai, un poids 2 évinçait 13 des 15 notices notées 3, faute de percentile (ERIC sans DOI, articles récents).
    Le filtre `--min-relevance` reste appliqué avant : les citations ne font jamais entrer du hors-sujet.
    Percentile inconnu = aucun bonus (pas une pénalité) ; non noté = en dernier."""
    if rec.get("relevance") is None:
        return (-1, -1)
    return (rec["relevance"] + citation_weight * (rec.get("citation_percentile") or 0), rec.get("cited_by") or 0)


def grade(records: list, topic: str, scorer):
    """Note la pertinence (0-3) de chaque notice, sur place."""
    for i, rec in enumerate(records, 1):
        try:
            score = scorer(topic, rec)
            # ponytail: sans résumé, le titre seul ne suffit pas pour « au cœur du sujet » (2e essai : 5 notices
            # Cairn sans résumé et hors sujet notées 3). Plafond à 2 ; à revoir si une base fournit le texte intégral.
            rec["relevance"] = min(score, 2) if score is not None and not rec["abstract"] else score
        except Exception as e:
            rec["relevance"] = None
            print(f"[rank] {rec['id']} : échec ({e})")
        if i % 25 == 0 or i == len(records):  # peu de lignes : toute la sortie revient dans le contexte de l'agent
            print(f"[rank] {i}/{len(records)} notées")
    if records:
        print("[rank] notes : " + ", ".join(f"{k} = {sum(r['relevance'] == k for r in records)}" for k in (3, 2, 1, 0)))


def order(records: list, citation_weight: float = CITATION_WEIGHT) -> list:
    return sorted(records, key=lambda r: sort_key(r, citation_weight), reverse=True)


def rank(records: list, topic: str, scorer, citation_weight: float = CITATION_WEIGHT) -> list:
    grade(records, topic, scorer)
    return order(records, citation_weight)


def selected(records: list, min_relevance: int, top: int = None) -> list:
    """Les `top` meilleures notices (déjà classées) de pertinence ≥ min_relevance."""
    return [r for r in records if (r.get("relevance") or 0) >= min_relevance][:top]
