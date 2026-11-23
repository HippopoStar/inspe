---
name: literature-review
description: Builds a selection of scientific publications on a topic (HAL, TEL, DUMAS, OpenAlex, Crossref, Cairn, Persée, OpenEdition, JSTOR, Taylor & Francis, ERIC, DOAJ, CORE, Semantic Scholar, plus Springer, Scopus and Web of Science when a key is provided), ranked by relevance and citation count, with PDFs and a Zotero export (selection.ris).
---

# Publication selection on a topic

**Strict rule**: one single command does everything (search, grading, PDFs, export). Do not read `metadata.json`, do not write any script.

**Language**: French and English publications are always both fine. Always give queries in both languages (the command requires it) and never filter or prefer a language. Answer the user in the language they wrote in.

## 1. Prepare the command (no long thinking)

- `<folder>`: short lowercase name for the topic, e.g. `didactique_informatique`.
- `--topic`: the user's subject in one sentence.
- `--fr`: 2 or 3 short keyword queries in French (not the user's sentence).
- `--en`: the same ideas in English, 2 or 3 queries.
- **Every query must contain the topic's core concept.** A query made only of generic words ("études comparatives", "pedagogical process") brings back off-topic results.
  Example for "études comparatives sur le peer learning":
  `--fr "apprentissage entre pairs" "apprentissage par les pairs comparaison" "tutorat entre pairs efficacité"`
  `--en "peer learning comparative study" "peer tutoring effectiveness" "peer instruction versus lecture"`
- `--sources`: space-separated names, without quotes, chosen by field (databases whose key is missing are skipped automatically):
  * Humanities / social sciences, French-speaking: `hal tel dumas cairn persee openedition openalex`
  * Education: `hal tel dumas eric cairn openalex`
  * Computer science / hard sciences: `openalex semanticscholar core springer scopus wos`
  * General or unsure: `all` (every accessible database, slower)

## 2. Run it

```bash
python3 /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py review \
  --dir "/workspace/<folder>" \
  --topic "<subject in one sentence>" \
  --fr "<requête 1>" "<requête 2>" \
  --en "<query 1>" "<query 2>" \
  --sources <sources>
```

## 3. Answer

Copy the table printed at the end exactly as is (every row), then tell the user, in their language:
- `/workspace/<folder>/selection.ris` is to be imported into Zotero (File > Import);
- `/workspace/<folder>/pdfs/` is to be uploaded to an Open WebUI Knowledge collection;
- PDFs marked `[lien]` must be downloaded by hand (HAL blocks robots).

The selection keeps the 20 best results. If the user wants more or fewer, run again with `--top` (default 20) or `--min-relevance` (default 2).
To see which databases are accessible: `search_manager.py sources --check`.
