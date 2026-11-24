"""A project team adopts an enterprise concept at an exact version (D009).

The adoption is a record in the project's own store, with the full wording as it
stood at that version, so the project never depends on a live copy. Moving to a
newer version, or dropping the concept, is a deliberate new revision by the team's
lead with a reason. The enterprise concept is resolved and checked by the server
before this runs; nothing the browser sends is trusted as the concept.
"""
from dataclasses import asdict

from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .domain import txt

KIND = 'enterprise-adoption'
WORDING = ('kind', 'title', 'definition', 'includes', 'excludes', 'not_confused_with', 'reach', 'named')


class Adoptions:
    def __init__(self, w):
        self.w = w
        self.store = w.store

    def _latest(self, record_id):
        row = self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 1', (record_id,)).fetchone()
        return self.store.read(Ref(record_id, row[0]), {SCOPE}) if row else None

    def state(self):
        rows = self.store.db.execute(
            "SELECT r.id,r.revision FROM records r JOIN (SELECT id,MAX(revision) rev FROM records WHERE kind=? GROUP BY id) x "
            "ON r.id=x.id AND r.revision=x.rev ORDER BY r.rowid", (KIND,))
        items = []
        for r in rows:
            record = self.store.read(Ref(r['id'], r['revision']), {SCOPE})
            b = record['body']
            items.append(dict(ref=asdict(record['ref']), domain=b['domain'], concept=b['concept'], wording=b['wording'], origin=b['origin'],
                              status=b['status'], actor=b['actor'], at=b['at'], reason=b['reason']))
        return dict(items=items)

    def _lead(self, domain):
        definition = self.w.domain_knowledge.definition(domain)
        if self.w.actor not in definition['leaders']:
            raise PermissionError('Only this team’s lead can adopt, update or drop an enterprise concept.')
        return definition

    def adopt(self, data):
        domain = data.get('domain')
        definition = self._lead(domain)
        concept = data.get('_enterprise')  # set by the server from the enterprise store, never by the browser
        if not isinstance(concept, dict):
            raise ValueError('Choose a current enterprise concept.')
        if concept['reach'] == 'named-domains' and definition['label'].casefold() not in {n.casefold() for n in concept['named']}:
            raise PermissionError('This concept reaches only ' + ', '.join(concept['named']) + '.')
        if concept['origin'].get('project') == data.get('_project') and concept['origin'].get('domain') == domain:
            raise ValueError('This is your own team’s concept. It is already yours.')
        reason = txt(data, 'reason', 1000, True)
        if data.get('confirm') is not True:
            raise ValueError('Explicitly confirm the adoption.')
        record_id = 'ADOPT-' + concept['ref']['id'] + '-' + domain
        with self.store.transaction():
            previous = self._latest(record_id)
            expected = asdict(previous['ref']) if previous else None
            if data.get('expected') != expected:
                raise StaleBasis('This adoption changed. Reopen it before saving.')
            if previous and previous['body']['status'] == 'adopted' and previous['body']['concept'] == concept['ref']:
                raise ValueError('Your team already uses this version.')
            body = dict(domain=domain, concept=concept['ref'], wording={k: concept[k] for k in WORDING},
                        origin={k: concept['origin'].get(k) for k in ('project_title', 'domain_label')}, status='adopted',
                        actor=self.w.actor, at=now(), reason=reason, previous=expected)
            ref = self.store.put(record_id, KIND, SCOPE, body, previous['ref'].revision if previous else 0)
        return dict(message=f"Adopted {concept['title']} at version {concept['ref']['revision']}. It stays at this version until your team moves it.", ref=asdict(ref))

    def drop(self, data):
        raw = data.get('adoption') or {}
        with self.store.transaction():
            previous = self._latest(str(raw.get('id', '')))
            if not previous or previous['kind'] != KIND:
                raise ValueError('Choose an adopted concept.')
            if asdict(previous['ref']) != raw:
                raise StaleBasis('This adoption changed. Reopen it before saving.')
            body = previous['body']
            self._lead(body['domain'])
            if body['status'] != 'adopted':
                raise ValueError('This concept is not in use.')
            reason = txt(data, 'reason', 1000, True)
            body.update(status='dropped', actor=self.w.actor, at=now(), reason=reason, previous=raw)
            ref = self.store.put(previous['ref'].id, KIND, SCOPE, body, previous['ref'].revision)
        return dict(message='Dropped. The record of its use is kept.', ref=asdict(ref))
