"""README, REPRODUCE.md, SOURCES.md, LICENSE, corpus.json, laws.csv, data/ and tools for the Faroe Islands law
repository (called by build.py; every file is generated, so a rebuild keeps them current)."""
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILES = HERE / 'repo'
CACHE = HERE / '.cache'
# Published with the record. The retrieval script and its notes stay private (the user's rule of 2026-10-29), and
# publish_gate (gitlaw_common, private) checks every file before it is written.
BUILD_FILES = ('build.py', 'docs.py', 'check_repo.py')
sys.path.insert(0, str(HERE.parent / 'gitlaw_common'))
from publish_gate import publish_gate  # noqa: E402

CITATION = {'file': r'(.+)/paragraf-([0-9]+[a-z]?)(~[0-9]+)?\.md',
            'cites': '§ ?{n}([^0-9a-z]|$)'}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _csv(rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def source_sums() -> str:
    paths = [CACHE / 'list.json', *sorted(CACHE.glob('list-*.html')), *sorted((CACHE / 'acts').glob('*.html'))]
    return ''.join(f"{p.relative_to(CACHE).as_posix()}\t{_sha(p)}\n" for p in paths)


def fetch_runs() -> list[dict]:
    p = CACHE / 'fetch-log.jsonl'
    return [json.loads(l) for l in p.read_text('utf-8').splitlines() if l.strip()] if p.exists() else []


def render(acts: list[dict], commits: list[tuple], issues: list[list[str]], amend: list[list[str]],
           today: str) -> dict[str, bytes]:
    by_kind = Counter(a['folder'] for a in acts)
    roles = Counter(a['role'] for a in acts)
    langs = Counter(a['language'] for a in acts)
    amending = {(r[4], r[5], r[6]) for r in amend}
    runs = fetch_runs()
    stats = {
        'today': today, 'retrieved': today, 'acts': len(acts), 'commits': len(commits) + 1,
        'logtingslog': by_kind.get('logtingslog', 0), 'kunngerd': by_kind.get('kunngerd', 0),
        'logtingslogarkunngerd': by_kind.get('logtingslogarkunngerd', 0),
        'units': sum(a['units'] for a in acts), 'paragraphs': sum(a['paragraphs'] for a in acts),
        'annexes': sum(a['annexes'] for a in acts), 'no_paragraph_acts': sum(1 for a in acts if not a['paragraphs']),
        'duplicate_acts': sum(1 for a in acts if a['duplicates']),
        'notes': sum(a['notes'] for a in acts), 'other_notes': sum(a['other_notes'] for a in acts),
        'acts_with_notes': sum(1 for a in acts if a['notes']),
        'amendment_rows': len(amend), 'amending_acts': len(amending),
        'role_principal': roles.get('principal', 0), 'role_amending': roles.get('amending', 0),
        'role_commencement': roles.get('commencement', 0), 'role_repealing': roles.get('repealing', 0),
        'lang_fo': langs.get('fo', 0), 'lang_da': langs.get('da', 0), 'lang_mixed': langs.get('fo+da', 0),
        'oldest': min(a['enacted'] for a in acts if a['enacted']), 'newest': max(a['enacted'] for a in acts),
        'issues': len(issues),
        'odd_markers': sum(1 for i in issues if 'kept as printed' in i[1] and i[1].startswith('marker')),
        'odd_note_starts': sum(1 for i in issues if 'kept as printed' in i[1] and i[1].startswith('note start')),
        'requests': sum(r['stats']['requests'] for r in runs) + 5,
        'megabytes': round(sum(r['stats']['bytes'] for r in runs) / 1e6),
    }
    ver = HERE / 'verification.json'
    if ver.exists():
        v = json.loads(ver.read_text('utf-8'))
        check = (f"`tools/build/check_repo.py` on the previous build from the same cache: {v['acts']} acts read back from "
                 f"git (main, in index.txt order) and compared with the cached pages, {v['chars']:,} letters and digits, "
                 f"{v['mismatches']} mismatches; {v['commits']} commits, {v['bad_trailers']} whose final paragraph git does not "
                 f"read as trailers (`%(trailers:only)`), {v['no_inforce']} without In-force, {v['backwards']} backwards, "
                 f"{v['future']} after the build day, {v['merges']} merges, {v['crs']} with a carriage return; "
                 f"tools/in_force_on.py right on {v['tool_ok']} of {v['tool_samples']} samples. Head of that build: "
                 f"`{v['head']}`.")
    else:
        check = 'Not yet run for this build.'
    stats['check'] = check

    def fill(s: str) -> str:
        for k, v in stats.items():
            s = s.replace('{{' + k.upper() + '}}', f'{v:,}' if isinstance(v, int) and v >= 10000 else str(v))
        for name in BUILD_FILES:
            s = s.replace('{{SHA_' + name.upper().replace('.', '_') + '}}', _sha(HERE / name))
        return s

    lang_rows = [[a['dir'], a['language'], a['label'] + ' nr. ' + a['nr'] + ' frá ' + a['enacted_as_printed'],
                  a['title']] for a in acts if a['language'] != 'fo']
    corpus = {
        'corpus': 'fo/national/acts',
        'name': 'Faroe Islands: Løgtingslógir, Kunngerðir and Løgtingslógarkunngerðir in force (Lógasavnið, logir.fo)',
        'label': 'Faroe Islands',
        'language': 'fo',
        'languages': {'fo': stats['lang_fo'], 'da': stats['lang_da'], 'fo+da': stats['lang_mixed'],
                      'list': 'data/languages.csv'},
        'acts': {'logtingslog': stats['logtingslog'], 'kunngerd': stats['kunngerd'],
                 'logtingslogarkunngerd': stats['logtingslogarkunngerd']},
        'history': 'current-only',
        'history_from': today,
        'record_to': today,
        'checked_on': today,
        'record_note': (f"logir.fo publishes only the current consolidated text of each act, so each act has one version "
                        f"here: the text as retrieved on {today}. There is no line-by-line history before that day. "
                        f"The site's amendment notes are kept in each act's notes.md and parsed into "
                        f"data/amendments.csv ({stats['amendment_rows']} rows naming {stats['amending_acts']} amending acts)."),
        'built': today,
        'baseline_trailer': 'Consolidated',
        'in_force_trailer': 'In-force',
        'has_future_branch': False,
        'future_branch': None,
        'dates': {'commit': 'the retrieval day (logir.fo gives no consolidation date); Date-source: retrieved',
                  'baseline_trailer': 'Consolidated', 'other_trailers': ['Enacted', 'Published'],
                  'time': '12:00 Atlantic/Faroe (UTC+0; UTC+1 with summer time, EU rule, from 1981)',
                  'before_1970': 'not needed: every commit is dated by the retrieval day'},
        'author': {'consolidated': 'Lógasavnið (Løgmansskrivstovan)', 'amendment': 'none (current-only)',
                   'unexplained': 'none yet'},
        'scope': {
            'trailer': 'Applies',
            'when_absent': ('not extracted for the Faroe Islands; each amending act\'s in-force clause, where the site '
                            'quotes it, is in data/amendments.csv (in_force_clause)'),
            'default_reach': {
                'rule': 'presumption against retroactivity',
                'meaning': ('an act applies from its entry into force and does not reach completed facts unless it '
                            'says so; criminal law is not applied retroactively to the accused\'s detriment'),
                'authority': ('general principle of Danish-Faroese law; for criminal law Revsilógin (Løgtingslógarkunngerð '
                              'nr. 8/2024, logtingslogarkunngerd/2024/8) § 1 (no punishment without law) and § 3 '
                              '(a change after the act: the new law, but never harsher than the old)'),
                'decided_here': False,
            },
        },
        'citation': CITATION,
        'tool': 'tools/in_force_on.py',
    }
    laws_csv = _csv([['kind', 'number', 'enacted', 'published', 'role', 'language', 'authority', 'paragraphs',
                      'annexes', 'notes', 'title', 'path', 'source']] +
                    [[a['folder'], a['nr'], a['enacted'], a['published'], a['role'], a['language'], a['authority'],
                      a['paragraphs'], a['annexes'], a['notes'], a['heading'].removesuffix(' (Galdandi)'),
                      a['dir'] + '/', a['url']] for a in acts])
    roles_csv = _csv([['path', 'role', 'title']] + [[a['dir'], a['role'], a['heading'].removesuffix(' (Galdandi)')]
                                                    for a in acts if a['role'] != 'principal'])
    files = {
        'corpus.json': (json.dumps(corpus, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
        'README.md': fill((REPO_FILES / 'README.md').read_text('utf-8')).encode('utf-8'),
        'REPRODUCE.md': fill((REPO_FILES / 'REPRODUCE.md').read_text('utf-8')).encode('utf-8'),
        'SOURCES.md': fill((REPO_FILES / 'SOURCES.md').read_text('utf-8')).encode('utf-8'),
        'LICENSE': (REPO_FILES / 'LICENSE').read_bytes(),
        'laws.csv': laws_csv,
        'data/amendments.csv': _csv([['act', 'provision', 'stk', 'note', 'amending_kind', 'amending_number',
                                      'amending_date', 'in_force_clause', 'note_text']] + amend),
        'data/roles.csv': roles_csv,
        'data/languages.csv': _csv([['path', 'language', 'act', 'title']] + lang_rows),
        'data/unreadable.csv': _csv([['act', 'issue']] + issues),
        'data/stats.json': (json.dumps({k: v for k, v in stats.items() if k != 'check'}, ensure_ascii=False, indent=1,
                                       sort_keys=True) + '\n').encode('utf-8'),
        'data/source-sha256.tsv': source_sums().encode('utf-8'),
        'tools/in_force_on.py': (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes(),
    }
    for name in BUILD_FILES:
        files[f'tools/build/{name}'] = (HERE / name).read_bytes()
    for name in ('README.md', 'REPRODUCE.md', 'SOURCES.md', 'LICENSE'):
        files[f'tools/build/repo/{name}'] = (REPO_FILES / name).read_bytes()
    return publish_gate(files)
