# Sources

| Source | What it gives | Used |
| --- | --- | --- |
| [Lógasavnið](https://logir.fo) (logir.fo), Løgmansskrivstovan | The current consolidated text of every Faroese act, with the site's amendment notes; a list of acts filterable by kind, status and edition | Yes: the text of every act |
| The site's own list of acts | Every act by kind ("Rættarreglubólkur": Løgtingslóg, Kunngerð, Løgtingslógarkunngerð), status ("Galdandi", in force) and edition ("Høvuðsrættarregla", principal act), with number, date and title | Yes: the list of {{ACTS}} acts |
| Each act's page on logir.fo | The act's text, its notes, and a side panel with kind, status, Felagsmál/Sermál, authority ("Myndugleiki"), publication day ("Útgávudagur"), the Kunngerðablaðið issue and the Løgting case | Yes |
| Each act as published in Kunngerðablaðið (PDF or Word on logir.fo) | The text as first published | No |
| Kunngerðablaðið (the official gazette) | The binding text | No |

Retrieved {{RETRIEVED}} (Faroe time). The sha256 of every page the build read is in [`data/source-sha256.tsv`](data/source-sha256.tsv).

## Reuse

- **Terms**: the site's "Fyrivarni" (`/Reservations.aspx`) says only that the text published in Kunngerðablaðið is the binding one and that no liability is taken for errors in the collection. It does not forbid reuse. The footer reads "© Øll rættindi tilskilað" (all rights reserved).
- **Legal basis**: Løgtingslóg nr. 30 frá 30. apríl 2015 um upphavsrætt (Upphavsrættarlógin), § 9, stk. 1: "Lógir, kunngerðir, rundskriv frá myndugleikum, reglugerðir, dómar og onnur líknandi skjøl, sum tað almenna letur gera, eru ikki vard av upphavsrætti." (Laws, executive orders, circulars from the authorities, regulations, judgments and other similar documents that public authorities have made are not protected by copyright.) Stk. 2: the exception does not cover works that are independent contributions to such documents; these may still be reproduced together with the official documents. The act is in this repository as `logtingslog/2015/30` (§ 9 in `paragraf-9.md`).
- **History**: none on the site. The act pages show only the current consolidation ("sum seinast broytt við ..."), with per-provision notes naming the amending acts. There are no dated earlier consolidations, so the record is `current-only`.
