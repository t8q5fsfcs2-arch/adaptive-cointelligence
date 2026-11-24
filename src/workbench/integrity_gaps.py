"""Human follow-up on exact saved judgments. Collection is not reassessment.

No model calls, inferred assignments, resolution decisions or authority changes.
Cards are projections; only an explicit response writes records.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .validation import reference

SOURCE_KINDS = {'source', 'intake-source', 'contribution', 'evidence', 'integrity-gap-source'}
SOURCE_FIELDS = ('text', 'statement', 'observation', 'content')
GAP_REVIEW_KINDS = {'integrity-assessment', 'integrity-gap-review'}
BOUNDARY = ('Information supplied; awaiting review. The saved judgment, evidence level, '
            'scope decisions and approvals are unchanged.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]


def text(data, key, limit, optional=False):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > limit or (not optional and not value.strip()):
        raise ValueError(f'{key.replace("_", " ").capitalize()} must contain 1–{limit} characters')
    return value.strip()


class IntegrityGaps:
    def __init__(self, workspace):
        self.w, self.store = workspace, workspace.store

    def assessment(self, raw):
        record = self.store.read(reference(raw), self.w.scopes)
        if record['kind'] not in GAP_REVIEW_KINDS:
            raise ValueError('Choose a saved AI partner reply or diagnostic gap')
        return record

    def thread(self, id):
        row = self.store.db.execute('SELECT MAX(revision) FROM records WHERE id=?', (id,)).fetchone()
        return self.store.read(Ref(id, row[0]), self.w.scopes) if row[0] else None

    def cards(self, assessment):
        body = assessment['body']; trace = body.get('decision_trace') or {}
        findings = {(f['packet_ref'], p['part_ref']): p
                    for f in trace.get('packet_findings', []) for p in f.get('parts', [])}
        groups = {}
        for group in trace.get('mapping_groups', []):
            if group.get('applicability', {}).get('status') == 'shared':
                for clause in group['clause_refs']:
                    groups[clause] = group['representative']
        cards = {}
        for gap in trace.get('recommendation', {}).get('unresolved_material_gaps', []):
            part = findings.get((gap['packet_ref'], gap['part_ref']), {})
            # Collapse only explicitly shared mappings with identical judgments/requests.
            # Retain every original occurrence, including its distinct source reference.
            clause = gap['obligation_ref']; canonical = groups.get(clause, clause)
            identity = [gap['packet_ref'], canonical, gap['part_ref'].removeprefix(clause),
                        gap['status'], gap['remaining_gap'], part.get('interpretation'),
                        part.get('evidence_refs'), part.get('reasoning')]
            key = digest(identity)
            if key not in cards:
                basis = body.get('context', {}).get('review_basis', {})
                cards[key] = dict(key=key, assessment=asdict(assessment['ref']),
                    thread_id='IGAP-'+digest([asdict(assessment['ref']), key]),
                    title=gap['source'].get('meaning') or gap['source']['quote'],
                    missing=gap['remaining_gap'], status=gap['status'],
                    interpretation=deepcopy(part.get('interpretation', {})),
                    reasoning=part.get('reasoning', ''), source=deepcopy(gap['source']),
                    evidence_level=trace.get('evidence_level', 'Not recorded'),
                    evidence_quotes=deepcopy(part.get('evidence_quotes', [])),
                    support_scope=part.get('support_scope', ''),
                    record_kind=assessment['kind'],
                    provenance=deepcopy(body.get('gap_provenance', {})),
                    clarification_request=deepcopy(body.get('clarification_requests', {}).get(gap['part_ref'], {})),
                    purpose=basis.get('purpose', 'Not recorded'), basis_boundary=basis.get('boundary', ''),
                    scope=assessment['scope'], occurrences=[])
            cards[key]['occurrences'].append({k: deepcopy(gap[k]) for k in
                ('key', 'packet_ref', 'obligation_ref', 'part_ref')})
        return list(cards.values())

    def selected(self, data):
        assessment = self.assessment(data.get('assessment'))
        card = next((c for c in self.cards(assessment) if c['key'] == data.get('key')), None)
        if card is None:
            raise ValueError('Choose a gap from this exact saved review')
        return assessment, card

    def state(self):
        out = []
        # Diagnostic excerpts can collect follow-up without masquerading as full
        # assessments. Integrity approval paths still accept only assessments.
        for assessment in self.w.latest_records():
            if assessment['kind'] not in GAP_REVIEW_KINDS:
                continue
            for card in self.cards(assessment):
                thread = self.thread(card['thread_id'])
                card['response_count'] = len(thread['body']['responses']) if thread else 0
                card['collection_status'] = 'information-supplied' if thread else 'information-needed'
                out.append({k: v for k, v in card.items() if k not in
                            {'evidence_quotes', 'source', 'interpretation', 'reasoning', 'support_scope'}})
        return out

    def source_allowed(self, record, scope):
        # A private source cannot be copied into a shared or another domain's response.
        return record['kind'] in SOURCE_KINDS and record['scope'] in {scope, SCOPE}

    def read(self, data):
        assessment, card = self.selected(data)
        thread = self.thread(card['thread_id'])
        card['expected'] = asdict(thread['ref']) if thread else None
        card['responses'] = [dict(ref=raw, **self.store.read(Ref(**raw), self.w.scopes)['body'])
                             for raw in thread['body']['responses']] if thread else []
        card['sources'] = [dict(ref=asdict(r['ref']), title=r['body'].get('title', r['ref'].id),
                               field_names=[f for f in SOURCE_FIELDS
                                            if isinstance(r['body'].get(f), str) and r['body'][f]])
                          for r in self.w.latest_records() if self.source_allowed(r, assessment['scope'])
                          and any(isinstance(r['body'].get(f), str) and r['body'][f] for f in SOURCE_FIELDS)]
        card['boundary'] = BOUNDARY
        card['assessment_has_newer_version'] = self.store.latest(assessment['ref'].id, self.w.scopes)['ref'] != assessment['ref']
        return card

    def read_source(self, data):
        assessment, _ = self.selected(data)
        source = self.store.read(reference(data.get('source')), self.w.scopes)
        if not self.source_allowed(source, assessment['scope']):
            raise PermissionError('This source cannot be used in this gap’s scope')
        return dict(ref=asdict(source['ref']), fields={f: source['body'][f] for f in SOURCE_FIELDS
                    if isinstance(source['body'].get(f), str)})

    def respond(self, data):
        self.w.rights.live_member(self.w.actor)
        assessment, card = self.selected(data)
        request = text(data, 'request_id', 100)
        kind = data.get('kind')
        if kind not in {'evidence', 'clarification', 'hunch', 'next-action'}:
            raise ValueError('Choose evidence, clarification, a hunch or a proposed next action')
        note = text(data, 'note', 4000)
        # The server, not a supplied actor field, determines attribution.
        actor = dict(actor=self.w.actor, principal=self.w.principal_id)
        rid = 'IGRESP-'+digest([actor, request])
        signature = digest({k: v for k, v in data.items() if k not in {'actor', 'principal'}})
        with self.store.transaction():
            prior = self.thread(rid)
            if prior:
                if prior['body']['request_signature'] != signature:
                    raise ValueError('This request identifier was already used for a different response')
                return dict(ref=asdict(prior['ref']), message=BOUNDARY)
            current = self.thread(card['thread_id'])
            expected = data.get('expected')
            if expected != (asdict(current['ref']) if current else None):
                raise StaleBasis('Another response was saved. Reopen this gap before adding yours; keep your draft.')
            evidence = None; bases = [assessment['ref']]
            if kind == 'evidence':
                supplied = data.get('evidence') or {}
                if supplied.get('ref'):
                    source = self.store.read(reference(supplied['ref']), self.w.scopes)
                    if not self.source_allowed(source, assessment['scope']):
                        raise PermissionError('Use a source visible in this gap’s scope, or publish it through the existing sharing flow')
                    if self.store.latest(source['ref'].id, self.w.scopes)['ref'] != source['ref']:
                        raise StaleBasis('This source changed. Reopen the gap and select its current version')
                    field = supplied.get('field'); quote = text(supplied, 'quote', 4000)
                    if field not in SOURCE_FIELDS or not isinstance(source['body'].get(field), str) or quote not in source['body'][field]:
                        raise ValueError('The passage must match the exact selected source field')
                    evidence = dict(ref=asdict(source['ref']), field=field, quote=quote,
                                    provenance='Exact stored passage; relevance and sufficiency await review')
                else:
                    title = text(supplied, 'title', 200)
                    passage = text(supplied, 'text', 12000)
                    locator = text(supplied, 'source_locator', 1500)
                    source_ref = self.store.put('IGSRC-'+digest([actor, request]), 'integrity-gap-source',
                        assessment['scope'], dict(title=title, text=passage, source_locator=locator,
                        status='human-supplied-unverified', **actor, at=now()))
                    source = self.store.read(source_ref, self.w.scopes)
                    evidence = dict(ref=asdict(source_ref), field='text', quote=passage,
                                    provenance='Human-supplied source text; origin and sufficiency await review')
                bases.append(source['ref'])
                evidence['title'] = source['body'].get('title', source['ref'].id)
                evidence['source_locator'] = source['body'].get('source_locator', '')
            elif data.get('evidence'):
                raise ValueError('Only an evidence response may attach source evidence')
            authority = {'evidence': 'Contributor input; not ratification',
                         'clarification': 'Contributor interpretation; not a governing decision',
                         'hunch': 'Unverified hunch; not evidence',
                         'next-action': 'Proposed next action; not assigned or authorized'}[kind]
            response = dict(assessment=asdict(assessment['ref']), gap_key=card['key'],
                occurrences=card['occurrences'], evidence_level=card['evidence_level'],
                kind=kind, note=note, evidence=evidence, **actor, at=now(),
                status='awaiting-review', authority=authority,
                boundary=BOUNDARY, request_signature=signature)
            ref = self.store.put(rid, 'integrity-gap-response', assessment['scope'], response)
            for basis in bases:
                self.store.depend(ref, basis, self.w.scopes)
            thread_ref = self.store.put(card['thread_id'], 'integrity-gap-follow-up', assessment['scope'],
                dict(assessment=asdict(assessment['ref']), gap_key=card['key'], occurrences=card['occurrences'],
                     status='information-supplied', responses=(current['body']['responses'] if current else [])+[asdict(ref)]),
                expected_revision=current['ref'].revision if current else 0)
            self.store.depend(thread_ref, ref, self.w.scopes)
            self.store.depend(thread_ref, assessment['ref'], self.w.scopes)
        return dict(ref=asdict(ref), message=BOUNDARY)
