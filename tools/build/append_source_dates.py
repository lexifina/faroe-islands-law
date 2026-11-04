"""Append reviewed source-date metadata corrections, preserving every existing law blob and tag."""
import argparse,csv,hashlib,io,json,os,subprocess
from pathlib import Path
IDENTITY='Lexifina <faroe-islands-law@lexifina.com>'
def git(repo,*args,input=None):
    return subprocess.run(['git','-c','gc.auto=0','-C',str(repo),*args],input=input,capture_output=True,check=True).stdout
def append(repo,rows,recorded,expected,checkout=True):
    base=git(repo,'rev-parse','HEAD').decode().strip()
    if base!=expected: raise SystemExit('published base changed; review the new base before appending')
    log=git(repo,'log','--reverse','--format=%H%x1f%B%x1e',base).decode('utf-8')
    original={}
    for item in log.split('\x1e'):
        if not item.strip(): continue
        sha,msg=item.strip('\n').split('\x1f',1)
        t=dict(line.split(': ',1) for line in msg.rstrip().split('\n\n')[-1].splitlines() if ': ' in line)
        if t.get('Kind')=='consolidated':
            if t.get('Source') in original: raise SystemExit('multiple baseline versions; explicit version matching required')
            original[t['Source']]=(sha,t)
    if len(original)!=len(rows): raise SystemExit(f'baseline/source count differs: {len(original)} vs {len(rows)}')
    stream=io.BytesIO(); w=stream.write; mark=0
    import datetime
    timestamp=int(datetime.datetime.fromisoformat(recorded+'T12:00:00+00:00').timestamp())
    when=f'{timestamp} +0000'
    public=[]
    def commit(message,files):
        nonlocal mark
        mark+=1
        w(f'commit refs/heads/main\nmark :{mark}\nauthor {IDENTITY} {when}\ncommitter {IDENTITY} {when}\n'.encode())
        b=message.encode('utf-8'); w(f'data {len(b)}\n'.encode()+b+b'\n')
        w(f'from {base if mark==1 else ":"+str(mark-1)}\n'.encode())
        for path,b in sorted(files.items()): w(f'M 100644 inline {path}\ndata {len(b)}\n'.encode()+b+b'\n')
        w(b'\n')
    for r in sorted(rows,key=lambda r:r['act']):
        sha,t=original[r['source']]
        if t.get('In-force')!=r['text_as_of'] or t.get('Date-source')!='retrieved': raise SystemExit('baseline is not the reviewed retrieval-dated version')
        info={'act':r['act'],'status':r['status'],'first_law':None,'text_as_of':r['text_as_of'],'enacted':r['enacted'],'published':r['published'],'gazette':r['gazette'],'source':r['source'],'corrects':sha,'source_dates':[{'kind':x[0],'number':x[1],'date':x[2]} for x in r['amendments']]}
        if r['status']=='hold':
            info['reason']=r['reason']; public.append(info); continue
        info['in_force_basis']=r['basis']
        if r['status']=='dated': info['in_force']=r['in_force']
        elif r['status']!='text-as-of': raise SystemExit('unknown dating decision')
        public.append(info)
        name=r['act']+'/date-basis.json'
        trailers=['Kind: correction',f'Corrects: {sha}',f'Supersedes: {sha}',f'Correction-set: source-dates-{recorded}',f'Act-path: {r["act"]}',f'Files: {name}','Reason: Withdraw retrieval date as entry into force; retain source dating evidence',f'Text-as-of: {r["text_as_of"]}',f'In-force-basis: {r["basis"]}',f'Source: {r["source"]}']
        if r['status']=='dated': trailers.insert(1,f'In-force: {r["in_force"]}'); trailers.append('Date-source: source commencement')
        else: trailers.append('Date-source: observation only; entry into force unresolved')
        message=f'Date correction: {r["act"]}\n\nThe current text is unchanged. This correction replaces the baseline date claim with source evidence.\n\n'+'\n'.join(trailers)+'\n'
        commit(message,{name:(json.dumps(info,ensure_ascii=False,indent=2)+'\n').encode('utf-8')})
    count={key:sum(r['status']==key for r in rows) for key in ['dated','text-as-of','hold']}
    corpus=json.loads(git(repo,'show',base+':corpus.json'))
    corpus.update({'history':'current-only','record_to':'2026-10-29','build':'partial','source_dating':count,'first_law':None})
    corpus['dates']={'commit':'Append-only metadata corrections are recorded on their correction day; original commits remain unchanged.','in_force':'Source commencement where established; absent for observation-only records.','text_as_of':'Date of the single supplied current text, not commencement.','baseline_trailer':'Text-as-of','other_trailers':['Enacted','Published','In-force-basis'],'time':'12:00 UTC for this correction set'}
    corpus['record_note']='One observed current text per act. Reviewed date metadata corrects the original retrieval-as-In-force claim; it does not reconstruct earlier wording. Date holds are metadata; existing observed versions remain readable through the observation reader.'
    corpus['baseline_trailer']='Text-as-of'; corpus['history_from']='2026-10-29'
    docs={
        'data/source-dates.json':(json.dumps(public,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),
        'corpus.json':(json.dumps(corpus,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),
        'jurisdiction.json':(json.dumps({'jurisdiction':'Faroe Islands','language':'fo','history':'current-only','first_law':None,'text_as_of':'2026-10-29','build':'partial','source_dating':count,'source':'https://logir.fo'},ensure_ascii=False,indent=2)+'\n').encode('utf-8'),
        'tools/in_force_on.py':(Path(__file__).parent / 'repo' / 'tools' / 'in_force_on.py').read_bytes(),
        'tools/build/source_dates.py':Path(__file__).with_name('source_dates.py').read_bytes(),
        'tools/build/append_source_dates.py':Path(__file__).read_bytes(),
    }
    builder=git(repo,'show',base+':tools/build/build.py').decode('utf-8')
    old="    tr = ['Kind: consolidated', f'In-force: {day}', f'Consolidated: {day}', 'Date-source: retrieved']"
    replacement="""    from source_dates import resolve_act
    decision = resolve_act(a, sys.modules[__name__])
    if decision['status'] == 'hold':
        raise ValueError(a['dir'] + ': source dating held: ' + decision['reason'])
    tr = ['Kind: consolidated', f'Text-as-of: {day}',
          'In-force-basis: ' + decision['basis'],
          'Date-source: ' + ('source commencement' if decision['status'] == 'dated' else 'observation only')]
    if decision['status'] == 'dated':
        tr.append('In-force: ' + decision['in_force'])"""
    if builder.count(old)!=1: raise SystemExit('builder date insertion point differs from the reviewed baseline')
    builder=builder.replace(old,replacement)
    builder=builder.replace('Every principal act in force that the site lists', 'Each eligible principal act in force that the site lists')
    builder=builder.replace("    prepare(args.repo)", "    if args.repo.exists() and (args.repo / '.git').exists():\n        raise SystemExit('Existing history must use append_source_dates.py; rebuilding an existing repository is refused')\n    prepare(args.repo)")
    docs['tools/build/build.py']=builder.encode('utf-8')
    legacy_docs=git(repo,'show',base+':tools/build/docs.py').decode('utf-8')
    insertion="           today: str) -> dict[str, bytes]:\n"
    if legacy_docs.count(insertion)!=1: raise SystemExit('legacy renderer differs from baseline')
    legacy_docs=legacy_docs.replace(insertion,insertion+"    raise RuntimeError('Legacy full-rebuild documentation is superseded; use reviewed append_source_dates.py')\n")
    docs['tools/build/docs.py']=legacy_docs.encode('utf-8')
    checker=git(repo,'show',base+':tools/build/check_repo.py').decode('utf-8')
    checker=checker.replace('def main() -> None:\n',"def main() -> None:\n    global CACHE\n    if '--cache' in sys.argv:\n        CACHE = Path(sys.argv[sys.argv.index('--cache') + 1])\n")
    checker=checker.replace("    import build  # only for the folder", "    import build\n    build.CACHE = CACHE\n    build.PAGES = CACHE / 'acts'\n    # only for the folder")
    checker=checker.replace('    # commits\n',"    blobs.p.stdin.close()\n    blobs.p.wait()\n\n    # commits\n")
    checker=checker.replace("        d = t.get('In-force')", "        if t.get('Kind') == 'correction':\n            if not all(t.get(k) for k in ('Corrects', 'Supersedes', 'Reason', 'Act-path', 'Files', 'Text-as-of', 'In-force-basis')):\n                bad.append(sha[:7])\n            if t.get('In-force') and t['In-force'] > today:\n                future.append(sha[:7])\n            continue\n        d = t.get('In-force')")
    start=checker.index('    # the on-date tool'); end=checker.index('    head = git(repo',start)
    tool_check="""    # Source-reviewed query boundaries and text equality to the preserved git files.
    tool = repo / 'tools' / 'in_force_on.py'
    samples = [('logtingslog/1966/68', '2026-10-29', True),
               ('kunngerd/1958/44', '2026-10-28', False),
               ('kunngerd/1958/44', '2026-10-29', True),
               ('kunngerd/1958/44', '2026-10-30', False),
               ('logtingslog/1964/28', '2026-10-29', False),
               ('kunngerd/2019/76', '2026-10-29', False),
               ('kunngerd/1978/52', '2026-10-29', False)]
    ok = 0
    for law, query_day, expected in samples:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(tool), query_day, law, 'title'], cwd=repo,
                                capture_output=True, text=True, encoding='utf-8')
        good = (result.returncode == 0) == expected
        if expected:
            good = good and result.stdout == git(repo, 'show', f'main:{law}/title.md')
        else:
            good = good and 'no version' in result.stderr
        ok += good
        print(f"tool {law} {query_day}: {'ok' if good else 'WRONG'}")
"""
    checker=checker[:start]+tool_check+checker[end:]
    docs['tools/build/check_repo.py']=checker.encode('utf-8')
    oldreadme=git(repo,'show',base+':README.md').decode('utf-8')
    license_part=oldreadme.split('## Licence',1)[-1] if '## Licence' in oldreadme else 'See LICENSE and SOURCES.md.'
    license_part=license_part.replace('**This repository is private.**','').replace('This repository is private.','')
    readme=f'''# The laws of the Faroe Islands

This record preserves 1,329 official current-text acts listed by Lógasavnið (logir.fo) as in force on 29 October 2026: 444 Løgtingslógir, 882 Kunngerðir and 3 Løgtingslógarkunngerðir. The texts are Faroese and, where the source uses it, Danish. Each act has one observed current text, divided into provision and textual-annex files in the reading order in `index.txt`. Earlier wording is not reconstructed.

The source-date correction set preserves every existing law-text file and original commit. It corrects the date claim through labelled append-only metadata records linked by `Corrects` and `Supersedes`.

| Current-text date status | Acts | Meaning |
| --- | ---: | --- |
| Source-dated | {count['dated']} | `In-force` is established from the act's commencement clause or the latest source-named amendment. |
| Observation only | {count['text-as-of']} | `Text-as-of: 2026-10-29`; entry into force of the full current text is unresolved. No `In-force` date is assigned. |
| Held | {count['hold']} | Date ambiguity or source images require further examination. Observed text remains accessible; no verified commencement is claimed. |

`data/source-dates.json` retains source enactment, gazette publication and named amendment dates separately. An observation date is never an entry-into-force date. Source-dated current wording does not establish earlier wording; the record contains only the supplied current text. The source-date records correct the legal commencement claims; the observation reader preserves access to every original observed version. The unchanged historical commits remain visible in git.

Use `python tools/in_force_on.py YYYY-MM-DD ACT-PATH [UNIT]` to read a supported record. The observation reader preserves the published version-selection behavior. Date holds remain visible in metadata and do not remove existing observations; output does not certify legal effect. Consult the source-date records separately for commencement evidence.

There are {sum(bool(r['images']) for r in rows)} image-bearing source acts with {sum(len(r['images']) for r in rows)} image references in the observed pages. Those acts are held; this text record does not claim they are complete. The other unresolved date cases are identified in `data/source-dates.json`. This is a partial record, and current coverage beyond the source listing dated 29 October 2026 has not been established.

The statutory text comes from Lógasavnið and is unchanged. Source dates and quotations are retained as supplied. Metadata and tools were prepared with AI assistance and reviewed against official source pages. Lógasavnið states that the text published in Kunngerðablaðið is authoritative.

## Licence
{license_part.strip()}
'''
    docs['README.md']=readme.encode('utf-8')
    docs['REPRODUCE.md']=b'# Source record\n\nOne observed current text per act, as supplied by Logasavnid on 29 October 2026. Original law blobs and tags are preserved. Source-date metadata is appended only after review of its source evidence. See data/source-dates.json for the dated, observation-only and held records.\n'
    docs['tools/build/repo/README.md']=docs['README.md']
    docs['tools/build/repo/REPRODUCE.md']=docs['REPRODUCE.md']
    # Ship exactly the country-owned canonical tools, not transient job copies.
    canonical = Path(__file__).resolve().parent
    for name in ('build.py', 'check_repo.py', 'docs.py', 'source_dates.py', 'append_source_dates.py'):
        docs['tools/build/' + name] = (canonical / name).read_bytes()
    docs['tools/in_force_on.py'] = (canonical / 'repo' / 'tools' / 'in_force_on.py').read_bytes()
    metadata_trailers = [
        'Kind: correction',
        f'Corrects: {base}',
        f'Supersedes: {base}',
        'Correction-scope: metadata',
        'Act-path: .',
        'Files: ' + ', '.join(sorted(docs)),
        'Reason: Correct retrieval-date claims in published documentation, metadata and date-query tools',
        'Text-as-of: 2026-10-29',
        'In-force-basis: Metadata correction only; per-act source commencement evidence is in data/source-dates.json; no new legal commencement date is assigned',
    ]
    commit('Metadata correction: source dates and current-text observations\n\nDescribe confirmed source dates, observations and held records.\n\n' + '\n'.join(metadata_trailers) + '\n', docs)
    w(b'done\n'); git(repo,'fast-import','--quiet','--done',input=stream.getvalue())
    if checkout: git(repo,'reset','--hard','main')
    return git(repo,'rev-parse','HEAD').decode().strip(),count
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--review',type=Path,required=True); ap.add_argument('--expected-base',required=True); ap.add_argument('--recorded',required=True); ap.add_argument('--no-checkout',action='store_true'); args=ap.parse_args()
    data=args.manifest.read_bytes(); review=json.loads(args.review.read_text('utf-8'))
    if review.get('ok') is not True or review.get('manifest_sha256')!=hashlib.sha256(data).hexdigest(): raise SystemExit('independent source review is missing or does not match this manifest')
    for role in ['AUTHOR','COMMITTER']:
        os.environ['GIT_'+role+'_NAME']='Lexifina'; os.environ['GIT_'+role+'_EMAIL']='faroe-islands-law@lexifina.com'
    rows=json.loads(data)
    head,count=append(args.repo,rows,args.recorded,args.expected_base,not args.no_checkout)
    print(json.dumps({'head':head,'counts':count}),flush=True)
if __name__=='__main__': main()
