"""Étape 3 : télécharger les PDF en accès libre des notices retenues."""
import os

from net import HTTP


def pdf_path(theme_dir: str, rec: dict) -> str:
    return os.path.join(theme_dir, "pdfs", rec["suggested_filename"])


def download(records: list, theme_dir: str):
    os.makedirs(os.path.join(theme_dir, "pdfs"), exist_ok=True)
    missed = 0
    for rec in records:
        if os.path.exists(pdf_path(theme_dir, rec)) or not rec["pdf_url"]:
            continue
        try:
            resp = HTTP.get(rec["pdf_url"], timeout=30)
            resp.raise_for_status()
        except Exception:
            missed += 1
            continue
        if b"%PDF" in resp.content[:1024]:
            with open(pdf_path(theme_dir, rec), "wb") as f:
                f.write(resp.content)
        else:
            # Erreur, ou page anti-robot de HAL : téléchargement manuel (lien dans SELECTION.md).
            missed += 1
    have = sum(os.path.exists(pdf_path(theme_dir, r)) for r in records)
    print(f"PDF : {have}/{len(records)} dans {os.path.join(theme_dir, 'pdfs')} ; "
          f"{missed} à télécharger à la main (bloqués par un anti-robot ou en erreur, liens dans SELECTION.md)")
