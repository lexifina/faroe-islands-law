"""Conservative source-clause dating. No legal text is generated or edited."""
import re
from datetime import date,timedelta
MONTHS={'januar':1,'januari':1,'februar':2,'februari':2,'mars':3,'marts':3,'apríl':4,'april':4,'mai':5,'maj':5,'juni':6,'juli':7,'august':8,'september':9,'oktober':10,'november':11,'desember':12,'december':12}
DATE=re.compile(r'(\d{1,2})\.?\s+('+ '|'.join(MONTHS) +r')\s+(\d{4})',re.I)
def source_days(text):
    out=[]
    for m in DATE.finditer(text):
        try: out.append(date(int(m[3]),MONTHS[m[2].lower()],int(m[1])).isoformat())
        except ValueError: pass
    return out
def commencement(clause,published):
    text=re.sub(r'^\s*(?:\[\^\d+\]\s*)*(?:§\s*\d+\s*[a-z]?\.|Stk\.\s*\d+\.)\s*','',clause,flags=re.I).lower()
    if re.search(r'(kemur|koma|kom)\s+beinanvegin\s+í\s+gildi',text):
        if published: return published,'explicit immediate commencement on source publication date'
        return None,'immediate commencement without publication date'
    entry=re.search(r'(kemur|koma|kom|fær|fáa|træder|trådte|træde|får)\s+(?:í\s+gildi|i\s+kraft|gildi)\s+',text)
    if not entry:
        return None,'no explicit commencement clause'
    # Split commencement, delegation and retroactivity require human examination.
    if re.search(r'(landsstýris|fastsættes|bestemmer|ásetir|tó |dog |bortset|undtagen|virkning|virknað|stk\.|§)',text):
        return None,'split, delegated or retroactive commencement'
    tail=text[entry.end():].strip()
    dated=DATE.match(re.sub(r'^(?:tann|hin|den)\s+','',tail))
    if dated:
        candidates=source_days(dated[0])
        if len(candidates)==1: return candidates[0],'explicit commencement date immediately after commencement verb'
        return None,'invalid explicit commencement date'
    if re.match(r'(dagin eftir|dagen efter)',tail) and re.search(r'(kunngjør|lýst|bekendtgj)',tail):
        if published: return (date.fromisoformat(published)+timedelta(days=1)).isoformat(),'day after source publication'
        return None,'publication-relative commencement without publication date'
    if re.match(r'(beinanvegin|straks)',tail):
        if published: return published,'immediate commencement on source publication date'
        return None,'immediate commencement without publication date'
    if re.match(r'(kunngerðardagin|kunngerðadegnum|bekendtgørelsesdagen|dagin,?\s+(?:ið|hon)|dagen,?\s+(?:hvor|den))',tail):
        if published: return published,'commencement on source publication date'
    return None,'unresolved commencement wording'
def decide(enacted,published,body_clauses,amendments):
    for row in amendments:
        try: date.fromisoformat(row[2])
        except ValueError:
            return {'status':'hold','reason':'unparsed amendment date: '+row[2],'quotes':[row[4]]}
    refs={tuple(x[:3]) for x in amendments}
    latest=max((x[2] for x in refs),default='')
    if latest:
        rows=[x for x in amendments if x[2]==latest]
        missing=[identity for identity in {tuple(x[:3]) for x in rows} if not any(tuple(x[:3])==identity and x[3] for x in rows)]
        if missing:
            return {'status':'hold','reason':'latest amendment identity has no quoted commencement','latest_amendment_date':latest,'quotes':[x[4] for x in rows]}
        clauses=sorted({x[3] for x in rows if x[3]})
        # A current act's original publication cannot date a later amendment.
        selected=[]; reasons=[]
        for c in clauses:
            d,why=commencement(c,'')
            if d: selected.append(d)
            else: reasons.append(why)
        if selected and len(set(selected))==1 and not reasons and selected[0]>=latest:
            return {'status':'dated','in_force':selected[0],'basis':'Latest source-named amendment: '+ '; '.join(clauses),'latest_amendment_date':latest,'quotes':clauses}
        return {'status':'hold','reason':'; '.join(sorted(set(reasons))) or 'latest amendment has no unambiguous commencement on or after enactment','latest_amendment_date':latest,'quotes':clauses}
    selected=[]; quotes=[]; reasons=[]
    for c in body_clauses:
        d,why=commencement(c,published)
        if d: selected.append(d); quotes.append(c)
        else: reasons.append(why)
    if selected and len(set(selected))==1 and not reasons and selected[0]>=enacted:
        return {'status':'dated','in_force':selected[0],'basis':'Source commencement: '+ '; '.join(quotes),'quotes':quotes}
    if not enacted and not published and not body_clauses:
        return {'status':'text-as-of','basis':'The source gives no date; the observation date is not an entry-into-force date.','quotes':[]}
    return {'status':'hold','reason':'; '.join(sorted(set(reasons))) or 'source dates exist but current-text commencement is not established','quotes':body_clauses}

def resolve_act(a,build):
    """Fail closed over source images, malformed annotations and staged commencement."""
    html=a['page'].read_text('utf-8'); src=build.content(html)
    p=build.Blocks(); p.feed(src); p.close()
    notes={}
    for b in p.blocks:
        if b['note'] is not None: notes.setdefault(b['note'],[]).append(b['text'])
    amendments=[]; unparsed=[]
    for ls in notes.values():
        text=' '.join(ls); refs,clause=build.parse_note(text)
        if not refs and re.match(r'^(?:\[\^\d+\]:\s*)?(?:Broytt|Ændret|Tilføjet|Ophævet|Strikað|Sett inn|Nýtt|Orðað)',text,re.I): unparsed.append(text)
        for kind,nr,day in refs: amendments.append([kind,nr,day,clause,text])
    for b in p.blocks:
        if b['note'] is None and b['cls'] in build.HEADER_CLS:
            refs,clause=build.parse_note(b['text'])
            for kind,nr,day in refs:
                if day>a['enacted'] and not any(x[:3]==[kind,nr,day] for x in amendments): amendments.append([kind,nr,day,clause,b['text']])
    clauses=[b['text'] for b in p.blocks if b['note'] is None and re.search(r'(kemur|koma|kom|fær|fáa|træder|trådte|træde|får)\s+(?:beinanvegin\s+)?(?:í\s+gildi|i\s+kraft|gildi)',b['text'],re.I)]
    pub=build.parse_day(build.side_info(html).get('Útgávudagur',''))
    d=decide(a['enacted'],pub,clauses,amendments)
    if unparsed: d={'status':'hold','reason':'amendment annotation could not be fully parsed'}
    if not amendments and re.search(r'(sum.*broytt|som.*ændret)',a['heading'],re.I): d={'status':'hold','reason':'title says amended but no amendment references were parsed'}
    latest=d.get('latest_amendment_date','')
    body_ambiguous=any(re.search(r'(tó |dog |undant|undtag|landsstýris|fastsættes|bestemmer|ásetir)',c,re.I) or any(day>'2026-10-29' for day in source_days(c)) for c in clauses)
    missed_clause=latest and any(x[2]==latest and not x[3] and re.search(r'(gildi|kraft)',x[4],re.I) for x in amendments)
    if body_ambiguous: d={'status':'hold','reason':'split, delegated or future commencement remains in the source body'}
    elif missed_clause: d={'status':'hold','reason':'source amendment contains commencement wording that was not fully extracted'}
    elif d['status']=='hold' and not unparsed:
        if latest and d['reason'].startswith('latest amendment') and all(not x[3] for x in amendments if x[2]==latest):
            d={**d,'status':'text-as-of','basis':'The source gives no date for this consolidated version; commencement of the full current text is unresolved. Source enactment, publication and amendment dates are retained separately.'}
        elif not amendments and not clauses and d['reason']=='source dates exist but current-text commencement is not established':
            d={**d,'status':'text-as-of','basis':'The source gives no date for this consolidated version. Source enactment and publication dates are retained separately; commencement of the full current text is unresolved.'}
    if d['status']=='dated' and d['in_force']>'2026-10-29': d={'status':'hold','reason':'commencement is after the source observation date'}
    if re.search(r'<img\b',src,re.I): d={'status':'hold','reason':'source images require separate review'}
    return d
