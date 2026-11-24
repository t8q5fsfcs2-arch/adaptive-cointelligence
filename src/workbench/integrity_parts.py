"""Exact clause-part coverage and conservative aggregation; not semantic proof.

Sentence/semicolon boundaries create review units, not inferred new requirements.
Source units remain intact. Recognized standalone headings supply context; all
other units require review. Lists and qualifiers keep the complete original clause.
"""
import re
import hashlib
import json

VERSION='fixed-material-conditions-v3'
PROJECTION_VERSION='material-review-projection-v1'
# Deliberately narrow: unknown labels and action-bearing lines remain reviewable.
SECTION_LABELS=frozenset({'operating conditions:', 'project rules:'})

def review_projection(units):
    """Non-destructive source-role projection, never a rewrite of frozen meaning."""
    from copy import deepcopy
    material={};headings={}
    for pid,unit in units.items():
        text=unit['full_clause'];a=unit['start'];b=unit['end']
        line_start=text.rfind('\n',0,a)+1;line_end=text.find('\n',b)
        if line_end<0:line_end=len(text)
        standalone=not text[line_start:a].strip() and not text[b:line_end].strip()
        if standalone and ' '.join(unit['quote'].lower().split()) in SECTION_LABELS:
            headings[pid]=dict(deepcopy(unit),material=False,role='section-heading',evidence_target=False,
                classification=PROJECTION_VERSION,
                classification_reason='Recognized standalone section label; retained with its full source and governing links as context, not a claim of behavior.')
        else:material[pid]=deepcopy(unit)
    return material,headings

def label(ref):return ref['id']+':v'+str(ref['revision'])

def quote_choices(passage,limit=600):
    """Deterministic contiguous source spans; no paraphrasing or semantic scoring.

    Keep sentence/line boundaries where possible. The complete passage remains
    available as context. Ambiguous repeated selections are not offered as unique
    locators; inability to locate evidence cannot license positive support.
    """
    spans=[];start=0
    while start<len(passage):
        end=min(start+limit,len(passage))
        if end<len(passage):
            boundaries=[m.end() for m in re.finditer(r'(?<=[.;])\s+|\n+',passage[start:end])]
            cut=next((x for x in reversed(boundaries) if x>=limit//3),None)
            if cut:end=start+cut
            else:
                space=passage.rfind(' ',start+1,end)
                if space>start:end=space
        value=passage[start:end].strip()
        if value and passage.find(value,passage.find(value)+1)<0:spans.append(value)
        start=end
    return list(dict.fromkeys(spans))

def quote_catalog(ctx,contract):
    """Stable IDs for literal selections; the model chooses, code resolves bytes."""
    allowed={cid for packet in contract['packets'] for cid in packet_citations(ctx,packet,contract)}
    result={}
    for cid in sorted(allowed):
        source=ctx['citation_catalog'][cid]['quote']
        for quote in quote_choices(source):
            start=source.index(quote);value=dict(citation_ref=cid,quote=quote,start=start,end=start+len(quote))
            key='Q-'+hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()[:16]
            result[key]=value
    return result

def catalog(clauses):
    result={}
    for cid,source in clauses.items():
        text=source['quote'];start=0;spans=[]
        for match in re.finditer(r'(?<=[.;])\s+|\n+',text):
            spans.append((start,match.start()));start=match.end()
        spans.append((start,len(text)))
        ordinal=0
        for a,b in spans:
            while a<b and text[a].isspace():a+=1
            while b>a and text[b-1].isspace():b-=1
            if a==b:continue
            ordinal+=1;pid=cid+'/P'+str(ordinal)
            result[pid]=dict(clause_ref=cid,quote=text[a:b],start=a,end=b,material=True,full_clause=text,preceding_text=text[:a],
                boundary='Interpret this exact span within the full governing clause, including list qualifiers and scope. Every stated condition inside the span requires support.')
    return result

def packet_citations(ctx,packet,contract):
    records={label(r['ref']):r for r in ctx['records']}
    expression=records[label(contract['packets'][packet]['expression'])]
    source=records[label(expression['body']['source'])]
    allowed={label(expression['ref']),label(source['ref'])}
    # Only the packet's own explicitly selected evidence, already in this exact
    # permission-checked assembly, can support its claims. No other packet's vault.
    for raw in source['body'].get('source_refs',[]):
        r=records.get(label(raw))
        if r and r['kind'] in {'source','evidence','contribution'}:allowed.add(label(raw))
    return sorted(k for k,v in ctx['citation_catalog'].items() if label(v) in allowed)

def aggregate(parts):
    states=[p['status'] for p in parts]
    if not states:raise ValueError('Every clause needs its material parts assessed.')
    if 'contradicted' in states:return 'contradicted'
    if all(s=='supported' for s in states):return 'supported'
    if all(s=='absent' for s in states):return 'absent'
    return 'uncertain'

def parent(parts,part_catalog):
    status=aggregate(parts);missing=[p for p in parts if p['status']!='supported']
    if missing:
        explanation='Not fully supported. '+ ' '.join(part_catalog[p['part_ref']]['quote'][:110]+' — '+p['remaining_gap'] for p in missing)
    else:explanation='Every material part has cited packet evidence. Semantic support remains provisional; no operational verification or approval is implied.'
    return dict(status=status,evidence_refs=list(dict.fromkeys(k for p in parts for k in p['evidence_refs']))[:6],
        reasoning=explanation[:600],material=bool(missing),parts=parts)

def validate_finding(finding,ctx,contract):
    expected={k:v for k,v in contract['material_parts'].items() if v['clause_ref']==finding['obligation_ref']}
    parts=finding['parts'];ids=[p['part_ref'] for p in parts]
    if len(ids)!=len(expected) or set(ids)!=set(expected):raise ValueError('Assess every material part exactly once; no missing, extra or waived parts.')
    allowed=set(packet_citations(ctx,finding['packet_ref'],contract))
    for part in parts:
        from .integrity_interpretation import validate as validate_interpretation
        validate_interpretation(part)
        from .integrity_explanations import explanation
        for field in ('reasoning','claim_interpretation','support_scope'):explanation(part[field],field)
        if part['status']!='supported':explanation(part['remaining_gap'],'remaining gap')
        if ctx.get('condition_inventory'):
            from .integrity_inventory import LEVELS
            if part.get('evidence_level')!=ctx['evidence_level']:raise ValueError('The evidence level is fixed before grading; do not change it.')
            if part['claim_interpretation']!=expected[part['part_ref']]['meaning'] or part['support_scope']!=LEVELS[ctx['evidence_level']]:
                raise ValueError('The frozen condition meaning and evidence scope cannot be rewritten during grading.')
            check=part['entailment_check'];explanation(check['explanation'],'entailment check')
            if part['status']=='supported' and check['counterexample_possible']:raise ValueError('A material counterexample prevents full support; preserve uncertainty.')
        if ctx.get('condition_inventory'):
            from .integrity_relationship import validate as relationship_check
            relationship_check(part)
        from .integrity_followup import validate as followup_check
        followup_check(part,finding['packet_ref'],ctx)
        refs=part['evidence_refs']
        if len(set(refs))!=len(refs) or not set(refs)<=allowed:raise ValueError('Part support must cite this packet or its selected source evidence, not a requirement or another packet.')
        if part['status'] in {'supported','contradicted'} and not refs:raise ValueError('Every supported or contradicted material part requires its own evidence.')
        if part['status']=='supported' and part['remaining_gap']:raise ValueError('A material part with an unresolved gap cannot be supported.')
        if part['status']!='supported' and not part['remaining_gap'].strip():raise ValueError('Identify the missing evidence, contradiction or uncertainty for each unsupported part.')
        quotes=part['evidence_quotes']
        if set(refs)!={q['citation_ref'] for q in quotes}:raise ValueError('Every evidence reference needs its literal supporting quote; no uncited quote or bare reference.')
        for q in quotes:
            if q['citation_ref'] not in allowed:raise ValueError('Quote this packet evidence, not governing language or another packet.')
            passage=ctx['citation_catalog'][q['citation_ref']]['quote'];quote=q['quote']
            if not quote or quote not in passage:raise ValueError('Evidence quote is not an exact substring of its selected packet passage.')
            if passage.find(quote,passage.find(quote)+1)>=0:raise ValueError('Use enough exact surrounding text to locate the quote unambiguously.')
    derived=aggregate(parts)
    if finding['status']!=derived:raise ValueError('Whole-clause support must agree with every material part; partial support cannot become full support.')
    finding['material']=finding['material'] or derived!='supported'
