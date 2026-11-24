"""Requirement evidence level (D004): a read-only projection over shared records.

Deterministic and explainable. It never calls a model, never writes, never
approves or blocks anything, and stays separate from the human-recorded
confidence rating kept by requirement assessments.
"""
from datetime import datetime, timezone

from .bridge import OPEN

VERSION = 3  # D014 rev 2: independent origins that bear on the requirement count toward coverage
HIGH_MIN_CURRENT = 2      # contributions on the current version
HIGH_MIN_TEAMS = 2        # distinct teams among those contributions
HIGH_MAX_AGE_DAYS = 90    # newest evidence no older than this for High
HIGH_MIN_ORIGINS = 2      # independent cited sources among current contributions
STALE_AGE_DAYS = 180      # newest evidence older than this caps at Low
CONTRADICTION_KINDS = {'challenge', 'conflict'}
GAP_KINDS = {'gap', 'question'}
DEPENDENCY_KINDS = {'dependency'}


def _when(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _refs(values, requirement_id):
    return [r for r in values or [] if isinstance(r, dict) and r.get('id') == requirement_id]


def _issue_targets(body, requirement_id):
    target = body.get('target') or {}
    return target.get('id') == requirement_id or bool(_refs(body.get('requirement_refs'), requirement_id))


def _origin(ref):
    """One underlying source, however many times it was released or cited."""
    identity = ref.get('id', '') if isinstance(ref, dict) else ''
    return identity[len('RELEASE-'):] if identity.startswith('RELEASE-') else identity


def origins_of(contribution, requirement_id=None, blocks=None):
    """Sources that bear on one requirement (D014 rev 2).

    A handoff output such as a developer brief restates decided work and adds no origin.
    Where a contribution shares building blocks, only sources cited by blocks linked to
    this requirement count. Otherwise its own cited sources count.
    """
    body = contribution['body']
    if body.get('developer_brief'):
        return set()
    shared = [(blocks or {}).get(r.get('id')) for r in body.get('knowledge_cards') or [] if isinstance(r, dict)]
    shared = [b for b in shared if b]
    if shared and requirement_id:
        refs = [e.get('ref') for b in shared for e in b['body'].get('evidence') or []
                if any((l.get('ref') or {}).get('id') == requirement_id for l in b['body'].get('relations') or [])]
    else:
        refs = body.get('source_refs') or []
    return {o for o in (_origin(r) for r in refs) if o}


def evidence_level(requirement_id, current_revision, records, now=None):
    """Return the evidence level and its full basis for one requirement."""
    now = now or datetime.now(timezone.utc)
    contributions = [r for r in records if r['kind'] == 'contribution' and _refs(r['body'].get('requirement_refs'), requirement_id)]
    issues = [r for r in records if r['kind'] == 'bridge-issue' and _issue_targets(r['body'], requirement_id)]
    on_current = [c for c in contributions if current_revision is not None and
                  any(ref.get('revision') == current_revision for ref in _refs(c['body'].get('requirement_refs'), requirement_id))]
    teams = sorted({c['body'].get('domain') for c in contributions if c['body'].get('domain')})
    current_teams = sorted({c['body'].get('domain') for c in on_current if c['body'].get('domain')})
    dates = [d for d in (_when(c['body'].get('published_at')) for c in contributions) if d]
    dates += [d for d in (_when(i['body'].get('updated_at') or i['body'].get('created_at')) for i in issues) if d]
    newest = max(dates) if dates else None
    age_days = max(0, (now - newest).days) if newest else None
    open_issues = [i for i in issues if i['body'].get('status') in OPEN]
    resolved = [i for i in issues if i['body'].get('status') not in OPEN]
    contradictions = [i for i in open_issues if i['body'].get('kind') in CONTRADICTION_KINDS]
    gaps = [i for i in open_issues if i['body'].get('kind') in GAP_KINDS]
    dependencies = [i for i in open_issues if i['body'].get('kind') in DEPENDENCY_KINDS]
    blocks = {r['ref'].id: r for r in records if r['kind'] == 'knowledge-card'}
    origins = sorted(set().union(*[origins_of(c, requirement_id, blocks) for c in on_current])) if on_current else []

    reasons = []
    short = []
    if not contributions:
        level = 'empty'
        reasons.append('No shared work references this requirement yet.')
    else:
        low = []
        if contradictions:
            low.append(f'{len(contradictions)} open contradiction{"s" if len(contradictions) != 1 else ""}')
        if not on_current:
            low.append('no shared work references the current version')
        if age_days is not None and age_days > STALE_AGE_DAYS:
            low.append(f'newest evidence is {age_days} days old')
        if on_current and not origins:
            low.append('the shared work on the current version cites no source')
        if low:
            level = 'low'
            reasons.append('Low because ' + '; '.join(low) + '.')
        elif (len(on_current) >= HIGH_MIN_CURRENT and len(current_teams) >= HIGH_MIN_TEAMS and
              len(origins) >= HIGH_MIN_ORIGINS and
              age_days is not None and age_days <= HIGH_MAX_AGE_DAYS and not gaps):
            level = 'high'
            reasons.append(f'High: {len(on_current)} contributions from {len(current_teams)} teams on the current version, '
                           f'{len(origins)} independent sources, recent evidence and no open contradictions or gaps.')
        else:
            level = 'moderate'
            if len(on_current) < HIGH_MIN_CURRENT:
                short.append(f'{HIGH_MIN_CURRENT} contributions on the current version')
            if len(current_teams) < HIGH_MIN_TEAMS:
                short.append(f'work from {HIGH_MIN_TEAMS} teams on the current version')
            if len(origins) < HIGH_MIN_ORIGINS:
                short.append(f'{HIGH_MIN_ORIGINS} independent sources cited')
            if gaps:
                short.append('open gaps resolved')
            if age_days is not None and age_days > HIGH_MAX_AGE_DAYS:
                short.append(f'evidence from the last {HIGH_MAX_AGE_DAYS} days')
            reasons.append('Moderate. High needs ' + ', '.join(short) + '.' if short else 'Moderate.')
    if dependencies:
        reasons.append(f'{len(dependencies)} open dependenc{"ies" if len(dependencies) != 1 else "y"} to watch.')

    # D012: say what would raise the level, from the same facts. Advice only; nothing is blocked.
    if level == 'empty':
        raise_to = dict(to='low', needs=['published work from any team that references this requirement'])
    elif level == 'low':
        needs = []
        if contradictions:
            needs.append('the open contradiction resolved in Decisions & Issues')
        if not on_current:
            needs.append('published work that references the current version')
        if age_days is not None and age_days > STALE_AGE_DAYS:
            needs.append(f'evidence from the last {STALE_AGE_DAYS} days')
        if on_current and not origins:
            needs.append('shared work that cites its source')
        raise_to = dict(to='moderate', needs=needs)
    elif level == 'moderate':
        raise_to = dict(to='high', needs=short)
    else:
        raise_to = None

    def ref(r):
        return dict(id=r['ref'].id, revision=r['ref'].revision)

    return dict(
        version=VERSION, level=level, reasons=reasons,
        requirement=dict(id=requirement_id, revision=current_revision),
        contributions=len(contributions), on_current=len(on_current), teams=teams, current_teams=current_teams,
        independent_origins=len(origins), origins=origins,
        newest_at=newest.isoformat() if newest else None, age_days=age_days,
        open_contradictions=len(contradictions), open_gaps=len(gaps), open_dependencies=len(dependencies),
        resolved_issues=len(resolved),
        raise_to=raise_to,
        basis=dict(contributions=[ref(c) for c in contributions], issues=[ref(i) for i in issues]))


def evidence_levels(records, now=None):
    """Evidence levels for every requirement id that is approved or referenced in shared records."""
    current = {}
    for r in records:
        if r['kind'] == 'requirement':
            current[r['ref'].id] = r['ref'].revision
    referenced = set(current)
    for r in records:
        if r['kind'] == 'contribution':
            referenced.update(x['id'] for x in r['body'].get('requirement_refs') or [] if isinstance(x, dict) and x.get('id'))
        elif r['kind'] == 'bridge-issue':
            target = (r['body'].get('target') or {}).get('id')
            if isinstance(target, str) and target.startswith('REQ'):
                referenced.add(target)
            referenced.update(x['id'] for x in r['body'].get('requirement_refs') or [] if isinstance(x, dict) and x.get('id'))
    # Candidates not yet approved have no shared current version; their latest referenced revision stands in.
    for rid in referenced - set(current):
        revisions = [x.get('revision') for r in records if r['kind'] == 'contribution'
                     for x in _refs(r['body'].get('requirement_refs'), rid) if isinstance(x.get('revision'), int)]
        current[rid] = max(revisions) if revisions else None
    return {rid: evidence_level(rid, current[rid], records, now) for rid in sorted(referenced)}
