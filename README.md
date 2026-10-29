# The laws of the Faroe Islands, as a git repository

The acts of the Faroe Islands in force, as a git repository: 444 Løgtingslógir (acts of the Løgting, `logtingslog/`), 882 Kunngerðir (executive orders, `kunngerd/`) and 3 Løgtingslógarkunngerðir (consolidated acts promulgated as a whole, such as the traffic act, the tax act and the criminal code, `logtingslogarkunngerd/`). That is every principal act ("Høvuðsrættarregla") that the official law collection, [Lógasavnið](https://logir.fo) (logir.fo), listed as in force ("Galdandi") on 2026-10-29: 1329 acts, from 1930-04-15 to 2026-10-16. Every § is one file (19,066 § files, 19,566 unit files with annexes), with one paragraph per line, so `git blame` and `git diff` work line by line. The text is as published: Faroese, and for 13 acts Danish (28 more mix the two; see [`data/languages.csv`](data/languages.csv)).

**Current text only: there is no history before 2026-10-29.** logir.fo publishes the current consolidated text of each act, with every amendment worked in, and keeps no dated earlier consolidations. So each act is one commit holding its whole text as retrieved on 2026-10-29, and nothing before that day can be reconstructed from this source: there is no line-by-line history before the record starts. New retrievals will be added as later commits, so the history grows forward from here. What the site does say about the past is kept: it marks each amended provision with a note number, and each note names the amending act and often quotes its in-force clause ("Broytt við løgtingslóg nr. 152 frá 20. desember 2013, har § 2 ljóðar soleiðis: “Henda løgtingslóg kemur í gildi 1. januar 2014.”"). The markers stay in the text as `[^N]`, the notes are in each act's `notes.md`, and [`data/amendments.csv`](data/amendments.csv) lists them by provision (9801 rows naming 1409 amending acts).

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What does § 1 of the pensions act (Eftirlønarlógin, Løgtingslóg nr. 49/2013) say? | `python tools/in_force_on.py 2026-10-29 logtingslog/2013/49 paragraf-1` |
| The whole of an act, in order | `python tools/in_force_on.py 2026-10-29 logtingslog/2013/49` |
| Which acts amended a provision, and when they came into force | `grep '^logtingslog/2013/49,paragraf-2,' data/amendments.csv` |
| The notes of an act, as the site prints them | `cat logtingslog/2013/49/notes.md` |
| Every provision an amending act changed, in every act (here Løgtingslóg nr. 23 of 26 February 2026) | `grep ',løgtingslóg,23,2026-02-26,' data/amendments.csv` |
| What changed in an act since this record started (after later retrievals) | `git log -p --word-diff -- logtingslog/2013/49` |
| Which retrieval last wrote each line | `git blame logtingslog/2013/49/paragraf-2.md` |
| Which acts cite the copyright act | `git grep -l 'upphavsrætt'` |
| The list of acts, with their dates, authority, role and language | [`laws.csv`](laws.csv) |
| The acts the site lists as principal but whose title says they amend, commence or repeal another | [`data/roles.csv`](data/roles.csv) |

Files: `<kind>/<year>/<number>/` per act, after its number and the year of its date (`logtingslog/2013/49` is Løgtingslóg nr. 49 frá 14. mai 2013). `title.md` holds the date and number as the site prints them, the title (`# ...`), any short name in brackets, and everything before § 1 (the enacting formula, "Við heimild í ..."). Each § is `paragraf-<n>.md` (`paragraf-16a.md` for § 16 a); chapter headings and § titles that stand before a § are its first lines, as `## ...`. Its paragraphs follow, one per line (`Stk. 2. ...`, numbered items `1) ...`, `a) ...`). The signature lines after the last § stay in that §'s file. Annexes are `fylgiskjal-<n>.md` (Fylgiskjal, Skjal, Bilag). An act without any § (most are short commencement or repeal orders) has its text in `tekstur.md`. Where a § number occurs twice outside quotation marks (in 10 acts, usually a later act's in-force rule printed after the last §, or a Danish order reproduced in an annex), the later one is `paragraf-<n>~2.md`. `notes.md` has one `[^N]: ...` per note. Where a marker on the site prints a different number from the note it links to, or none (2 markers), and where a note's own number is printed differently or not at all (5 notes), the text is kept exactly as printed and the case is listed in [`data/unreadable.csv`](data/unreadable.csv). `index.txt` gives the reading order. Table rows are one line with cells joined by ` | `; pictures are `[image]`.

## The dates, and which one we use

**Every act is dated 2026-10-29, the day its text was retrieved**, at noon Faroe time (UTC+0 in winter, UTC+1 in summer), in the `In-force:` and `Consolidated:` trailers and as the commit date (`Date-source: retrieved`). It means: the text the publisher gave as in force that day. logir.fo gives no date for its consolidations, and it updates them quickly (an amendment of 9 October 2026 was already worked into the pensions act), but the commit date is not the date any amendment took effect and is not proof that the text was in force on that day.

Each commit also carries the act's own dates: `Enacted:` is the date in its title ("frá 14. mai 2013", the day it was signed, staðfest or issued) and `Published:` the day it appeared in Kunngerðablaðið ("Útgávudagur" on the site), with `Gazette:` naming the issue. The dates on which amendments took effect are in the notes: [`data/amendments.csv`](data/amendments.csv) gives each amending act's own date and, in `in_force_clause`, its in-force rule as the site quotes it. They are not turned into commit dates, because the rule often depends on publication ("dagin eftir, at hon er kunngjørd") or on a later order.

`tools/in_force_on.py DATE PATH [UNIT]` reads the `In-force:` trailers, so it does not depend on your time zone. For a date before 2026-10-29 it says there is no version, because the source has none.

## What "author" means

Every law-text commit has the same author: `Lógasavnið (Løgmansskrivstovan) <logasavn@logir-fo.invalid>`, with the trailer `Kind: consolidated` (the address cannot exist). The author is the publisher of the consolidation, not a lawmaker: no line is credited to an amending act, because without the earlier text nobody can tell which words an amendment wrote. The notes say which acts changed a provision; they are kept as text and data, not used to credit lines. In the shared design of these repositories, a later change will be credited to an amending act only where the source shows the text before and after it and a new note names that act; otherwise it is labelled `Kind: unexplained`.

1330 commits: one per act (1329) and one documentation commit, authored by Lexifina. Each commit's trailers also give `Law:`, `Law-kind:`, `Law-number:`, `Authority:` (the ministry, "Myndugleiki"), `Competence:` (Felagsmál, a joint Faroese-Danish matter, or Sermál, a Faroese special matter), `Role:`, `Language:`, `Notes:` and `Source:` (the page on logir.fo).

**Role.** logir.fo lists all 1329 acts as principal acts in force. For most (1261) that is what they are. The title of 36 says they bring another act, or parts of one, into force ("at seta í gildi ...", "gildiskomu av ..."; `Role: commencement`), 27 that they repeal other acts ("at seta úr gildi ..."; `Role: repealing`), and 5 Kunngerðir that they are changes to another act or list ("broyting í kunngerð um ..."; `Role: amending`). They are kept as the site lists them, labelled, and listed in [`data/roles.csv`](data/roles.csv).

## What it does not show

- Any text before 2026-10-29. logir.fo keeps no dated earlier consolidations, and the acts as first published in Kunngerðablaðið were not read.
- Acts that are no longer in force ("Áður galdandi", "Søgulig"), acts not yet in force ("Í koming"), and amending acts, which the site lists separately ("Broytingarrættarregla"). The other kinds of rule the site holds (Danish laws and orders in force for the Faroe Islands such as "Lov", "Anordning" and "Bekendtgørelse", Tingskipan, Rundskriv and so on) are not in this record: only the three Faroese kinds named above.
- Formatting (bold, italics, indentation, column layout of tables) and pictures (`[image]`).
- The notes that are not amendment notes (for example explanations in a table or a list of countries; 115 of 1758 notes) are in `notes.md` but not in `data/amendments.csv`.
- Acts the parser could only partly structure: 65 acts have no § and are one `tekstur.md`, 10 have a repeated § number, and a few note markers are printed with the wrong number or none (see above). They are listed in [`data/unreadable.csv`](data/unreadable.csv) (87 rows); their text is complete.

This is a research aid. Lógasavnið says that only the text published in Kunngerðablaðið is binding ("Fyrivarni"), and the same is true here.

## How it is checked

Before publishing, `tools/build/check_repo.py` read every act back from git and compared it with the page the site served, independently of the builder: it strips the tags of the page's text area with a regular expression (leaving out only the chapter list the site adds on top), keeps the letters and digits in order, and compares them with the letters and digits of the act's files read in `index.txt` order (leaving out `[image]`). The note markers `[^N]` keep the site's note numbers, so they compare too. It also checks that git reads every commit's final paragraph as trailers (`git log --format=%(trailers:only)`), that every law commit has `In-force:`, that there are no merges, no dates that go backwards and none after the build day, no carriage returns in messages, and that `tools/in_force_on.py` prints the right text for sample provisions and refuses a date before the record.

`tools/build/check_repo.py` on the previous build from the same cache: 1329 acts read back from git (main, in index.txt order) and compared with the cached pages, 12,890,604 letters and digits, 0 mismatches; 1330 commits, 0 whose final paragraph git does not read as trailers (`%(trailers:only)`), 0 without In-force, 0 backwards, 0 after the build day, 0 merges, 0 with a carriage return; tools/in_force_on.py right on 5 of 5 samples. Head of that build: `c0fc2280f2c41f5f16def438902ef7ad42f7e200`.

Two builds from the same cache give the same HEAD. See [`REPRODUCE.md`](REPRODUCE.md).

## How it is built

The record is built from the site's own list of acts (principal acts in force of the three kinds) and each act's page, as retrieved on 2026-10-29. `build.py` reads the act's text area (`div#div_content`, the Word-generated HTML the site shows), splits it at each paragraph that starts with "§ N.", puts chapter headings on the § below them, and writes one commit per act with one `git fast-import`. No AI model takes part in building or checking it. See [`REPRODUCE.md`](REPRODUCE.md) and [`SOURCES.md`](SOURCES.md).

## Licence

Source: Lógasavnið, https://logir.fo, the Faroese law collection published by Løgmansskrivstovan. The site's footer reads "© Øll rættindi tilskilað" (all rights reserved), but official texts are not protected by copyright in the Faroe Islands: Løgtingslóg nr. 30 frá 30. apríl 2015 um upphavsrætt (Upphavsrættarlógin), § 9, stk. 1, as published on logir.fo (`logtingslog/2015/30/paragraf-9.md`), reads: "Lógir, kunngerðir, rundskriv frá myndugleikum, reglugerðir, dómar og onnur líknandi skjøl, sum tað almenna letur gera, eru ikki vard av upphavsrætti." (Laws, executive orders, circulars from the authorities, regulations, judgments and other similar documents that public authorities have made are not protected by copyright.) Under stk. 2, independent contributions to such documents stay protected, but may be reproduced together with them. The reservation on the site may cover its own material (design, software, editorial apparatus). The wording of the acts was not changed; it was only split into files and lines. **This repository is private.** Lexifina's own contributions (the tools, the arrangement and the commit messages) are CC0. See [`LICENSE`](LICENSE).
