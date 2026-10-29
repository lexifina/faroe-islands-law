"""Check the Faroe Islands law repository against the cached logir.fo pages.

    python -X utf8 scripts/faroe-islands-law/check_repo.py ~/Documents/faroe-islands-law-build [--today D] [--no-record]

1. Letters and digits: for every act in the listing, the files read back from git (main, in index.txt order) give
   exactly the letters and digits (str.isalnum, NFC) of the act's page, in order. The page side does not use
   build.py: it takes the text area (from `<div id="div_content"` to `<aside`), drops the chapter list the site adds
   on top (`<ul class=ChapterList>`), <style>, <script> and comments, strips every tag with a regular expression and
   unescapes entities. On the git side only the `[image]` placeholders are left out; note markers `[^N]` keep the
   site's note numbers, so they compare too.
2. Trailers: every commit's final paragraph is all trailers to `git log --format=%(trailers:only)`, and every law
   commit has In-force and Kind.
3. History: no merges; In-force dates never go backwards and are not after the build day; no CR in any message.
4. Tool: tools/in_force_on.py prints the file for sample units and the whole act in index.txt order, and refuses a
   date before the record.
Writes scripts/faroe-islands-law/verification.json (read by docs.py into README.md and REPRODUCE.md) unless
--no-record.
"""
import json
import re
import subprocess
import sys
import unicodedata
from html import unescape
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'


def page_chars(html: str) -> str:
    i = html.find('<div id="div_content"')
    j = html.find('<aside', i)
    h = html[i:j if j > 0 else len(html)]
    h = re.sub(r'(?is)<ul\b[^>]*class="?ChapterList\b[^>]*>.*?</ul\s*>', ' ', h)
    h = re.sub(r'(?is)<(script|style)\b.*?</\1\s*>', ' ', h)
    h = re.sub(r'(?s)<!--.*?-->', ' ', h)
    h = re.sub(r'(?s)<[^>]*>', ' ', h)
    t = unicodedata.normalize('NFC', unescape(h))
    return ''.join(c for c in t if c.isalnum())


def git_chars(text: str) -> str:
    t = unicodedata.normalize('NFC', text.replace('[image]', ' '))
    return ''.join(c for c in t if c.isalnum())


def git(repo: Path, *a: str) -> str:
    return subprocess.run(['git', '-C', str(repo), '-c', 'core.quotepath=false', *a], capture_output=True,
                          text=True, encoding='utf-8', check=True).stdout


class Blobs:
    def __init__(self, repo: Path):
        self.p = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)

    def get(self, spec: str) -> str | None:
        self.p.stdin.write(spec.encode('utf-8') + b'\n')
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if head[-1] == b'missing':
            return None
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return data.decode('utf-8')


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    repo = Path(args[0]).resolve()
    record = '--no-record' not in sys.argv
    today = sys.argv[sys.argv.index('--today') + 1] if '--today' in sys.argv else None
    rows = json.loads((CACHE / 'list.json').read_text('utf-8'))['rows']
    sys.path.insert(0, str(HERE))
    import build  # only for the folder of each act (load_acts) and the page file name
    acts = build.load_acts()
    if today is None:
        today = build.retrieved_day()
    assert len(acts) == len(rows)
    blobs = Blobs(repo)
    mism, chars, checked = [], 0, 0
    for a in acts:
        idx = blobs.get(f"main:{a['dir']}/index.txt")
        if idx is None:
            mism.append([a['dir'], 'not in git'])
            continue
        mine = ''.join(git_chars(blobs.get(f"main:{a['dir']}/{fn}") or '') for fn in idx.split())
        theirs = page_chars(a['page'].read_text('utf-8'))
        checked += 1
        chars += len(theirs)
        if mine != theirs:
            k = next((i for i, (x, y) in enumerate(zip(mine, theirs)) if x != y), min(len(mine), len(theirs)))
            mism.append([a['dir'], f'char {k}: git {mine[max(0, k - 20):k + 30]!r} vs page '
                                   f'{theirs[max(0, k - 20):k + 30]!r} ({len(mine)} vs {len(theirs)})'])
    tracked = {'/'.join(p.split('/')[:3]) for p in git(repo, 'ls-tree', '-r', '--name-only', 'main').split('\n')
               if p.endswith('/index.txt')}
    extra = sorted(tracked - {a['dir'] for a in acts})
    for e in extra:
        mism.append([e, 'in git but not in the listing'])
    print(f'letters and digits: {checked} acts, {chars} characters, {len(mism)} mismatches')
    for m in mism[:20]:
        print('  ', *m)

    # commits
    raw = subprocess.run(['git', '-C', str(repo), 'log', '--first-parent', '--reverse',
                          '--format=%H%x1f%B%x1f%(trailers:only,unfold)%x1e', 'main'], capture_output=True).stdout
    commits = [c.strip(b'\n').split(b'\x1f') for c in raw.split(b'\x1e') if c.strip()]
    bad, no_inforce, backwards, future, crs, last = [], [], [], [], 0, ''
    for sha, body, trailers in commits:
        sha = sha.decode()
        if b'\r' in body:
            crs += 1
        text = body.decode('utf-8').rstrip('\n')
        para = text.split('\n\n')[-1].split('\n')
        got = [l for l in trailers.decode('utf-8').split('\n') if l.strip()]
        if para != got:
            bad.append(sha[:7])
        t = dict(l.split(': ', 1) for l in got if ': ' in l)
        if t.get('Kind') == 'documentation':
            continue
        d = t.get('In-force')
        if not d or not t.get('Kind'):
            no_inforce.append(sha[:7])
            continue
        if d < last:
            backwards.append(sha[:7])
        last = max(last, d)
        if d > today:
            future.append(sha[:7])
    merges = int(git(repo, 'rev-list', '--merges', '--count', 'main').strip())
    print(f'commits: {len(commits)}, trailers not parsed {len(bad)}, no In-force {len(no_inforce)}, backwards '
          f'{len(backwards)}, after {today} {len(future)}, merges {merges}, messages with CR {crs}')

    # the on-date tool
    tool = repo / 'tools' / 'in_force_on.py'
    samples = [('logtingslog/2015/30', 'paragraf-9'), ('logtingslogarkunngerd/2024/8', 'paragraf-3'),
               ('logtingslog/2013/49', 'paragraf-2'), ('logtingslog/2013/49', None), ('kunngerd/2017/47', None)]
    ok = 0
    for law, unit in samples:
        r = subprocess.run([sys.executable, '-X', 'utf8', str(tool), today, law] + ([unit] if unit else []),
                           cwd=repo, capture_output=True, text=True, encoding='utf-8')
        if unit:
            want = blobs.get(f'main:{law}/{unit}.md')
        else:
            want = ''.join(blobs.get(f'main:{law}/{n}') + '\n' for n in blobs.get(f'main:{law}/index.txt').split())
        good = r.returncode == 0 and r.stdout == want
        early = subprocess.run([sys.executable, '-X', 'utf8', str(tool), '2026-01-01', law] + ([unit] if unit else []),
                               cwd=repo, capture_output=True, text=True, encoding='utf-8')
        good = good and early.returncode != 0 and 'no version' in early.stderr
        ok += good
        print(f"tool {law} {unit or '(whole act)'}: {'ok' if good else 'WRONG'}")
    head = git(repo, 'rev-parse', 'HEAD').strip()
    result = {'acts': checked, 'chars': chars, 'mismatches': len(mism), 'mismatch_list': mism[:50],
              'commits': len(commits), 'bad_trailers': len(bad), 'no_inforce': len(no_inforce),
              'backwards': len(backwards), 'future': len(future), 'merges': merges, 'crs': crs,
              'tool_ok': ok, 'tool_samples': len(samples), 'head': head, 'today': today}
    print(f'head {head}')
    if record:
        (HERE / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n',
                                                encoding='utf-8')
    failed = mism or bad or no_inforce or backwards or future or merges or crs or ok != len(samples)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
