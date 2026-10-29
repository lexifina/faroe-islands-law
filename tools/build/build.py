"""Build the Faroe Islands law repository from the retrieved logir.fo pages.

    python -I scripts/faroe-islands-law/build.py ~/Documents/faroe-islands-law-build --today YYYY-MM-DD [--limit N]

logir.fo (Lógasavnið) publishes the current consolidated text of every act in force and keeps no dated past
consolidations. So the history here starts at that text ("current-only"):

1. Every principal act in force that the site lists (Løgtingslóg, Kunngerð, Løgtingslógarkunngerð) is one law. Each
   § is one file (`paragraf-1.md`, `paragraf-16a.md`), one paragraph per line; chapter headings and § titles go on
   top of the § below them as `##` lines. The act's number, date, title and anything before § 1 is `title.md`, each
   annex (Fylgiskjal, Bilag) is `fylgiskjal-N.md`, and the site's endnotes are `notes.md`, one `[^N]: ...` per note.
   The note markers stay in the text where the site prints them, as `[^N]`.
2. Each law is one commit, `Kind: consolidated`, by the publisher, dated noon Faroe time on the day the text was
   retrieved (the site gives no consolidation date). Every note that names an amending act ("Broytt við løgtingslóg
   nr. 152 frá 20. desember 2013, har § 2 ljóðar soleiðis: ...") is parsed into data/amendments.csv, one row per
   provision that carries its marker. No line is credited to an amending act, because the text before each
   amendment is not published.
3. The whole history is written in one git fast-import stream, sorted, with fixed dates: the same cache always gives
   the same hashes. The target folder must be empty or an earlier build of this script; no remote is ever added.
"""
import argparse
import csv
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
PAGES = CACHE / 'acts'
SITE = 'https://logir.fo'
COMMITTER = 'Lexifina <corpus@lexifina.com>'
PUBLISHER = ('Lógasavnið (Løgmansskrivstovan)', 'logasavn@logir-fo.invalid')
MARKER = '.faroe-islands-law-build'  # inside .git: this folder is a build of this script and may be rebuilt

KINDS = {  # listing category -> (folder, label)
    'Løgtingslóg': ('logtingslog', 'Løgtingslóg'),
    'Kunngerð': ('kunngerd', 'Kunngerð'),
    'Løgtingslógarkunngerð': ('logtingslogarkunngerd', 'Løgtingslógarkunngerð'),
}
MONTHS = {'januar': 1, 'januari': 1, 'februar': 2, 'februari': 2, 'mars': 3, 'marts': 3, 'apríl': 4, 'april': 4,
          'mai': 5, 'maj': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11,
          'desember': 12, 'december': 12}


# ---------------------------------------------------------------------------------------------------- dates

def faroe_offset(day: str) -> int:
    """Hours east of UTC at noon on `day` in Atlantic/Faroe: UTC+0, and UTC+1 with summer time from 1981 (EU rule:
    01:00 UTC on the last Sunday of March to 01:00 UTC on the last Sunday of October). Noon is never on a switch
    hour, so the day decides."""
    d = datetime.strptime(day, '%Y-%m-%d').date()
    if d.year < 1981:
        return 0

    def last_sunday(m: int):
        import datetime as dt
        x = dt.date(d.year, m, 31)
        return x - dt.timedelta(days=(x.weekday() + 1) % 7)
    return 1 if last_sunday(3) <= d < last_sunday(10) else 0


def git_date(day: str) -> str:
    off = faroe_offset(day)
    d = datetime.strptime(day, '%Y-%m-%d')
    ts = int(datetime(d.year, d.month, d.day, 12 - off, 0, tzinfo=timezone.utc).timestamp())
    return f'{ts} +{off:02d}00'


def parse_day(s: str) -> str:
    """'15. april 1930' / '14. mai 2013' / '17-05-2013' -> ISO; '' if unreadable."""
    s = (s or '').strip()
    m = re.fullmatch(r'(\d{1,2})-(\d{1,2})-(\d{4})', s)
    if m:
        return f'{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
    m = re.fullmatch(r'(\d{1,2})\.\s*([^\W\d_]+)\s+(\d{4})', s)
    if m and m.group(2).lower() in MONTHS:
        return f'{int(m.group(3)):04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}'
    return ''


# ---------------------------------------------------------------------------------------------------- html

BLOCK = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'tr', 'blockquote', 'dl', 'dt',
         'dd', 'hr', 'thead', 'tbody', 'center', 'pre'}
NOTE_REF = re.compile(r'#_?(edn|ftn)(\d+)$')         # a marker in the text
NOTE_BACK = re.compile(r'#_?(edn|ftn)ref(\d+)$')     # the number at the start of a note


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    s = s.replace('\xa0', ' ').replace('​', '').replace('\xad', '').replace('﻿', '')
    return re.sub(r'\s+', ' ', s).strip()


class Blocks(HTMLParser):
    """div#div_content -> blocks [{cls, tag, text, note}] in document order. One block per paragraph or table row
    (cells joined with ' | '); <br> starts a new block outside tables. The chapter list the site adds on top
    (UL.ChapterList) is skipped. A note marker that prints its note's number becomes [^N], and the number at the
    start of a note becomes [^N]:; a marker that prints another number, or none, is kept as printed and listed in
    `odd_markers`. Pictures become [image]. `note` is the endnote number a block belongs to (inside div#ednN /
    div#ftnN), else None."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self.cur: list[str] = []
        self.cls = ''
        self.tag = ''
        self.stack: list[tuple[str, bool, int | None]] = []  # (tag, skipping, note number set here)
        self.skip = 0
        self.note: int | None = None
        self.cell = 0
        self.cells_in_row = 0
        self.in_row = False
        self.topnrdato = False
        self.capture: list | None = None  # [kind ('ref'|'back'), N, printed text]
        self.odd_markers: list[str] = []

    def flush(self):
        t = norm(''.join(self.cur))
        if t:
            self.blocks.append({'cls': self.cls, 'tag': self.tag, 'text': t, 'note': self.note,
                                'row': self.in_row})
        self.cur = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        if tag in ('img', 'br', 'hr', 'col', 'meta', 'link', 'input', 'wbr'):
            if self.skip:
                return
            if tag == 'img':
                self.cur.append(' [image] ')
            elif tag == 'br':
                if self.cell:
                    self.cur.append(' ')
                else:
                    self.flush()
            elif tag == 'hr' and not self.cell:
                self.flush()
            return
        cls = a.get('class', '').strip().strip("'\"").split()
        skip = tag in ('style', 'script') or (tag == 'ul' and 'ChapterList' in cls)
        note_here = None
        if tag == 'a' and not self.skip:
            href = a.get('href', '')
            m = NOTE_REF.search(href)
            b = NOTE_BACK.search(href)
            if m or b:
                self.capture = ['ref' if m else 'back', int((m or b).group(2)), []]
                skip = True
        if tag == 'div':
            m = re.fullmatch(r'_?(edn|ftn)(\d+)', a.get('id', ''))
            if m:
                self.flush()
                note_here = int(m.group(2))
        self.stack.append((tag, skip, note_here))
        if note_here is not None:
            self.note = note_here
        if skip:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ('td', 'th'):
            if self.cells_in_row:
                self.cur.append(' | ')
            self.cells_in_row += 1
            self.cell += 1
            return
        if tag == 'tr':
            self.flush()
            self.cells_in_row = 0
            self.in_row = True
            self.cls, self.tag = 'tr', 'tr'
            return
        if tag in BLOCK or tag in ('p',):
            if self.cell:
                self.cur.append(' ')
                return
            self.flush()
            self.cls = cls[0] if cls else ''
            self.tag = tag
            self.topnrdato = tag == 'p' and self.cls == 'topnrdato'

    def handle_endtag(self, tag):
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            return
        popped = self.stack[idx:]
        del self.stack[idx:]
        was_skipping = self.skip > 0
        if tag == 'a' and self.capture is not None and self.skip == 1:
            kind, n, buf = self.capture
            self.capture = None
            printed = norm(''.join(buf))
            if re.sub(r'\D', '', printed) == str(n):
                self.cur.append(f'[^{n}]' if kind == 'ref' else f'[^{n}]: ')
            else:
                self.cur.append(printed + (' ' if kind == 'back' else ''))
                self.odd_markers.append(f"{'marker' if kind == 'ref' else 'note start'} linked to note {n} "
                                        f"prints {printed!r}; kept as printed")
        for _, sk, nh in popped:
            if sk:
                self.skip -= 1
            if nh is not None:
                self.flush()
                self.note = None
        if was_skipping:
            return
        if tag == 'span' and self.topnrdato:
            self.cur.append(' ')  # the date and "Nr." are two floated spans with nothing between them
        if tag in ('td', 'th'):
            self.cell = max(0, self.cell - 1)
            return
        if tag == 'tr':
            self.flush()
            self.cells_in_row = 0
            self.in_row = False
            return
        if tag in BLOCK and not self.cell:
            self.flush()
            self.topnrdato = False

    def handle_data(self, data):
        if self.capture is not None:
            self.capture[2].append(data)
        elif not self.skip:
            self.cur.append(data)

    def close(self):
        super().close()
        self.flush()


def content(html: str) -> str:
    i = html.find('<div id="div_content"')
    j = html.find('<aside', i)
    return html[i:j if j > 0 else len(html)]


def side_info(html: str) -> dict:
    j = html.find('<aside')
    side = html[j:] if j > 0 else ''
    info = {}
    for k, v in re.findall(r'<strong>([^<]*):</strong>\s*([^<]*)</div>', side):
        info[unescape(k).strip()] = norm(unescape(v))
    m = re.search(r'Kunngerðablaðið</h2>\s*<p[^>]*>(.*?)</p>', side, re.S)
    info['gazette'] = norm(unescape(re.sub(r'<[^>]+>', '', m.group(1)))) if m else ''
    m = re.search(r'Løgtingsmál nr:\s*([^<]+)</a>', side)
    info['logtingsmal'] = norm(m.group(1)) if m else ''
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    info['h1'] = norm(unescape(re.sub(r'<[^>]+>', '', m.group(1)))) if m else ''
    return info


# ---------------------------------------------------------------------------------------------------- act

HEADER_CLS = {'topnrdato', 'titel', 'titel2', 'MsoTitle', 'MsoSubtitle', 'subtitel', 'ktitle2', 'NrDato'}
HEADING_CLS = {'Kapitelnummer', 'Kapiteloverskrift', 'Kapittul', 'Tekstoverskrift', 'TekstoverskriftB',
               'TekstoverskriftVB', 'TekstoverskriftVO', 'TekstoverskriftVenstre', 'Afsnitsnummer',
               'Afsnitsoverskrift', 'ParaOverskrift'}
ANNEX_CLS = {'Bilagstitel', 'bilagstitel0'}
PARA = re.compile(r'^(?:\[\^\d+\]\s*)*§\s*(\d+)\s*([a-zA-Z])?\s*\.(?!\d)')
ANNEX = re.compile(r'^(?:\[\^\d+\]\s*)*(Fylgiskjal|Fylgiskjøl|Bilag|Skjal|Appendiks|Anneks|Viðfesti)\b\.?\s*([0-9A-Za-z]{0,6})\b')
TITLE_START = re.compile(r'^(Løgtingslóg|Kunngerð|Løgtingslógarkunngerð|Eykajáttanarløgtingslóg|Lov|Lagtingslov|'
                         r'Anordning|Bekendtgørelse|Kundgørelse|Fíggjarlóg)\b')
HEADING_TEXT = re.compile(r'^(Kapittul|Kapitul|Kapitel|Partur|Táttur|Afsnit|Brot)\s+([0-9]+|[IVXLC]+)\.?\b')


def split_act(blocks: list[dict]) -> tuple[list[tuple[str, list[str]]], dict[int, list[str]], dict]:
    """Body blocks -> [(file stem, lines)] in order, notes {N: lines}, and counts."""
    body = [b for b in blocks if b['note'] is None]
    notes: dict[int, list[str]] = {}
    for b in blocks:
        if b['note'] is not None:
            notes.setdefault(b['note'], []).append(b['text'])
    files: list[tuple[str, list[str]]] = [('title', [])]
    pending: list[str] = []
    seen: dict[str, int] = {}
    first = True
    in_annex = False
    stats = {'paragraphs': 0, 'annexes': 0, 'duplicates': 0}

    def new_file(stem: str):
        nonlocal pending
        if stem in seen:
            seen[stem] += 1
            stats['duplicates'] += 1
            stem = f'{stem}~{seen[stem]}'
        else:
            seen[stem] = 1
        files.append((stem, pending))
        pending = []

    for b in body:
        t, cls = b['text'], b['cls']
        is_header = first and cls in HEADER_CLS and len(files) == 1
        if is_header:
            if cls == 'titel' or cls == 'MsoTitle' or cls == 'titel2':
                files[0][1].append('# ' + t)
            else:
                files[0][1].append(t)
            continue
        first = False
        m = PARA.match(t)
        a = ANNEX.match(t)
        is_annex = a and not b['row'] and len(t) <= 160 and (
            cls in ANNEX_CLS or re.fullmatch(r'(?:\[\^\d+\]\s*)*\S+\.?\s*[0-9A-Za-z]{0,6}\.?', t))
        if is_annex and len(files) > 1:
            in_annex = True
            stats['annexes'] += 1
            label = (a.group(2) or str(stats['annexes'])).lower()
            new_file(f'fylgiskjal-{label}')
            files[-1][1].append('## ' + t)
            continue
        if m and not in_annex and not b['row']:
            stats['paragraphs'] += 1
            new_file(f'paragraf-{int(m.group(1))}{(m.group(2) or "").lower()}')
            files[-1][1].append(t)
            continue
        heading = (cls in HEADING_CLS or b['tag'] in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
                   or (HEADING_TEXT.match(t) and len(t) <= 80)) and not b['row']
        if heading and not in_annex:
            pending.append('## ' + t)
            continue
        if pending:
            files[-1][1].extend(pending)
            pending = []
        files[-1][1].append(t)
    if pending:
        files[-1][1].extend(pending)
    head = files[0][1]
    if not any(l.startswith('# ') for l in head):
        # the title has no title class on some pages: the first line that starts with the act's kind
        for i, l in enumerate(head[:4]):
            if TITLE_START.match(l):
                head[i] = '# ' + l
                break
    if stats['paragraphs'] == 0:
        # no §: the header lines (up to the title) stay in title.md, the rest before any annex is tekstur.md
        title_lines = files[0][1]
        n_head = max((i + 1 for i, l in enumerate(title_lines) if l.startswith('# ')), default=0)
        rest = title_lines[n_head:]
        files = [('title', title_lines[:n_head])] + ([('tekstur', rest)] if rest else []) + files[1:]
    return files, notes, stats


AMEND_KIND = (r'løgtingslógarkunngerð|løgtingslóg|kunngerð|anordning|kongelig anordning|lov|lóg|bekendtgørelse|'
              r'kundgørelse|lovbekendtgørelse|anordningsbekendtgørelse|rundskriv|fyriskipan|tingskipan')
NR_DATE = re.compile(r'\bnr\.\s*(\d+)\s+(?:frá|fra|af|av)\s+(\d{1,2}\.\s*[^\W\d_]+\s+\d{4})', re.I)
KIND_WORD = re.compile(r'\b(' + AMEND_KIND + r')\b', re.I)
AMEND_START = re.compile(r'^(?:\[\^\d+\]:\s*)?(Broytt|Broyttur|Broytt\s+við|Ændret|Tilføjet|Ophævet|Strikað|Sett inn|'
                         r'Sett í gildi|Nýtt|Orðað)', re.I)


def parse_note(text: str) -> tuple[list[tuple[str, str, str]], str]:
    """'Broytt við løgtingslóg nr. 152 frá 20. desember 2013, har § 2 ljóðar soleiðis: “...”' ->
    ([(kind, nr, iso date)], in-force clause). Only the words before the quoted clause are read for acts."""
    body = re.sub(r'^\[\^\d+\]:\s*', '', text)
    if not re.search(r'\b(broytt|ændret|ophævet|tilføjet|strikað|sett inn)\b', body[:200], re.I):
        return [], ''
    q = re.search(r'(ljóðar|lyder)\s+soleiðis:|ljóðar\s+so:|lyder\s+således:|[“"„»]', body)
    head = body[:q.start()] if q else body
    clause = ''
    if q:
        clause = body[q.end():].strip() if q.group(0)[0] not in '“"„»' else body[q.start():].strip()
        clause = clause.strip(' “”"„»«')
    acts = []
    for m in NR_DATE.finditer(head):
        kinds = KIND_WORD.findall(head[:m.start()])
        kind = kinds[-1].lower() if kinds else ''
        acts.append((kind, m.group(1), parse_day(m.group(2)) or m.group(2)))
    return acts, clause


def language(lines: list[str]) -> str:
    words = re.findall(r'[^\W\d_]+', ' '.join(lines).lower())
    da = sum(1 for w in words if w in ('ikke', 'efter', 'af', 'eller', 'være', 'denne', 'bliver', 'hvis', 'nærmere',
                                       'skal', 'til', 'paa', 'på', 'med', 'om'))
    fo = sum(1 for w in words if w in ('ikki', 'eftir', 'av', 'ella', 'vera', 'henda', 'verður', 'hesi', 'nærri',
                                       'skal', 'til', 'á', 'við', 'um'))
    # 'skal', 'til' count for both; the others decide
    da_only = da - sum(1 for w in words if w in ('skal', 'til'))
    fo_only = fo - sum(1 for w in words if w in ('skal', 'til'))
    tot = da_only + fo_only
    if not tot:
        return 'fo'
    if da_only / tot >= 0.8:
        return 'da'
    if da_only / tot >= 0.2:
        return 'fo+da'
    return 'fo'


ROLE_REPEAL = re.compile(r'\búr gildi\b', re.I)
ROLE_COMMENCE = re.compile(r'(seta í gildi|gildiskomu|koma í gildi|kemur í gildi|fær gildi|fáa gildi)', re.I)
ROLE_AMEND = re.compile(r'\bbroyting(ar)? í\b', re.I)


def role(title: str) -> str:
    """What the listing title says the act does. logir.fo lists every one of these as a principal act in force
    (Høvuðsrættarregla, Galdandi); the title tells repeal orders, commencement orders and amending orders apart."""
    if ROLE_REPEAL.search(title):
        return 'repealing'
    if ROLE_COMMENCE.search(title):
        return 'commencement'
    if ROLE_AMEND.search(title):
        return 'amending'
    return 'principal'


def page_key(href: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]', '_', href.strip('/'))[:180]


def load_acts(limit: int | None = None) -> list[dict]:
    rows = json.loads((CACHE / 'list.json').read_text('utf-8'))['rows']
    acts = []
    for r in rows:
        folder, label = KINDS[r['category']]
        nr = re.sub(r'\D', '', r['nr'])
        day = parse_day(r['date'])
        acts.append({'category': r['category'], 'folder': folder, 'label': label, 'nr': nr, 'enacted': day,
                     'enacted_as_printed': r['date'], 'href': r['href'], 'title': r['title'], 'heading': r['heading'],
                     'url': SITE + '/' + r['href'], 'page': PAGES / (page_key(r['href']) + '.html'),
                     'role': role(r['title'])})
    used: dict[str, str] = {}
    for a in sorted(acts, key=lambda a: (a['folder'], a['enacted'], int(a['nr'] or 0), a['href'])):
        base = f"{a['folder']}/{a['enacted'][:4]}/{a['nr']}"
        d, k = base, 2
        while d in used:
            d = f'{base}-{k}'
            k += 1
        used[d] = a['href']
        a['dir'] = d
    acts.sort(key=lambda a: (a['enacted'], list(KINDS).index(a['category']), int(a['nr'] or 0), a['dir']))
    return acts[:limit] if limit else acts


def build_act(a: dict) -> dict:
    """path -> text for one act, plus amendment rows and counts."""
    html = a['page'].read_text('utf-8')
    p = Blocks()
    p.feed(content(html))
    p.close()
    files, notes, st = split_act(p.blocks)
    info = side_info(html)
    out: dict[str, str] = {}
    order = []
    for stem, lines in files:
        if not lines:
            continue
        out[f"{a['dir']}/{stem}.md"] = '\n'.join(lines) + '\n'
        order.append(f'{stem}.md')
    note_lines = []
    issues = list(p.odd_markers)
    for n in sorted(notes):
        if not notes[n][0].startswith(f'[^{n}]:'):
            issues.append(f'note {n} does not start with its own number; its first line in notes.md is as printed')
        note_lines += notes[n]
    if note_lines:
        out[f"{a['dir']}/notes.md"] = '\n'.join(note_lines) + '\n'
        order.append('notes.md')
    out[f"{a['dir']}/index.txt"] = '\n'.join(order) + '\n'
    # where each note's markers are: file and Stk.
    where: dict[int, list[tuple[str, str]]] = {}
    for stem, lines in files:
        stk = ''
        for l in lines:
            m = re.match(r'^(?:\[\^\d+\]\s*)*(?:Stk\.\s*(\d+)\.|(\d+)\.\s*stk\.)', l)
            if m:
                stk = f'stk. {m.group(1) or m.group(2)}'
            elif PARA.match(l):
                stk = ''
            for n in re.findall(r'\[\^(\d+)\](?!:)', l):
                key = (stem, stk)
                lst = where.setdefault(int(n), [])
                if key not in lst:
                    lst.append(key)
    amend = []
    other_notes = 0
    for n in sorted(notes):
        text = ' '.join(notes[n])
        acts, clause = parse_note(text)
        if not acts:
            other_notes += 1
            continue
        for stem, stk in where.get(n, [('', '')]):
            for kind, nr, day in acts:
                amend.append([a['dir'], stem, stk, str(n), kind, nr, day, clause,
                              re.sub(r'^\[\^\d+\]:\s*', '', text)])
    body_lines = [l for stem, ls in files for l in ls]
    return {'files': out, 'amend': amend, 'info': info, 'stats': st, 'notes': len(notes), 'issues': issues,
            'other_notes': other_notes, 'language': language(body_lines),
            'units': sum(1 for s, ls in files if ls and s.startswith(('paragraf-', 'fylgiskjal-', 'tekstur'))),
            'title_line': next((l[2:] for l in files[0][1] if l.startswith('# ')), '')}


# ---------------------------------------------------------------------------------------------------- write

LANG_NAME = {'fo': 'Faroese', 'da': 'Danish', 'fo+da': 'Faroese and Danish'}


def message(a: dict, day: str, built: dict) -> str:
    info = built['info']
    subject = f"{a['label']} nr. {a['nr']}/{a['enacted'][:4]}: current text on logir.fo, {day}"
    heading = a['heading'].removesuffix(' (Galdandi)')
    body = [heading + '.', '',
            f"The text of this {a['label']} as Lógasavnið (logir.fo) publishes it, consolidated with every amendment",
            f'the site has worked in, retrieved on {day}. logir.fo keeps no earlier consolidations, so this commit holds',
            'the whole text and nobody is credited with single lines. The notes the site prints are kept: the',
            f"markers [^N] in the text and the notes themselves in notes.md ({built['notes']} notes; data/amendments.csv",
            'lists the amending acts they name).']
    if a['role'] == 'amending':
        body += ['', f"logir.fo lists this {a['label']} as a principal act in force, but its title says it is a change",
                 '("broyting í ...") to another act or list (Role: amending).']
    elif a['role'] == 'commencement':
        body += ['', f"logir.fo lists this {a['label']} as a principal act in force, but its title says it brings",
                 'another act, or provisions of one, into force (Role: commencement).']
    elif a['role'] == 'repealing':
        body += ['', f"logir.fo lists this {a['label']} as a principal act in force, but its title says it repeals",
                 'other acts ("at seta úr gildi", Role: repealing).']
    if built['language'] != 'fo':
        body += ['', f"The text is in {LANG_NAME[built['language']]}, as on the site."]
    tr = ['Kind: consolidated', f'In-force: {day}', f'Consolidated: {day}', 'Date-source: retrieved']
    if a['enacted']:
        tr.append(f"Enacted: {a['enacted']}")
    pub = parse_day(info.get('Útgávudagur', ''))
    if pub:
        tr.append(f'Published: {pub}')
    if info.get('gazette'):
        tr.append(f"Gazette: {info['gazette']}")
    tr += [f"Law: {a['label']} nr. {a['nr']} frá {a['enacted_as_printed']}", f"Law-kind: {a['folder']}",
           f"Law-number: {a['nr']}", f"Role: {a['role']}", f"Language: {built['language']}"]
    if info.get('Myndugleiki'):
        tr.append(f"Authority: {info['Myndugleiki']}")
    if info.get('Felagsmál/Sermál'):
        tr.append(f"Competence: {info['Felagsmál/Sermál']}")
    if info.get('logtingsmal'):
        tr.append(f"Logting-case: {info['logtingsmal']}")
    tr.append(f"Notes: {built['notes']}")
    tr.append(f"Source: {a['url']}")
    return '\n'.join([subject, '', *body, '', *tr]) + '\n'


def fast_import(repo: Path, commits: list[tuple], docs: dict[str, bytes], today: str) -> None:
    name, email = PUBLISHER
    buf = io.BytesIO()
    w = buf.write
    mark = 0
    for day, a, built in commits:
        mark += 1
        when = git_date(day)
        msg = message(a, day, built).encode('utf-8')
        w(f'commit refs/heads/main\nmark :{mark}\n'.encode())
        w(f'author {name} <{email}> {when}\ncommitter {COMMITTER} {when}\n'.encode('utf-8'))
        w(f'data {len(msg)}\n'.encode() + msg + b'\n')
        if mark > 1:
            w(f'from :{mark - 1}\n'.encode())
        for path, text in sorted(built['files'].items()):
            t = text.encode('utf-8')
            w(f'M 100644 inline {path}\ndata {len(t)}\n'.encode('utf-8') + t + b'\n')
        w(b'\n')
    when = git_date(today)
    msg = (f'Documentation: README, REPRODUCE, SOURCES, corpus.json, laws.csv, data and tools\n\n'
           f'Built from the logir.fo cache retrieved on {today}.\n\nKind: documentation\n').encode()
    w(f'commit refs/heads/main\nmark :{mark + 1}\n'.encode())
    w(f'author {COMMITTER} {when}\ncommitter {COMMITTER} {when}\n'.encode())
    w(f'data {len(msg)}\n'.encode() + msg + b'\n')
    if mark:
        w(f'from :{mark}\n'.encode())
    for path, data in sorted(docs.items()):
        w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode('utf-8') + data + b'\n')
    w(b'\ndone\n')
    r = subprocess.run(['git', '-C', str(repo), 'fast-import', '--quiet', '--done'], input=buf.getvalue(),
                       capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode('utf-8', 'replace')[-3000:])


def prepare(repo: Path) -> None:
    """An empty folder, or an earlier build of this script (wiped); anything else is refused."""
    if repo.exists() and any(repo.iterdir()):
        if not (repo / '.git' / MARKER).exists():
            sys.exit(f'{repo} is not empty and is not an earlier build of this script; refusing to touch it')

        def onerr(func, path, _):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        for child in repo.iterdir():
            shutil.rmtree(child, onerror=onerr) if child.is_dir() else child.unlink()
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    for k, v in (('core.autocrlf', 'false'), ('core.longpaths', 'true'), ('core.quotepath', 'false')):
        subprocess.run(['git', '-C', str(repo), 'config', k, v], check=True)
    (repo / '.git' / MARKER).write_text('built by scripts/faroe-islands-law/build.py; never pushed from here\n',
                                        encoding='utf-8')


def retrieved_day() -> str:
    """The Faroe-time day the act pages were retrieved, from the retrieval log kept with them."""
    runs = [json.loads(l) for l in (CACHE / 'fetch-log.jsonl').read_text('utf-8').splitlines() if l.strip()]
    t = datetime.strptime(runs[-1]['when'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    off = faroe_offset(t.strftime('%Y-%m-%d'))
    return datetime.fromtimestamp(t.timestamp() + off * 3600, timezone.utc).strftime('%Y-%m-%d')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True, help='the retrieval day; dates every commit (YYYY-MM-DD)')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.today):
        sys.exit('--today must be YYYY-MM-DD')
    fetched = retrieved_day()
    if fetched != args.today:
        sys.exit(f'the cache was retrieved on {fetched} (Faroe time); pass --today {fetched}')
    acts = load_acts(args.limit)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(min(args.workers, 8)) as pool:
        results = list(pool.map(build_act, acts, chunksize=8))
    commits, amend, issues = [], [], []
    for a, built in zip(acts, results):
        a.update({'language': built['language'], 'notes': built['notes'], 'other_notes': built['other_notes'],
                  'units': built['units'], 'paragraphs': built['stats']['paragraphs'],
                  'annexes': built['stats']['annexes'], 'duplicates': built['stats']['duplicates'],
                  'published': parse_day(built['info'].get('Útgávudagur', '')),
                  'authority': built['info'].get('Myndugleiki', ''), 'gazette': built['info'].get('gazette', ''),
                  'status': built['info'].get('Gildisstøða', ''), 'title_line': built['title_line']})
        amend += built['amend']
        issues += [[a['dir'], i] for i in built['issues']]
        if not a['enacted']:
            issues.append([a['dir'], f"act date {a['enacted_as_printed']!r} could not be read"])
        if a['paragraphs'] == 0:
            issues.append([a['dir'], 'no § found; the text is in tekstur.md'])
        if a['duplicates']:
            issues.append([a['dir'], f"{a['duplicates']} § number(s) occur twice outside quotation marks; the later "
                                     'one is paragraf-N~2.md'])
        if a['status'] != 'Galdandi':
            issues.append([a['dir'], f"status on the page is {a['status']!r}"])
        commits.append((args.today, a, built))
    print(f"{len(acts)} acts, {len(commits)} commits, {sum(a['units'] for a in acts)} unit files, "
          f"{len(amend)} amendment rows, {len(issues)} issues", flush=True)
    sys.path.insert(0, str(HERE))  # python -I leaves the script's folder off sys.path
    import docs as docmod
    docs = docmod.render(acts, commits, issues, amend, args.today)
    prepare(args.repo)
    fast_import(args.repo, commits, docs, args.today)
    subprocess.run(['git', '-C', str(args.repo), 'checkout', '-q', '-f', 'main'], check=True)
    head = subprocess.run(['git', '-C', str(args.repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    count = subprocess.run(['git', '-C', str(args.repo), 'rev-list', '--count', 'HEAD'], capture_output=True,
                           text=True).stdout.strip()
    print(f'built {args.repo}: {count} commits, head {head}', flush=True)


if __name__ == '__main__':
    main()
