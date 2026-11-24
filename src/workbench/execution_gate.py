"""D014 Rule 7 step 6: check current access and current basis immediately before acting.

Deterministic. Blockers stop the action: the actor may no longer act, or a pinned version
is no longer readable or current. Open challenges on the basis are notices the actor must
acknowledge; low confidence alone never blocks.
"""
from __future__ import annotations

from dataclasses import asdict

from .bridge import OPEN
from .core import Ref, StaleBasis

CHALLENGE_KINDS = {'challenge', 'conflict'}


def check(w, refs: list[Ref], permitted: bool, action: str) -> dict:
    blockers, notices = [], []
    if not permitted:
        blockers.append(f'You no longer have permission to {action}.')
    ids = set()
    for ref in refs:
        try:
            w.store.read(ref, w.scopes)
            current = w.store.latest(ref.id, w.scopes)['ref']
        except PermissionError:
            blockers.append(f'{ref.label()} is no longer available to you.')
            continue
        if current != ref:
            blockers.append(f'{ref.label()} has a newer version ({current.label()}).')
        ids.add(ref.id)
    for issue in w.latest_records('bridge-issue'):
        b = issue['body']
        if b.get('kind') not in CHALLENGE_KINDS or b.get('status') not in OPEN:
            continue
        touched = {x.get('id') for x in [b.get('target') or {}, *(b.get('requirement_refs') or [])] if isinstance(x, dict)}
        if touched & ids:
            notices.append(dict(issue=asdict(issue['ref']), title=b.get('title', ''), kind=b.get('kind')))
    return dict(action=action, blockers=blockers, notices=notices, checked=[asdict(r) for r in refs])


def enforce(gate: dict, acknowledged: bool) -> None:
    for message in gate['blockers']:
        if 'permission' in message or 'no longer available' in message:
            raise PermissionError(message)
        raise StaleBasis(message + ' Prepare a fresh preview before continuing.')
    if gate['notices'] and not acknowledged:
        raise ValueError('Open challenges touch this basis: ' + '; '.join(n['title'] or n['issue']['id'] for n in gate['notices'])
                         + '. Acknowledge them to continue.')
