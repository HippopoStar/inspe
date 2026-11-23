"""Étape 3 : télécharger les PDF en accès libre des notices retenues."""
import os

from net import HTTP


def pdf_path(theme_dir: str, rec: dict) -> str:
    return os.path.join(theme_dir, "pdfs", rec["suggested_filename"])


def download(records: list, theme_dir: str):
    os.makedirs(os.path.join(theme_dir, "pdfs"), exist_ok=True)
    for rec in records:
        if os.path.exists(pdf_path(theme_dir, rec)) or not rec["pdf_url"]:
            continue
        try:
            resp = HTTP.get(rec["pdf_url"], timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"ÉCHEC {rec['id']} : {e}")
            continue
        if b"%PDF" in resp.content[:1024]:
            with open(pdf_path(theme_dir, rec), "wb") as f:
                f.write(resp.content)
        elif b"not a bot" in resp.content[:2000]:
            # HAL protège ses fichiers par une page anti-robot : téléchargement manuel (lien dans SELECTION.md).
            print(f"BLOQUÉ (anti-robot) : {rec['id']} -> {rec['pdf_url']}")
        else:
            print(f"IGNORÉ (pas un PDF) : {rec['id']}")
    have = sum(os.path.exists(pdf_path(theme_dir, r)) for r in records)
    print(f"PDF : {have}/{len(records)} dans {os.path.join(theme_dir, 'pdfs')}")
