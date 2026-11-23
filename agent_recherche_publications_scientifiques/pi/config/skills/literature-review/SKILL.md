---
name: literature-review
description: Builds a selection of scientific publications on a topic (HAL, TEL, DUMAS, OpenAlex, Crossref, Cairn, Persée, OpenEdition, JSTOR, Taylor & Francis, ERIC, DOAJ, CORE, Semantic Scholar, plus Springer, Scopus and Web of Science when a key is provided), ranked by relevance and citation count, with links to open-access PDFs and a Zotero export (selection.ris).
---

# Publication selection on a topic

**One single command does everything** (search, grading, export; PDFs are linked, not downloaded). Do not read `metadata.json`, do not write any script.

**Language**: French and English publications are both always fine. Give queries in both languages, never filter or prefer one. Answer in the language the user wrote in.

## 1. Prepare the command (no long thinking)

- `--topic`: the user's subject in one sentence, with its context (level, method).
- `--core`: the core concept and its synonyms, in English and French, 1 to 3 words each, nothing else (no "comparative", "study"). The most cited works with these words in their title are added: the classics.
- `--fr` and `--en`: 2 or 3 keyword queries in each language, not the user's sentence. **Every query contains the core concept and has 2 to 4 words**: HAL, TEL and DUMAS require every word, so a long query finds nothing.
- `--sources`: names separated by spaces, without quotes. Education: `hal tel dumas eric cairn openalex`. Humanities, French-speaking: `hal tel dumas cairn persee openedition openalex`. Sciences: `openalex semanticscholar core springer scopus wos`. Unsure: `all` (slower). A database whose key is missing is skipped.

Example for "études comparatives sur le peer learning":
`--topic "Comparative studies of peer learning" --core "peer learning" "peer tutoring" "apprentissage entre pairs"`
`--fr "apprentissage entre pairs" "tutorat entre pairs efficacité" --en "peer learning comparative study" "peer tutoring effectiveness"`

## 2. Run it

```bash
python3 /home/node/.pi/agent/skills/literature-review/scripts/search_manager.py review \
  --topic "<subject in one sentence>" \
  --core "<concept>" "<synonym>" "<concept FR>" \
  --fr "<requête 1>" "<requête 2>" \
  --en "<query 1>" "<query 2>" \
  --sources <sources>
```

## 3. Answer

Do not copy the table: the user sees the command output and it is saved in `SELECTION.md`. In a few lines, in the user's language, with the folder printed by the command:
- how many publications were kept, and that the table is in `<folder>/SELECTION.md`;
- `<folder>/selection.ris` is to be imported into Zotero (File > Import);
- the `PDF` column links to open-access PDFs (`[lien]`), nothing was downloaded; to query a PDF in Open WebUI, download it and upload it to a Knowledge collection.

Options, only if the user asks: `--top` (20 kept), `--min-relevance` (2), `--citation-weight` (1; 0 = relevance only), `--snowball` (10 works cited by relevant results; 0 = none). `search_manager.py sources --check` lists the accessible databases.
