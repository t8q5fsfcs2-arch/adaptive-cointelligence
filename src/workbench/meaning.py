"""Meaning proposals and decisions between teams (D009 step 2).

A typed mapping between two teams' concepts, or sharing one team's concept with
another team, is proposed by a team member and decided explicitly by the lead of
each team it touches. Nothing is inferred and no model is involved. Approved
mappings and shares are a projection over these records; team knowledge itself is
never rewritten. Each proposal keeps the exact concept wording it was based on,
and a concept that changed since cannot be approved on the old basis.
"""
from dataclasses import asdict
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import SCOPE, fingerprint, now
from .domain import txt
from .domain_knowledge import meaning, snapshot

KIND = 'meaning-proposal'
RELATIONS = {'same-as': 'means the same as', 'broader': 'is broader than', 'narrower': 'is narrower than',
             'related': 'is related to', 'distinct-from': 'is distinct from'}
TYPES = {'mapping': 'Mapping between teams', 'share': 'Share a concept with a team'}
OPEN = {'proposed'}


def concept_view(entry):
    """The wording a proposal is based on: only what gives the concept its meaning."""
    return dict(id=entry['id'], kind=entry['kind'], title=entry['title'], definition=entry['definition'], **meaning(entry))


class Meaning:
    def __init__(self, w):
        self.w = w
        self.store = w.store

    def domains(self):
        return {d['key']: d for d in self.w.domain_knowledge.definitions()}

    def concept(self, domain, entry_id):
        if domain not in self.domains():
            raise ValueError('Choose a configured team')
        entry = next((e for e in snapshot(self.store, domain)['entries'] if e['id'] == entry_id), None)
        if not entry or entry['kind'] not in {'term', 'category'} or entry['status'] == 'archived':
            raise ValueError('Choose a current term or category')
        return entry

    def rows(self):
        found = self.store.db.execute(
            "SELECT r.id,r.revision FROM records r JOIN (SELECT id,MAX(revision) rev FROM records WHERE kind=? GROUP BY id) x "
            "ON r.id=x.id AND r.revision=x.rev ORDER BY r.rowid DESC", (KIND,))
        return [self.store.read(Ref(r['id'], r['revision']), {SCOPE}) for r in found]

    def changed(self, body):
        """Names of concepts whose meaning differs from what the proposal was based on, or that are gone."""
        out = []
        for side in body['concepts']:
            try:
                current = concept_view(self.concept(side['domain'], side['concept']['id']))
            except ValueError:
                out.append(side['concept']['title'])
                continue
            if fingerprint(current) != side['fingerprint']:
                out.append(side['concept']['title'])
        return out

    def state(self):
        domains = self.domains()
        me = self.w.actor
        items = []
        for r in self.rows():
            b = r['body']
            waiting = [d for d in b['deciders'] if d not in b['decisions']] if b['status'] in OPEN else []
            items.append(dict(ref=asdict(r['ref']), type=b['type'], relation=b.get('relation'), status=b['status'], reason=b['reason'],
                              proposed_by=b['proposed_by'], at=b['at'], concepts=b['concepts'], grantee=b.get('grantee'),
                              deciders=b['deciders'], decisions=b['decisions'], waiting=waiting, closed=b.get('closed'),
                              changed=self.changed(b) if b['status'] in OPEN else [],
                              mine=[d for d in waiting if me in domains.get(d, {}).get('leaders', [])],
                              can_withdraw=b['status'] in OPEN and b['proposed_by'] == me,
                              can_retire=b['status'] == 'approved' and any(me in domains.get(d, {}).get('leaders', []) for d in b['deciders'])))
        member = any(me in d['members'] for d in domains.values())
        return dict(items=items, relations=RELATIONS, types=TYPES, can_propose=member,
                    waiting_on_me=sum(1 for i in items if i['mine']))

    def propose(self, data):
        domains = self.domains()
        if not any(self.w.actor in d['members'] for d in domains.values()):
            raise PermissionError('Only a member of a project team can propose a meaning change.')
        kind = data.get('type')
        if kind not in TYPES:
            raise ValueError('Choose a mapping or a share.')
        reason = txt(data, 'reason', 1000, True)
        source = data.get('from') or {}
        first = self.concept(source.get('domain'), source.get('id'))
        sides = [dict(domain=source['domain'], concept=concept_view(first))]
        body = dict(type=kind, reason=reason, proposed_by=self.w.actor, at=now(), status='proposed', decisions={})
        if kind == 'mapping':
            target = data.get('to') or {}
            if data.get('relation') not in RELATIONS:
                raise ValueError('Choose how the two concepts relate.')
            if target.get('domain') == source['domain']:
                raise ValueError('A mapping joins concepts from two different teams. Use a relationship inside one team.')
            second = self.concept(target.get('domain'), target.get('id'))
            sides.append(dict(domain=target['domain'], concept=concept_view(second)))
            body.update(relation=data['relation'], deciders=[source['domain'], target['domain']])
        else:
            grantee = data.get('grantee')
            if grantee not in domains or grantee == source['domain']:
                raise ValueError('Choose another team to share this concept with.')
            body.update(grantee=grantee, deciders=[source['domain']])
        for side in sides:
            side['fingerprint'] = fingerprint(side['concept'])
            side['knowledge'] = snapshot(self.store, side['domain'])['ref']
        body['concepts'] = sides
        with self.store.transaction():
            for r in self.rows():
                o = r['body']
                if o['status'] in OPEN | {'approved'} and o['type'] == kind and o.get('grantee') == body.get('grantee') \
                        and {(s['domain'], s['concept']['id']) for s in o['concepts']} == {(s['domain'], s['concept']['id']) for s in sides}:
                    raise ValueError('This is already proposed or approved. Retire or withdraw it before proposing again.')
            ref = self.store.put('MEANING-' + uuid4().hex[:12], KIND, SCOPE, body)
        return dict(message='Proposed. Each team lead it touches decides; nothing changes until they do.', ref=asdict(ref))

    def _open(self, data):
        raw = data.get('proposal') or {}
        record = self.store.latest(str(raw.get('id', '')), {SCOPE})
        if record['kind'] != KIND:
            raise ValueError('Choose a meaning proposal.')
        if asdict(record['ref']) != raw:
            raise StaleBasis('This proposal changed. Reopen it before acting.')
        return record

    def decide(self, data):
        outcome = data.get('outcome')
        if outcome not in {'approve', 'decline'}:
            raise ValueError('Approve or decline.')
        reason = txt(data, 'reason', 1000, True)
        if data.get('confirm') is not True:
            raise ValueError('Explicitly confirm your decision.')
        domains = self.domains()
        with self.store.transaction():
            record = self._open(data)
            body = record['body']
            if body['status'] not in OPEN:
                raise ValueError('This proposal is already closed.')
            mine = [d for d in body['deciders'] if d not in body['decisions'] and self.w.actor in domains.get(d, {}).get('leaders', [])]
            if not mine:
                raise PermissionError('Only the lead of a team this touches, who has not yet decided, can decide.')
            if outcome == 'approve':
                changed = self.changed(body)
                if changed:
                    raise StaleBasis('Changed since this was proposed: ' + ', '.join(changed) + '. Decline or withdraw it and propose again.')
            for d in mine:
                body['decisions'][d] = dict(actor=self.w.actor, outcome=outcome, reason=reason, at=now())
            if outcome == 'decline':
                body.update(status='declined', closed=dict(actor=self.w.actor, at=now(), reason=reason))
            elif all(body['decisions'].get(d, {}).get('outcome') == 'approve' for d in body['deciders']):
                body.update(status='approved', closed=dict(actor=self.w.actor, at=now(), reason=reason))
            ref = self.store.put(record['ref'].id, KIND, SCOPE, body, record['ref'].revision)
        done = body['status']
        return dict(message='Approved and in effect.' if done == 'approved' else 'Declined. The proposal is kept.' if done == 'declined'
                    else 'Your approval is recorded. Waiting on the other team lead.', ref=asdict(ref))

    def close(self, data):
        """Withdraw an open proposal (its proposer) or retire an approved one (a lead of a team it touches)."""
        reason = txt(data, 'reason', 1000, True)
        domains = self.domains()
        with self.store.transaction():
            record = self._open(data)
            body = record['body']
            if body['status'] in OPEN:
                if body['proposed_by'] != self.w.actor:
                    raise PermissionError('Only the person who proposed this can withdraw it.')
                status = 'withdrawn'
            elif body['status'] == 'approved':
                if not any(self.w.actor in domains.get(d, {}).get('leaders', []) for d in body['deciders']):
                    raise PermissionError('Only the lead of a team this touches can retire it.')
                status = 'retired'
            else:
                raise ValueError('This proposal is already closed.')
            body.update(status=status, closed=dict(actor=self.w.actor, at=now(), reason=reason))
            ref = self.store.put(record['ref'].id, KIND, SCOPE, body, record['ref'].revision)
        return dict(message='Withdrawn.' if status == 'withdrawn' else 'Retired. It is no longer in effect; the record is kept.', ref=asdict(ref))
