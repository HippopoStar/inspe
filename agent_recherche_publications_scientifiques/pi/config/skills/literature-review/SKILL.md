---
name: literature-review
description: Builds a selection of scientific publications on a topic (HAL, TEL, DUMAS, OpenAlex, Crossref, Cairn, Persée, OpenEdition, JSTOR, Taylor & Francis, ERIC, DOAJ, CORE, Semantic Scholar, plus Springer, Scopus and Web of Science when a key is provided), ranked by relevance and citation count, with links to open-access PDFs and a Zotero export (selection.ris).
---

# Publication selection on a topic

**Strict rule**: one single command does everything (search, grading, export; PDFs are not downloaded, only linked). Do not read `metadata.json`, do not write any script.

**Language**: French and English publications are always both fine. Always give queries in both languages (the command requires it) and never filter or prefer a language. Answer the user in the language they wrote in.

## 1. Prepare the command (no long thinking)

- `<folder>`: 2 or 3 words from the user's topic, lowercase, joined by `_` (the command adds the date and time in front). Never reuse a name from an example.
- `--topic`: the user's subject in one sentence.
- `--fr`: 2 or 3 keyword queries in French (not the user's sentence).
- `--en`: the same ideas in English, 2 or 3 queries.
- **Every query must contain the topic's core concept.** A query made only of generic words ("études comparatives", "pedagogical process") brings back off-topic results.
- **2 to 4 words per query.** HAL, TEL and DUMAS require every word: a long query returns nothing. Put context (level, method) in `--topic`, not in the queries.
- `--core`: the core concept and its synonyms, 1 to 3 words each, in English and French, nothing else (no "comparative", "study", "effectiveness"). The most cited works with these words in their title are added: they bring the classics that precise queries miss.
  Example: `--core "peer learning" "peer tutoring" "apprentissage entre pairs" "tutorat entre pairs"`
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
  --core "<concept>" "<synonym>" "<concept FR>" \
  --sources <sources>
```

## 3. Answer

Do not copy the table: the user already sees the command output, and the table is saved in `SELECTION.md`.
Answer in a few lines, in the user's language, with the folder path printed by the command (it starts with the date):
- how many publications were kept, and that the table is in `<printed folder>/SELECTION.md`;
- `<printed folder>/selection.ris` is to be imported into Zotero (File > Import);
- the `PDF` column of `SELECTION.md` links to open-access PDFs (`[lien]`); nothing was downloaded. To query a PDF in Open WebUI, the user downloads it and uploads it to a Knowledge collection.

The selection keeps the 20 best results, ranked by relevance plus citations. If the user wants more or fewer, run again with `--top` (default 20) or `--min-relevance` (default 2); `--citation-weight` (default 1, 0 = relevance only) sets how much citations count. The command also adds up to 10 works cited by at least 3 relevant results (`--snowball`, 0 = none): the `Ajouté car` column of the table says how many results cite each one.
To see which databases are accessible: `search_manager.py sources --check`.
