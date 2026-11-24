"""Explicit finding-to-intent requests. Published findings never rewrite intent.

The sponsor prepares a response in a private draft. Domain review and direction
publication commit that response. Requirement approval waits only for requests
whose declared scope includes that requirement (or the whole initiative).
"""
from dataclasses import asdict
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import SCOPE, DecisionBlocked, now
from .validation import required, reference

OPEN = {'open', 'drafted', 'deferred'}


def requests(store):
    rows = store.db.execute("SELECT id,MAX(revision) rev FROM records WHERE kind='intent-refinement' AND scope=? GROUP BY id ORDER BY MIN(rowid) DESC", (SCOPE,))
    return [store.read(Ref(r['id'], r['rev']), {SCOPE}) for r in rows]


def blockers(store, requirement_id):
    return [r for r in requests(store) if r['body']['status'] in OPEN and
            (not r['body']['requirement_refs'] or any(x['id'] == requirement_id for x in r['body']['requirement_refs']))]


class IntentRefinements:
    def __init__(self, intake):
        self.intake, self.store, self.actor = intake, intake.store, intake.actor

    def values(self, intent):
        if 'intake' in intent['body']:
            return intent['body']['intake']
        # Read an earlier intake publication without rewriting its record.
        for c in self.intake.cases():
            if c['body'].get('result', {}).get('intent') == asdict(intent['ref']):
                return c['body']['snapshot']['values']
        v = dict(intent['body'].get('value_proposition', {}))
        v.setdefault('value', intent['body'].get('text', ''))
        ctx = self.intake.latest('CTX-001')
        if ctx and ctx['body'].get('intent') == asdict(intent['ref']):
            from .intake import CONTEXT_FIELDS
            v.update({k: ctx['body'][k] for k in CONTEXT_FIELDS if k in ctx['body']})
        return v

    def current(self, raw):
        ref = reference(raw)
        r = self.store.latest(ref.id, {SCOPE})
        if r['kind'] != 'intent-refinement' or r['ref'] != ref:
            raise StaleBasis('This intent request changed. Reload it')
        if r['body']['status'] not in OPEN:
            raise DecisionBlocked('This request is resolved. Open another request for further change')
        return r

    def create(self, data):
        from .intake import ALL_FIELDS
        field = required(data, 'field')
        if field not in ALL_FIELDS or field in {'work_kind', 'assumption_owner'}:
            raise ValueError('Choose a narrative field in the business intent')
        with self.store.transaction():
            intent = self.store.latest('INT-001', {SCOPE})
            if intent['ref'] != reference(data.get('base_intent')):
                raise StaleBasis('Business intent changed. Review its current version first')
            source = self.store.read(reference(data.get('source')), {SCOPE})
            if source['kind'] != 'contribution':
                raise ValueError('Publish a finding to Decisions & Issues before using it here')
            if self.store.latest(source['ref'].id, {SCOPE})['ref'] != source['ref']:
                raise StaleBasis('The finding changed. Use its current published version')
            proposed = required(data, 'proposed_value')
            previous = self.values(intent).get(field, '')
            if proposed == previous:
                raise ValueError('Describe a change to the current intent')
            linked = data.get('requirement_refs', [])
            if not isinstance(linked, list) or len(linked) > 100:
                raise ValueError('Choose the affected requirements, or the whole initiative')
            refs = sorted(set(reference(r) for r in linked))
            for r in refs:
                record = self.store.read(r, {SCOPE})
                if record['kind'] != 'requirement' or self.store.latest(r.id, {SCOPE})['ref'] != r:
                    raise StaleBasis('Review the current affected requirements')
            body = dict(source=asdict(source['ref']), base_intent=asdict(intent['ref']),
                        field=field, previous_value=previous, proposed_value=proposed,
                        rationale=required(data, 'rationale'), requirement_refs=[asdict(r) for r in refs],
                        status='open', requested_by=self.actor, requested_at=now(),
                        boundary='Proposed refinement only; no finding, requirement or intent is approved')
            ref = self.store.put('ICR-' + uuid4().hex[:10], 'intent-refinement', SCOPE, body)
            for basis in [source['ref'], intent['ref'], *refs]:
                self.store.depend(ref, basis, {SCOPE})
        return {'message': 'Intent refinement sent to the sponsor. The current direction is unchanged.', 'id': ref.id}

    def adopt(self, data):
        from .sponsor import sync_intent_field
        self.intake.sponsor()
        with self.store.transaction():
            r = self.current(data.get('expected'))
            body = r['body']
            if self.intake.latest('INT-001')['ref'] != reference(body['base_intent']):
                raise StaleBasis('Intent has changed. Submit a new request against the current direction')
            if self.store.latest(body['source']['id'], {SCOPE})['ref'] != reference(body['source']):
                raise StaleBasis('The finding changed. Submit a new request using its latest version')
            draft = self.intake.draft(data.get('draft_expected'))
            selected = [x for x in draft['body'].get('refinements', [])
                        if self.store.latest(x['id'], {SCOPE})['body']['status'] == 'drafted' and x['id'] != r['ref'].id]
            if any(self.store.read(reference(x), {SCOPE})['body']['field'] == body['field'] for x in selected):
                raise DecisionBlocked('Another drafted request addresses this field. Resolve it before replacing that response')
            response = required(data, 'response')
            note = required(data, 'rationale')
            body.update(status='drafted', responded_by=self.actor, responded_at=now())
            updated = self.store.put(r['ref'].id, r['kind'], SCOPE, body, r['ref'].revision)
            left = sync_intent_field(draft['body'], body['field'], response) or []
            draft['body']['refinements'] = [*selected, asdict(updated)]
            draft['body'].setdefault('refinement_notes', {})[r['ref'].id] = note
            self.intake.save_draft(draft, draft['body'])
        review = (' Your ' + ' and '.join(left) + ' wording was different, so it was left as you wrote it. Review it in Business Intent.') if left else ''
        return {'message': 'Sponsor response added to the private intake draft. Business Intent and Context wording were updated together. Refresh drawers and request both domain reviews before publication.' + review, 'id': r['ref'].id, 'left_for_review': left}

    def dispose(self, data):
        from .sponsor import FIELD_QUESTIONS, sync_intent_field
        self.intake.sponsor()
        disposition = data.get('disposition')
        if disposition not in {'declined', 'deferred'}:
            raise ValueError('Choose decline or defer')
        with self.store.transaction():
            r = self.current(data.get('expected'))
            if r['body']['status'] == 'drafted':
                draft = self.intake.draft(data.get('draft_expected'))
                # The UI explicitly previews this reset; draft history is preserved.
                baseline = self.intake.latest('INT-001')
                field = r['body']['field']
                saved_answer = baseline['body'].get('business_brief', {}).get('answers', {}).get(FIELD_QUESTIONS.get(field))
                sync_intent_field(draft['body'], field, self.values(baseline).get(field, ''), restored_answer=saved_answer)
                draft['body']['refinements'] = [x for x in draft['body'].get('refinements', []) if x['id'] != r['ref'].id]
                draft['body'].get('refinement_notes', {}).pop(r['ref'].id, None)
                self.intake.save_draft(draft, draft['body'])
            body = r['body']
            body.update(status=disposition, sponsor_rationale=required(data, 'rationale'), responded_by=self.actor, responded_at=now())
            if disposition == 'deferred':
                from .decisions import ACTORS
                if data.get('next_owner') not in ACTORS:
                    raise ValueError('Name the next owner')
                body.update(next_owner=data['next_owner'], next_question=required(data, 'next_question'))
            ref = self.store.put(r['ref'].id, r['kind'], SCOPE, body, r['ref'].revision)
        return {'message': 'Sponsor response saved. Prior intent and requirement decisions remain unchanged.', 'id': ref.id}

    def finding_basis(self, snapshot):
        baseline = self.intake.latest('INT-001')
        ids = {r['id'] for r in baseline['body'].get('finding_basis', [])} if baseline else set()
        ids.update(r['body']['source']['id'] for r in self.selected(snapshot))
        return [asdict(self.store.latest(id, {SCOPE})['ref']) for id in sorted(ids)]

    def selected(self, snapshot):
        return [self.store.read(reference(raw), {SCOPE}) for raw in snapshot.get('refinements', [])]

    def freshness(self, snapshot):
        issues = []
        for raw in snapshot.get('finding_basis', []):
            if self.store.latest(raw['id'], {SCOPE})['ref'] != reference(raw):
                issues.append('An intake finding changed; request a fresh direction review')
        for r in self.selected(snapshot):
            b = r['body']
            if self.store.latest(r['ref'].id, {SCOPE})['ref'] != r['ref'] or b['status'] != 'drafted':
                issues.append('A selected intent request changed; refresh the sponsor draft and review')
            if self.store.latest(b['source']['id'], {SCOPE})['ref'] != reference(b['source']):
                issues.append('A finding supporting the intent response changed; review the latest finding')
            if self.intake.latest('INT-001')['ref'] != reference(b['base_intent']):
                issues.append('The request refers to an earlier business intent; submit a refreshed request')
        return issues

    def finalize(self, snapshot, intent, decision):
        result = []
        for r in self.selected(snapshot):
            body = r['body']
            body.update(status='incorporated', sponsor_rationale=snapshot.get('refinement_notes', {}).get(r['ref'].id, ''), result_intent=asdict(intent), decision=asdict(decision),
                        published_value=snapshot['values'][body['field']], resolved_at=now())
            result.append(self.store.put(r['ref'].id, r['kind'], SCOPE, body, r['ref'].revision))
        return result
