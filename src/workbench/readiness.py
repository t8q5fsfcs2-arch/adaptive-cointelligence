"""Readiness decision (D008): a human call that the case is ready to build.

The board informs the call; this record holds it. The decision belongs to whoever
holds Business direction decision rights (the decider or a delegate). Each call is
a new revision of one record, so earlier calls and their reasons are kept. The basis
the decider saw is computed here from shared records, never taken from the browser.
A later change to that basis opens reconsideration; it never rewrites the call.
"""
from dataclasses import asdict

from .bridge import OPEN
from .core import Ref, StaleBasis
from .decisions import SCOPE, fingerprint, now
from .requirement_evidence import evidence_levels

RECORD = 'PROJECT-READINESS'
KIND = 'readiness-decision'
OUTCOMES = {'ready': 'Ready to build', 'ready-with-conditions': 'Ready with conditions', 'not-yet': 'Not yet'}
CLOSED_CASES = {'approved', 'rejected', 'withdrawn', 'closed'}


class Readiness:
    def __init__(self, w):
        self.w = w
        self.store = w.store

    def current(self):
        row = self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 1', (RECORD,)).fetchone()
        return self.store.read(Ref(RECORD, row[0]), {SCOPE}) if row else None

    def deciders(self):
        rule = self.w.rights.rules('intent')
        return [rule['decider'], *rule.get('delegates', [])]

    def basis(self, records=None):
        records = records if records is not None else self.w.latest_records()
        intents = [r for r in records if r['kind'] == 'intent']
        intent = max(intents, key=lambda r: r['ref'].revision) if intents else None
        levels = {k: v['level'] for k, v in sorted(evidence_levels(records).items())}
        measures = [r for r in records if r['kind'] == 'success-measure' and r['body'].get('active', True)]
        issues = [r for r in records if r['kind'] == 'bridge-issue' and r['body'].get('status') in OPEN]
        cases = [r for r in records if r['kind'] == 'decision-case' and r['body'].get('status') not in CLOSED_CASES]
        published = [r for r in records if r['kind'] == 'intake-case' and r['body'].get('status') == 'published']
        values = (published[0]['body'].get('snapshot') or {}).get('values') or {} if published else {}
        return dict(
            intent=asdict(intent['ref']) if intent else None,
            requirement_levels=levels,
            measures=len(measures),
            measures_with_target=sum(1 for m in measures if str(m['body'].get('target') or '').strip()),
            open_issues=len(issues),
            open_conflicts=sum(1 for i in issues if i['body'].get('kind') in {'challenge', 'conflict'}),
            open_decisions=len(cases),
            validation_questions=sum(1 for k in ('research_question', 'operations_question') if str(values.get(k) or '').strip()),
        )

    def state(self, records=None):
        current = self.current()
        basis = self.basis(records)
        history = []
        for row in self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 10', (RECORD,)):
            r = self.store.read(Ref(RECORD, row[0]), {SCOPE})
            b = r['body']
            history.append(dict(ref=asdict(r['ref']), outcome=b['outcome'], label=OUTCOMES[b['outcome']], reason=b['reason'],
                                conditions=b.get('conditions', ''), actor=b['actor'], at=b['at']))
        changed = bool(current) and current['body']['basis_fingerprint'] != fingerprint(basis)
        return dict(ref=asdict(current['ref']) if current else None, current=history[0] if history else None, history=history,
                    basis=basis, basis_changed=changed, recorded_basis=current['body']['basis'] if current else None,
                    can_decide=self.w.actor in self.deciders(), deciders=self.deciders(), outcomes=OUTCOMES)

    def decide(self, data):
        if self.w.actor not in self.deciders():
            raise PermissionError('Only the Business direction decider or a delegate can record readiness.')
        outcome = data.get('outcome')
        if outcome not in OUTCOMES:
            raise ValueError('Choose Ready to build, Ready with conditions or Not yet.')
        reason = data.get('reason')
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ValueError('Explain the call in up to 2000 characters.')
        conditions = data.get('conditions') or ''
        if not isinstance(conditions, str) or len(conditions) > 2000:
            raise ValueError('Keep conditions under 2000 characters.')
        if outcome == 'ready-with-conditions' and not conditions.strip():
            raise ValueError('Name the conditions that must hold.')
        if outcome != 'ready-with-conditions':
            conditions = ''
        if data.get('confirm') is not True:
            raise ValueError('Explicitly confirm the readiness call.')
        with self.store.transaction():
            previous = self.current()
            expected = asdict(previous['ref']) if previous else None
            if data.get('expected') != expected:
                raise StaleBasis('Someone recorded a readiness call since you opened this. Reopen it before deciding.')
            basis = self.basis()
            body = dict(outcome=outcome, reason=reason.strip(), conditions=conditions.strip(), basis=basis,
                        basis_fingerprint=fingerprint(basis), actor=self.w.actor, at=now(), previous=expected,
                        decision_rights=dict(kind='intent', deciders=self.deciders()))
            ref = self.store.put(RECORD, KIND, SCOPE, body, previous['ref'].revision if previous else 0)
        return dict(message=f'Readiness recorded: {OUTCOMES[outcome]}. Earlier calls are kept.', ref=asdict(ref))
