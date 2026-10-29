# Reproducing this repository

Built from the pages of logir.fo retrieved on 2026-10-29, by the scripts in `tools/build/` (copied there as run). The sha256 of every page the build read is in [`data/source-sha256.tsv`](data/source-sha256.tsv), so a copy of those pages can be checked byte for byte before rebuilding. How the pages were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| build.py | `acf7dc96b593ee849a6eb60e94dfbfe623481ae5c1d95ef2c42f4bb5dc5efa20` |
| docs.py | `243cafa09ffe19bfeaa4d2ed919d4ccd7c8f3c2a2820f514850d5f7c0f52d13f` |
| check_repo.py | `ea0d622e9c1b65a954d0f33db7573f10be21b19a820dd2c92d83e256ff0421f7` |

## Steps

With the retrieved pages in place (each matching its sha256 in `data/source-sha256.tsv`):

```sh
# 1. Build into an empty folder (or an earlier build of this script). --today is the retrieval day (Faroe time);
#    it dates every commit.
python -I build.py ../faroe-islands-law-build --today 2026-10-29
# 2. Check the build against the retrieved pages; writes verification.json, which the next build puts in README.md.
python -X utf8 check_repo.py ../faroe-islands-law-build
# 3. Build again: the README now carries the check, and a third build gives the same HEAD as the second.
python -I build.py ../faroe-islands-law-build --today 2026-10-29
```

Python 3.12.10 (standard library only) and git 2.46.0.windows.1.

## What the build produced

- 1329 acts: 444 Løgtingslógir, 882 Kunngerðir, 3 Løgtingslógarkunngerðir; dated 1930-04-15 to 2026-10-16.
- 19,566 unit files: 19,066 §, 435 annexes, and `tekstur.md` for 65 acts without a §.
- 1330 commits: one `Kind: consolidated` commit per act, all dated 2026-10-29 12:00 Faroe time and ordered by the act's own date, then one documentation commit.
- 1758 notes in 496 acts; 9801 rows in `data/amendments.csv` naming 1409 distinct amending acts; 115 notes name no amending act.
- Roles by title: 1261 principal, 36 commencement, 27 repealing, 5 amending (`data/roles.csv`).
- Languages (by counting common Faroese and Danish words in the text): 1288 Faroese, 13 Danish, 28 both (`data/languages.csv`).
- 87 rows in `data/unreadable.csv` (acts with no § or a repeated § number; their text is complete).

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
python tools/in_force_on.py 2026-10-29 logtingslog/2015/30 paragraf-9
```

`tools/build/check_repo.py` on the previous build from the same cache: 1329 acts read back from git (main, in index.txt order) and compared with the cached pages, 12,890,604 letters and digits, 0 mismatches; 1330 commits, 0 whose final paragraph git does not read as trailers (`%(trailers:only)`), 0 without In-force, 0 backwards, 0 after the build day, 0 merges, 0 with a carriage return; tools/in_force_on.py right on 5 of 5 samples. Head of that build: `475fcb0013d39da8bf7a6d0d27a48c7e37485758`.

Rebuilding from the same pages gives the same `git rev-parse HEAD`.

## AI

The scripts, the README and these notes were written by Claude Code with Claude Opus 5.5 (`claude-opus-5-5`), working for Lexifina. No AI model writes or changes legal text, and none runs when the repository is built or checked: the build is the Python in `tools/build/`, run as recorded here.
