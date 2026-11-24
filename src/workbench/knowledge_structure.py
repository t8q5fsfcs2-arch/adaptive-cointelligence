"""D014 Rules 5 to 7: detect differences, define packet types and check structure.

Deterministic services over the typed relationships table. They report differences by
kind and never decide meaning: a reviewer judges whether a difference is compatible,
unsupported or contradictory, and decision owners settle consequences. Nothing here
writes records, calls a model, approves, blocks or resolves anything.
"""
from __future__ import annotations

from collections import defaultdict

from .bridge import OPEN as OPEN_STATUSES
from .core import Ref
from .knowledge_components import config, area_of, eligibility

CONTRADICTION_KINDS = {'challenge', 'conflict'}
NEXT_STEP = 'A reviewer judges whether this is compatible, unsupported or contradictory. Material consequences go to the decision owner.'


def _group(record: dict) -> str:
    body = record['body']
    return body.get('domain_label') or body.get('domain') or body.get('domain_key') or record['scope']


def _title(record: dict | None, fallback: str) -> str:
    if not record:
        return fallback
    body = record['body']
    return body.get('title') or (body.get('payload') or {}).get('title') or fallback


def _norm(text: str) -> str:
    return ' '.join((text or '').lower().split())


def differences(store, records: list[dict], scopes) -> list[dict]:
    """Differences between groups that link to the same identifier, reported by kind."""
    by_id = {r['ref'].id: r for r in records}
    rels = [l for l in store.relationships(scopes) if by_id.get(l['from_id'], {}).get('kind') == 'knowledge-card']
    targets: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for link in rels:
        targets[link['to_id']][_group(by_id[link['from_id']])].append(link)
    found = []
    for target_id, groups in sorted(targets.items()):
        if len(groups) < 2:
            continue
        try:
            latest = store.latest(target_id, scopes)['ref'].revision
        except PermissionError:
            continue
        signature = {g: dict(relations={l['relation'] for l in ls}, uses={l['use'] for l in ls},
                             conditions={_norm(l['conditions']) for l in ls},
                             revisions={l['to_revision'] for l in ls}) for g, ls in groups.items()}
        kinds = []
        stated = [s['conditions'] - {''} for s in signature.values()]
        if len({frozenset(s) for s in stated}) > 1:
            kinds.append('scope-differs' if all(stated) else 'scope-stated-by-one-group')
        if len({frozenset(s['relations']) for s in signature.values()}) > 1:
            kinds.append('relation-differs')
        if len({frozenset(s['uses']) for s in signature.values()}) > 1:
            kinds.append('use-differs')
        revisions = {r for s in signature.values() for r in s['revisions'] if r is not None}
        if len(revisions) > 1 or any(r < latest for r in revisions):
            kinds.append('revision-skew')
        if not kinds:
            continue
        message = {
            'scope-differs': 'Scope differs between groups: check applicability.',
            'scope-stated-by-one-group': 'Only one group states the scope: check applicability.',
            'relation-differs': 'Groups link to it with different relations.',
            'use-differs': 'Groups use it differently (for example as evidence and as direction).',
            'revision-skew': 'Groups rely on different or superseded versions.',
        }
        found.append(dict(
            target=dict(id=target_id, revision=latest), title=_title(by_id.get(target_id), target_id),
            kinds=kinds, messages=[message[k] for k in kinds], next=NEXT_STEP,
            groups=[dict(group=g, links=[dict(source=dict(id=l['from_id'], revision=l['from_revision']),
                                             source_title=_title(by_id.get(l['from_id']), l['from_id']),
                                             relation=l['relation'], conditions=l['conditions'], use=l['use'],
                                             revision=l['to_revision']) for l in ls])
                    for g, ls in sorted(groups.items())]))
    return found


def packet_contents(store, type_key: str, anchor: Ref, audience_scopes, latest_only=True) -> dict:
    """D014 Rule 5: follow the type's relations from the anchor to its depth, for its audience."""
    spec = config()['packet_types'][type_key]
    audience = set(audience_scopes)
    anchor_record = store.read(anchor, audience)
    if anchor_record['kind'] not in spec['anchor_kinds']:
        raise ValueError(f"A {spec['label']} packet starts from: " + ', '.join(spec['anchor_kinds']))
    rels = [l for l in store.relationships(audience, latest_only=latest_only) if l['relation'] in spec['relations']]
    chosen, frontier = {anchor.id: anchor}, [anchor.id]
    for _ in range(spec['depth']):
        nxt = []
        for node in frontier:
            for l in rels:
                if l['to_id'] == node and l['from_id'] not in chosen:
                    chosen[l['from_id']] = Ref(l['from_id'], l['from_revision']); nxt.append(l['from_id'])
                elif l['from_id'] == node and l['to_id'] not in chosen and l['to_revision']:
                    chosen[l['to_id']] = Ref(l['to_id'], l['to_revision']); nxt.append(l['to_id'])
        frontier = nxt
    refs = []
    for ref in chosen.values():
        try:
            current = store.latest(ref.id, audience)['ref']
        except PermissionError:
            continue
        refs.append(current if spec['revision_policy'] == 'latest' else ref)
    return dict(type=type_key, label=spec['label'], anchor=dict(id=anchor.id, revision=anchor.revision),
                revision_policy=spec['revision_policy'], refs=[dict(id=r.id, revision=r.revision) for r in sorted(refs)])


def structure_check(store, records: list[dict], packets: list[dict], drawers: list[dict], scopes) -> dict:
    """D014 Rule 7 step 2: what a reviewer should look at. Reports; never decides."""
    by_id = {r['ref'].id: r for r in records}
    rels = store.relationships(scopes)
    stale = [dict(packet=dict(id=p['id'], revision=p['revision']), purpose=p['purpose'], changed=p['changed_refs'])
             for p in packets if p.get('changed_refs')]
    reach = []
    for issue in (r for r in records if r['kind'] == 'bridge-issue'):
        b = issue['body']
        if b.get('kind') not in CONTRADICTION_KINDS or b.get('status') not in OPEN_STATUSES:
            continue
        # What is challenged is the target and the named requirements, not everything in the evidence trail.
        ids = {x.get('id') for x in [b.get('target') or {}, *(b.get('requirement_refs') or [])] if isinstance(x, dict)}
        ids.discard(None)
        dependents, frontier = {}, set(ids)
        for depth in (1, 2):
            nxt = set()
            for l in rels:
                if l['to_id'] in frontier and l['from_id'] not in dependents and l['from_id'] not in ids:
                    dependents[l['from_id']] = depth; nxt.add(l['from_id'])
            frontier = nxt
        newest = {}
        for p in packets:
            if any(ref['id'] in ids for ref in p['refs']) and p['revision'] >= newest.get(p['id'], p)['revision']:
                newest[p['id']] = p
        held = [dict(id=p['id'], revision=p['revision'], purpose=p['purpose'][:120]) for p in newest.values()]
        if dependents or held:
            reach.append(dict(issue=dict(id=issue['ref'].id, revision=issue['ref'].revision), title=b.get('title', ''),
                              challenged=sorted(ids),
                              dependents=[dict(id=i, depth=d, title=_title(by_id.get(i), i)) for i, d in sorted(dependents.items(), key=lambda kv: (kv[1], kv[0]))],
                              packets=held))
    gaps = []
    for req in (r for r in records if r['kind'] == 'requirement'):
        area = area_of(req, drawers)
        linked = [(by_id[l['from_id']], l['relation']) for l in rels
                  if l['to_id'] == req['ref'].id and by_id.get(l['from_id'], {}).get('kind') == 'knowledge-card']
        if not linked or area is None:
            continue
        checks = [eligibility(block, relation, area) for block, relation in linked]
        if not any(c['eligible'] for c in checks):
            missing = sorted({m for c in checks for m in c['missing']})
            gaps.append(dict(requirement=dict(id=req['ref'].id, revision=req['ref'].revision), title=_title(req, req['ref'].id),
                             area=area, linked=len(linked), missing=missing,
                             note=checks[0]['coaching'] if len(checks) == 1 else 'Linked blocks do not yet carry what this category needs.'))
    return dict(stale_pins=stale, challenge_reach=reach, category_gaps=gaps,
                differences=differences(store, records, scopes),
                boundary='Computed from recorded links and versions. It reports; it does not decide meaning, approve or block.')
