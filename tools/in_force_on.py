"""Print a Faroese act, or one unit of it, as this repository has it on a date.

    python tools/in_force_on.py 2026-10-29 logtingslog/2013/49                 # the whole pensions act
    python tools/in_force_on.py 2026-10-29 logtingslog/2013/49 paragraf-1      # its § 1
    python tools/in_force_on.py 2026-10-29 logtingslog/2015/30 paragraf-9      # copyright act, § 9

Reads the `In-force:` and `Consolidated:` trailers (the real dates, not the commit date or your time zone).
The record of every act starts at its text as retrieved from logir.fo; a date before that has no version here.
Standard library only.
"""
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', '-c', 'core.quotepath=false', *args], capture_output=True, text=True,
                          encoding='utf-8', check=True).stdout


def commit_on(day: str, path: str) -> tuple[str | None, str | None]:
    """The last commit on or before `day` that touched `path`, and the earliest date known for it."""
    fmt = '%H%x1f%(trailers:key=In-force,valueonly,separator=)%x1f%(trailers:key=Consolidated,valueonly,separator=)'
    earliest = None
    for line in git('log', '--first-parent', '--no-merges', f'--format={fmt}', 'main', '--', path).splitlines():
        h, inforce, consolidated = (line.split('\x1f') + ['', ''])[:3]
        d = (inforce or consolidated).strip()
        if not d:
            continue
        earliest = d
        if d <= day:
            return h, d
    return None, earliest


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, law = sys.argv[1], sys.argv[2].strip('/')
    unit = sys.argv[3] if len(sys.argv) > 3 else None
    if unit and unit.endswith('.md'):
        unit = unit[:-3]
    path = f'{law}/{unit}.md' if unit else law
    h, earliest = commit_on(day, path)
    if not h:
        if earliest:
            sys.exit(f'{path}: no version on or before {day}; the record starts at {earliest}, the day the current '
                     'text was retrieved from logir.fo (the site keeps no earlier consolidations)')
        sys.exit(f'{path}: not found')
    if unit:
        sys.stdout.write(git('show', f'{h}:{path}'))
        return
    try:
        names = [n for n in git('show', f'{h}:{law}/index.txt').splitlines() if n]
    except subprocess.CalledProcessError:
        names = sorted(n.rsplit('/', 1)[-1] for n in git('ls-tree', '--name-only', h, f'{law}/').split())
    for n in names:
        sys.stdout.write(git('show', f'{h}:{law}/{n}') + '\n')


if __name__ == '__main__':
    main()
