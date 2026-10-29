# Reproducing this repository

Built from the pages of logir.fo retrieved on {{RETRIEVED}}, by the scripts in `tools/build/` (copied there as run). The sha256 of every page the build read is in [`data/source-sha256.tsv`](data/source-sha256.tsv), so a copy of those pages can be checked byte for byte before rebuilding. How the pages were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| build.py | `{{SHA_BUILD_PY}}` |
| docs.py | `{{SHA_DOCS_PY}}` |
| check_repo.py | `{{SHA_CHECK_REPO_PY}}` |

## Steps

With the retrieved pages in place (each matching its sha256 in `data/source-sha256.tsv`):

```sh
# 1. Build into an empty folder (or an earlier build of this script). --today is the retrieval day (Faroe time);
#    it dates every commit.
python -I build.py ../faroe-islands-law-build --today {{RETRIEVED}}
# 2. Check the build against the retrieved pages; writes verification.json, which the next build puts in README.md.
python -X utf8 check_repo.py ../faroe-islands-law-build
# 3. Build again: the README now carries the check, and a third build gives the same HEAD as the second.
python -I build.py ../faroe-islands-law-build --today {{RETRIEVED}}
```

Python 3.12.10 (standard library only) and git 2.46.0.windows.1.

## What the build produced

- {{ACTS}} acts: {{LOGTINGSLOG}} Løgtingslógir, {{KUNNGERD}} Kunngerðir, {{LOGTINGSLOGARKUNNGERD}} Løgtingslógarkunngerðir; dated {{OLDEST}} to {{NEWEST}}.
- {{UNITS}} unit files: {{PARAGRAPHS}} §, {{ANNEXES}} annexes, and `tekstur.md` for {{NO_PARAGRAPH_ACTS}} acts without a §.
- {{COMMITS}} commits: one `Kind: consolidated` commit per act, all dated {{RETRIEVED}} 12:00 Faroe time and ordered by the act's own date, then one documentation commit.
- {{NOTES}} notes in {{ACTS_WITH_NOTES}} acts; {{AMENDMENT_ROWS}} rows in `data/amendments.csv` naming {{AMENDING_ACTS}} distinct amending acts; {{OTHER_NOTES}} notes name no amending act.
- Roles by title: {{ROLE_PRINCIPAL}} principal, {{ROLE_COMMENCEMENT}} commencement, {{ROLE_REPEALING}} repealing, {{ROLE_AMENDING}} amending (`data/roles.csv`).
- Languages (by counting common Faroese and Danish words in the text): {{LANG_FO}} Faroese, {{LANG_DA}} Danish, {{LANG_MIXED}} both (`data/languages.csv`).
- {{ISSUES}} rows in `data/unreadable.csv` (acts with no § or a repeated § number; their text is complete).

## Decisions made by hand

- The record is current-only: logir.fo has no dated earlier consolidations, and the acts as first published in Kunngerðablaðið were not read.
- Every commit is dated by the retrieval day, not by any date on the page: the site gives no consolidation date, and `Enacted:`/`Published:` are the act's own dates, which would date a 2026 text to 1930.
- A § starts at a paragraph whose text begins "§ N." (with an optional letter, "§ 16 a."), whatever its class: 368 pages have no `Paragraftekst` class. Quoted § text (amending provisions printed inside quotation marks) begins with the quotation mark, so it does not start a §.
- An annex starts at a short paragraph "Fylgiskjal N", "Skjal N" or "Bilag N" (or one with the class `Bilagstitel`) after the first §; after it no § is split off.
- Acts are kept in the site's own three kinds, even where the title shows a commencement, repeal or amending order; those are labelled `Role:`.
- Language is decided per act by counting words found only in Danish (ikke, efter, af, eller, ...) against words found only in Faroese (ikki, eftir, av, ella, ...): 80% or more Danish is `da`, 20% to 80% is `fo+da`.

## Checks

```sh
python -X utf8 tools/build/check_repo.py .     # with the retrieved pages present
git rev-list --merges --count main             # 0
python tools/in_force_on.py {{RETRIEVED}} logtingslog/2015/30 paragraf-9
```

{{CHECK}}

Rebuilding from the same pages gives the same `git rev-parse HEAD`.

## AI

The scripts, the README and these notes were written by Claude Code with Claude Opus 5.5 (`claude-opus-5-5`), working for Lexifina. No AI model writes or changes legal text, and none runs when the repository is built or checked: the build is the Python in `tools/build/`, run as recorded here.
