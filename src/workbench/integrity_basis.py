"""Distinguish retained historical analysis from eligibility for current use."""
from copy import deepcopy
from dataclasses import asdict
from .core import Ref, StaleBasis
from .integrity_explanations import explanation

VERSION='explicit-review-basis-v1'
HISTORICAL_LIMIT='Historical analysis of the exact selected versions; ineligible for current approval, reconciliation, ratification or operational reuse.'

def selection(data):
    purpose=data.get('review_purpose','current')
    if purpose not in ('current','historical'):raise ValueError('Choose current or historical review purpose.')
    reason=data.get('historical_reason','')
    if purpose=='historical':
        if data.get('mode')!='advisory':raise ValueError('Historical reviews are advisory; use current evidence for a formal decision.')
        explanation(reason,'reason for retaining historical versions')
        if len(reason)>1000:raise ValueError('Bound the historical review reason to 1,000 characters.')
    elif reason:raise ValueError('A historical reason requires historical review purpose.')
    return dict(version=VERSION,purpose=purpose,reason=reason,
        boundary=HISTORICAL_LIMIT if purpose=='historical' else 'Current selected versions at review time; bounded coverage and evidence level still apply.')

def report(service,ctx):
    superseded=[];unavailable=list(ctx['manifest']['unavailable'])
    for q in ctx['manifest']['included']:
        try:
            service.store.read(Ref(**q),service.w.scopes)
            latest=service.store.latest(q['id'],service.w.scopes)['ref']
            if latest!=Ref(**q):superseded.append(dict(kind='record',selected=q,current=asdict(latest)))
        except PermissionError:unavailable.append(dict(reason='Selected evidence is no longer accessible.'))
    for p in ctx['packets']:
        try:
            service.store.resolve_packet(p['id'],p['revision'],service.w.scopes)
            versions=[m['revision'] for m in service.store.packet_manifests(service.w.scopes) if m['id']==p['id']]
            latest=max(versions)
            if latest!=p['revision']:superseded.append(dict(kind='packet',selected=p,current=dict(id=p['id'],revision=latest)))
        except (PermissionError,ValueError):unavailable.append(dict(reason='Selected packet is no longer accessible.'))
    basis=ctx.get('review_basis',dict(purpose='legacy-unspecified',boundary='Historical record: purpose was not recorded. Reassess before current use.'))
    blockers=service.freshness(dict(body=dict(context=ctx)))
    current=basis['purpose']=='current' and not superseded and not unavailable and not blockers
    return dict(**basis,superseded=superseded,unavailable=unavailable,
        evidence_currency='unavailable' if unavailable else 'historical-selected-versions' if superseded else 'current-selected-versions',
        selected_versions_current=not superseded and not unavailable,current_use_eligible=current,current_use_blockers=blockers,
        coverage='bounded-selection',omitted_dependencies=len(ctx['manifest']['omitted']),
        preflight_model_calls=0)

def require(service,ctx):
    receipt=report(service,ctx)
    if receipt['unavailable']:raise StaleBasis('Selected evidence is unavailable. Resolve access or explicitly narrow the selection before model execution.')
    if receipt['purpose']=='current' and receipt['superseded']:
        names=', '.join(x['selected']['id']+':v'+str(x['selected']['revision'])+' → v'+str(x['current']['revision']) for x in receipt['superseded'])
        raise StaleBasis('Current review contains superseded inputs: '+names+'. Select and publish current versions, or explicitly request an advisory historical review with a reason. No model call was started by this preflight.')
    return receipt

def cache_context(ctx):
    out=deepcopy(ctx)
    if out.get('review_basis',{}).get('purpose')=='historical':
        # Later versions do not change the meaning of these exact historical
        # inputs. Current authority, method, model and selected contents remain
        # in the cache key; access is rechecked separately on every request.
        for p in out['observed_packets']:p.pop('latest',None)
    return out
