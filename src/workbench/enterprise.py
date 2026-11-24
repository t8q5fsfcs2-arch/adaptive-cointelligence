"""Enterprise meaning layer (D009 step 3): one store above the projects.

It holds three things as versioned records: who holds the two enterprise roles,
proposals to widen a team concept's reach beyond its domain, and the enterprise
concepts those approvals create. Nothing flows up from a project automatically: a
concept enters only through a proposal that the concept's own team lead and an
enterprise steward both approve, as two different people. Semantic services
proposes and never decides. Project stores are only read here, never written.

The overview reads counts and names from each project's shared team knowledge. It
does not expose concept wording from projects the viewer is not a member of.
"""
from dataclasses import asdict
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4

from .core import Ref, Store, StaleBasis
from .decisions import PERSONAS, SCOPE, fingerprint, now
from .domain import configured_domains, txt
from .domain_knowledge import meaning, snapshot
from .meaning import concept_view

ENTERPRISE = 'enterprise'
ROLES = 'ENTERPRISE-ROLES'
ROLE_NAMES = {'semantic_services': 'Semantic services', 'stewards': 'Enterprise steward'}
WIDE = {'named-domains': 'Named domains', 'enterprise': 'Enterprise'}
CAPACITIES = ('lead', 'steward')


def curation(concepts, bounded):
    """Empty: no concepts. Low: none has a boundary. High: every one has. Otherwise moderate."""
    return 'empty' if not concepts else 'low' if not bounded else 'high' if bounded == concepts else 'moderate'


class Enterprise:
    def __init__(self, anchor, projects):
        anchor = Path(anchor).resolve()
        self.path = anchor.with_name(anchor.stem + '-enterprise.sqlite3')
        self.projects = projects
        self.lock = threading.RLock()
        Store(self.path).close()

    # ---- reading
    def _latest(self, store, kind):
        rows = store.db.execute(
            "SELECT r.id,r.revision FROM records r JOIN (SELECT id,MAX(revision) rev FROM records WHERE kind=? GROUP BY id) x "
            "ON r.id=x.id AND r.revision=x.rev ORDER BY r.rowid DESC", (kind,))
        return [store.read(Ref(r['id'], r['revision']), {ENTERPRISE}) for r in rows]

    def _roles(self, store):
        found = self._latest(store, 'enterprise-roles')
        return found[0] if found else None

    def roles(self, store):
        record = self._roles(store)
        return record['body']['roles'] if record else {k: [] for k in ROLE_NAMES}

    def _catalog(self):
        with self.projects.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM projects ORDER BY created_at,id')]

    def _project(self, project_id):
        """Shared team knowledge of one project, read-only: domains, their leads, concepts and open proposals."""
        row = next((p for p in self._catalog() if p['id'] == project_id), None)
        if not row:
            raise ValueError('Choose an existing project.')
        store = Store(row['path'])
        try:
            title = ''
            try:
                title = store.latest('PROJECT-001', {SCOPE})['body'].get('title', '')
            except PermissionError:
                pass
            domains = {}
            for key, d in configured_domains(store).items():
                saved = snapshot(store, key)
                domains[key] = dict(key=key, label=d['label'], leaders=list(d.get('leaders', d['authors'])), knowledge=saved['ref'],
                                    entries=saved['entries'])
            proposals = [dict(store.read(Ref(r['id'], r['revision']), {SCOPE})['body'], id=r['id'], revision=r['revision']) for r in store.db.execute(
                "SELECT r.id,r.revision FROM records r JOIN (SELECT id,MAX(revision) rev FROM records WHERE kind='meaning-proposal' GROUP BY id) x "
                "ON r.id=x.id AND r.revision=x.rev")]
        finally:
            store.close()
        return dict(id=project_id, title=title or 'Untitled project', domains=domains, proposals=proposals)

    def _concept(self, project, domain, entry_id):
        d = project['domains'].get(domain)
        entry = next((e for e in d['entries'] if e['id'] == entry_id), None) if d else None
        if not entry or entry['kind'] not in {'term', 'category'} or entry['status'] != 'active':
            raise ValueError('Choose an active term or category.')
        return entry

    def _changed(self, body, project=None):
        try:
            project = project or self._project(body['origin']['project'])
            current = concept_view(self._concept(project, body['origin']['domain'], body['origin']['entry']))
        except (ValueError, sqlite3.Error, OSError):
            return True
        return fingerprint(current) != body['fingerprint']

    def overview(self, store):
        rows = []
        reach = {'project': 0, 'domain': 0, 'named-domains': 0, 'enterprise': 0}
        concepts = self._latest(store, 'enterprise-concept')
        wide = {(c['body']['origin']['project'], c['body']['origin']['domain'], c['body']['origin']['entry']): c['body']['reach']
                for c in concepts if c['body']['status'] == 'active'}
        open_wide = [p['body'] for p in self._latest(store, 'enterprise-proposal') if p['body']['status'] == 'proposed']
        totals = dict(concepts=0, bounded=0, mappings=0, proposals=len(open_wide))
        for row in self._catalog():
            try:
                project = self._project(row['id'])
            except (sqlite3.Error, OSError, ValueError, PermissionError):
                continue
            mappings = sum(1 for p in project['proposals'] if p['type'] == 'mapping' and p['status'] == 'approved')
            totals['mappings'] += mappings
            for key, d in project['domains'].items():
                live = [e for e in d['entries'] if e['kind'] in {'term', 'category'} and e['status'] != 'archived']
                if not live and not d['knowledge']:
                    continue
                bounded = sum(1 for e in live if any(meaning(e)[k].strip() for k in ('includes', 'excludes', 'not_confused_with')))
                levels = [wide.get((row['id'], key, e['id']), meaning(e)['reach']) for e in live]
                for level in levels:
                    reach[level] += 1
                waiting = sum(1 for p in project['proposals'] if p['status'] == 'proposed' and any(s['domain'] == key for s in p['concepts'])) \
                    + sum(1 for p in open_wide if p['origin']['project'] == row['id'] and p['origin']['domain'] == key)
                totals['concepts'] += len(live)
                totals['bounded'] += bounded
                totals['proposals'] += sum(1 for p in project['proposals'] if p['status'] == 'proposed' and p['concepts'][0]['domain'] == key)
                rows.append(dict(project=row['id'], project_title=project['title'], domain=key, label=d['label'],
                                 leads=[PERSONAS.get(a, {}).get('name', a) for a in d['leaders']],
                                 concepts=len(live), bounded=bounded, curation=curation(len(live), bounded),
                                 widest=max(levels, key=list(reach).index) if levels else 'project', waiting=waiting,
                                 mappings=sum(1 for p in project['proposals'] if p['type'] == 'mapping' and p['status'] == 'approved'
                                              and any(s['domain'] == key for s in p['concepts'])),
                                 knowledge_version=d['knowledge']['revision'] if d['knowledge'] else 0))
        totals['enterprise'] = sum(1 for c in concepts if c['body']['status'] == 'active')
        return dict(domains=rows, totals=totals, reach=reach)

    def state(self, actor, admin, memberships):
        store = Store(self.path)
        try:
            record = self._roles(store)
            roles = self.roles(store)
            mine = [k for k in ROLE_NAMES if actor in roles[k]]
            can_view = bool(admin or mine)
            concepts = [dict(ref=asdict(c['ref']), **{k: c['body'][k] for k in ('title', 'definition', 'includes', 'excludes', 'not_confused_with',
                                                                              'reach', 'named', 'origin', 'status', 'at', 'approved')})
                        for c in self._latest(store, 'enterprise-concept')]
            proposals = []
            cache = {}
            for p in self._latest(store, 'enterprise-proposal'):
                b = p['body']
                pid = b['origin']['project']
                if not can_view and pid not in memberships:
                    continue
                open_ = b['status'] == 'proposed'
                capacities = []
                changed = False
                if open_:
                    try:
                        project = cache.setdefault(pid, self._project(pid))
                        changed = self._changed(b, project)
                        leaders = project['domains'].get(b['origin']['domain'], {}).get('leaders', [])
                    except (sqlite3.Error, OSError, ValueError, PermissionError):
                        leaders, changed = [], True
                    if actor not in roles['semantic_services']:
                        if 'lead' not in b['decisions'] and actor in leaders and pid in memberships:
                            capacities.append('lead')
                        if 'steward' not in b['decisions'] and actor in roles['stewards'] and b['decisions'].get('lead', {}).get('actor') != actor:
                            capacities.append('steward')
                proposals.append(dict(ref=asdict(p['ref']), status=b['status'], reach=b['reach'], named=b['named'], reason=b['reason'],
                                      proposed_by=b['proposed_by'], at=b['at'], origin=b['origin'], concept=b['concept'], decisions=b['decisions'],
                                      waiting=[c for c in CAPACITIES if c not in b['decisions']] if open_ else [], mine=capacities[:1],
                                      changed=changed, can_withdraw=open_ and b['proposed_by'] == actor, closed=b.get('closed')))
            sessions = [self._session_view(store, r, actor, roles, memberships, cache) for r in self._latest(store, 'enterprise-session')
                        if can_view or r['body']['project'] in memberships]
            for view in sessions:
                if not view['member']:
                    for item in view['items']:
                        if (item.get('link') or {}).get('type') == 'mapping':
                            item.pop('sides', None)   # wording of a project's teams stays with that project's members
            result = dict(roles_mine=mine, can_admin=bool(admin), can_view=can_view, role_names=ROLE_NAMES, reach_names=WIDE,
                          concepts=concepts, proposals=proposals, waiting_on_me=sum(1 for p in proposals if p['mine']), sessions=sessions, can_facilitate='semantic_services' in mine,
                          can_retire='stewards' in mine)
            if can_view:
                used = self._adoptions()
                for c in concepts:
                    c['used_by'] = used.get(c['ref']['id'], [])
                result['overview'] = self.overview(store)
                result['roles'] = dict(ref=asdict(record['ref']) if record else None, roles=roles,
                                       reason=record['body']['reason'] if record else '', at=record['body']['at'] if record else None)
            if admin:
                result['people'] = [dict(actor=a, name=p['name'], role=p['role']) for a, p in PERSONAS.items()]
            return result
        finally:
            store.close()

    def current_concept(self, raw):
        """The active enterprise concept at exactly the version asked for, or an error. Used when a project adopts one."""
        raw = raw if isinstance(raw, dict) else {}
        store = Store(self.path)
        try:
            try:
                record = store.latest(str(raw.get('id', '')), {ENTERPRISE})
            except PermissionError:
                raise ValueError('Choose a current enterprise concept.')
            if record['kind'] != 'enterprise-concept' or record['body']['status'] != 'active':
                raise ValueError('Choose a current enterprise concept.')
            if asdict(record['ref']) != raw:
                raise StaleBasis('This enterprise concept has a newer version. Reopen it before adopting.')
            return dict(ref=asdict(record['ref']), **record['body'])
        finally:
            store.close()

    def _adoptions(self):
        """Where each enterprise concept is in use: read from every project's own adoption records."""
        used = {}
        for row in self._catalog():
            try:
                store = Store(row['path'])
            except (sqlite3.Error, OSError):
                continue
            try:
                title = ''
                try:
                    title = store.latest('PROJECT-001', {SCOPE})['body'].get('title', '')
                except PermissionError:
                    pass
                labels = {k: d['label'] for k, d in configured_domains(store).items()}
                for r in store.db.execute(
                        "SELECT r.id,r.revision FROM records r JOIN (SELECT id,MAX(revision) rev FROM records WHERE kind='enterprise-adoption' GROUP BY id) x "
                        "ON r.id=x.id AND r.revision=x.rev"):
                    b = store.read(Ref(r['id'], r['revision']), {SCOPE})['body']
                    if b['status'] == 'adopted':
                        used.setdefault(b['concept']['id'], []).append(dict(project_title=title or 'Untitled project', team=labels.get(b['domain'], b['domain']),
                                                                             revision=b['concept']['revision']))
            except (sqlite3.Error, OSError, ValueError):
                pass
            finally:
                store.close()
        return used

    # ---- facilitated sessions (step 4)
    def _session_view(self, store, record, actor, roles, memberships, cache):
        """A session with each agenda item resolved against the live proposal it points to. Nothing here decides."""
        b = record['body']
        try:
            project = cache.setdefault(b['project'], self._project(b['project']))
        except (sqlite3.Error, OSError, ValueError, PermissionError):
            project = dict(id=b['project'], title=b['project_title'], domains={}, proposals=[])
        domain = project['domains'].get(b['domain'], {})
        reach = {p['ref'].id: p for p in self._latest(store, 'enterprise-proposal')}
        local = {p['id']: p for p in project['proposals']}
        labels = {k: d['label'] for k, d in project['domains'].items()}
        items = []
        for item in b['items']:
            view = dict(item, state='discussed' if item.get('discussed') else 'topic')
            link = item.get('link')
            if link and link['type'] == 'reach' and link['id'] in reach:
                p = reach[link['id']]
                pb = p['body']
                view.update(state={'proposed': 'open', 'approved': 'agreed'}.get(pb['status'], 'closed'), status=pb['status'],
                            proposal=asdict(p['ref']), sides=[dict(team=pb['origin']['domain_label'], concept=pb['concept'])],
                            waiting=[c for c in CAPACITIES if c not in pb['decisions']] if pb['status'] == 'proposed' else [],
                            ask='Reach: ' + ('Enterprise' if pb['reach'] == 'enterprise' else ', '.join(pb['named'])), reason=pb['reason'])
            elif link and link['type'] == 'mapping' and link['id'] in local:
                pb = local[link['id']]
                view.update(state={'proposed': 'open', 'approved': 'agreed'}.get(pb['status'], 'closed'), status=pb['status'],
                            proposal=dict(id=pb['id'], revision=pb['revision']),
                            sides=[dict(team=labels.get(side['domain'], side['domain']), concept=side['concept']) for side in pb['concepts']],
                            waiting=[labels.get(d, d) for d in pb['deciders'] if d not in pb['decisions']] if pb['status'] == 'proposed' else [],
                            ask=('Relation: ' + pb['relation']) if pb['type'] == 'mapping' else 'Share with ' + labels.get(pb.get('grantee'), ''), reason=pb['reason'])
            elif link:
                view.update(state='closed', status='missing')
            items.append(view)
        live = [e for e in domain.get('entries', []) if e['kind'] in {'term', 'category'} and e['status'] != 'archived']
        bounded = sum(1 for e in live if any(meaning(e)[k].strip() for k in ('includes', 'excludes', 'not_confused_with')))
        return dict(ref=asdict(record['ref']), title=b['title'], when=b['when'], status=b['status'], facilitator=b['facilitator'], summary=b.get('summary', ''),
                    project=b['project'], project_title=project['title'], domain=b['domain'], domain_label=domain.get('label', b['domain_label']),
                    leads=domain.get('leaders', []), items=items, agreed=sum(1 for i in items if i['state'] in {'agreed', 'discussed'}),
                    can_edit=b['status'] == 'open' and actor in roles['semantic_services'], member=b['project'] in memberships,
                    health=dict(concepts=len(live), bounded=bounded,
                                mappings=sum(1 for p in project['proposals'] if p['type'] == 'mapping' and p['status'] == 'approved' and any(c['domain'] == b['domain'] for c in p['concepts'])),
                                open=sum(1 for p in project['proposals'] if p['status'] == 'proposed' and any(c['domain'] == b['domain'] for c in p['concepts']))
                                + sum(1 for p in reach.values() if p['body']['status'] == 'proposed' and p['body']['origin']['project'] == b['project'] and p['body']['origin']['domain'] == b['domain'])),
                    linkable=[dict(type='reach', id=p['ref'].id, title='Wider reach: ' + p['body']['concept']['title']) for p in reach.values()
                              if p['body']['status'] == 'proposed' and p['body']['origin']['project'] == b['project'] and p['body']['origin']['domain'] == b['domain']]
                    + [dict(type='mapping', id=p['id'], title=' / '.join(c['concept']['title'] for c in p['concepts']) + (' · ' + p['relation'] if p['type'] == 'mapping' else ' · share'))
                       for p in project['proposals'] if p['status'] == 'proposed' and any(c['domain'] == b['domain'] for c in p['concepts'])])

    def _facilitator(self, store, actor):
        if actor not in self.roles(store)['semantic_services']:
            raise PermissionError('Only Semantic services facilitates sessions.')

    def create_session(self, actor, memberships, data):
        title = txt(data, 'title', 120, True)
        when = txt(data, 'when', 60, False)
        if data.get('project') not in memberships:
            raise PermissionError('You do not have access to this project.')
        project = self._project(data['project'])
        domain = project['domains'].get(data.get('domain'))
        if not domain:
            raise ValueError('Choose a team in this project.')
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    self._facilitator(store, actor)
                    ref = store.put('ESESSION-' + uuid4().hex[:12], 'enterprise-session', ENTERPRISE,
                                    dict(title=title, when=when, status='open', facilitator=actor, project=project['id'], project_title=project['title'],
                                         domain=domain['key'], domain_label=domain['label'], items=[], actor=actor, at=now()))
            finally:
                store.close()
        return dict(message='Session created. Add what the team needs to agree.', ref=asdict(ref))

    def save_session(self, actor, data):
        """Replace the agenda. The facilitator orders items, adds notes and marks topics discussed; linked items take their state from the proposal."""
        raw = data.get('items')
        if not isinstance(raw, list) or len(raw) > 12:
            raise ValueError('Keep up to twelve agenda items.')
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    self._facilitator(store, actor)
                    record = self._open(store, data, 'enterprise-session')
                    body = record['body']
                    if body['status'] != 'open':
                        raise ValueError('This session is closed.')
                    project = self._project(body['project'])
                    reach = {p['ref'].id: p['body'] for p in self._latest(store, 'enterprise-proposal')}
                    local = {p['id']: p for p in project['proposals']}
                    known = {i['id']: i for i in body['items']}
                    items, seen = [], set()
                    for item in raw:
                        if not isinstance(item, dict):
                            raise ValueError('Provide each agenda item.')
                        item_id = item.get('id') if item.get('id') in known else 'ITEM-' + uuid4().hex[:8]
                        link = item.get('link')
                        clean = dict(id=item_id, title=txt(item, 'title', 160, True), note=txt(item, 'note', 1000, False), discussed=False)
                        if link:
                            if not isinstance(link, dict) or link.get('type') not in {'reach', 'mapping'} or (link['type'], link.get('id')) in seen:
                                raise ValueError('Link each proposal once.')
                            if link['type'] == 'reach':
                                p = reach.get(link.get('id'))
                                ok = p and p['origin']['project'] == body['project'] and p['origin']['domain'] == body['domain']
                            else:
                                p = local.get(link.get('id'))
                                ok = p and any(c['domain'] == body['domain'] for c in p['concepts'])
                            if not ok:
                                raise ValueError('Link a proposal that belongs to this team.')
                            seen.add((link['type'], link['id']))
                            clean['link'] = dict(type=link['type'], id=link['id'])
                        else:
                            clean['discussed'] = item.get('discussed') is True
                        items.append(clean)
                    body.update(items=items, actor=actor, at=now())
                    ref = store.put(record['ref'].id, 'enterprise-session', ENTERPRISE, body, record['ref'].revision)
            finally:
                store.close()
        return dict(message='Agenda saved.', ref=asdict(ref))

    def close_session(self, actor, data):
        summary = txt(data, 'summary', 2000, True)
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    self._facilitator(store, actor)
                    record = self._open(store, data, 'enterprise-session')
                    body = record['body']
                    if body['status'] != 'open':
                        raise ValueError('This session is already closed.')
                    body.update(status='closed', summary=summary, actor=actor, at=now())
                    ref = store.put(record['ref'].id, 'enterprise-session', ENTERPRISE, body, record['ref'].revision)
            finally:
                store.close()
        return dict(message='Session closed. Its agenda and summary are kept.', ref=asdict(ref))

    # ---- writing
    def save_roles(self, actor, admin, data):
        if not admin:
            raise PermissionError('Only an administrator can assign enterprise roles.')
        roles = data.get('roles')
        if not isinstance(roles, dict) or set(roles) != set(ROLE_NAMES):
            raise ValueError('Assign both enterprise roles.')
        clean = {}
        for key in ROLE_NAMES:
            people = roles[key]
            if not isinstance(people, list) or len(set(people)) != len(people) or any(p not in PERSONAS for p in people):
                raise ValueError('Choose each person once from the people on this site.')
            clean[key] = sorted(people)
        if set(clean['semantic_services']) & set(clean['stewards']):
            raise ValueError('Semantic services proposes and never decides. Nobody can hold both roles.')
        reason = txt(data, 'reason', 1000, True)
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    previous = self._roles(store)
                    expected = asdict(previous['ref']) if previous else None
                    if data.get('expected') != expected:
                        raise StaleBasis('Enterprise roles changed. Reopen them before saving.')
                    ref = store.put(ROLES, 'enterprise-roles', ENTERPRISE, dict(roles=clean, actor=actor, at=now(), reason=reason, previous=expected),
                                    previous['ref'].revision if previous else 0)
            finally:
                store.close()
        return dict(message='Enterprise roles saved.', ref=asdict(ref))

    def propose(self, actor, memberships, data):
        origin = data.get('origin') or {}
        reach = data.get('reach')
        if reach not in WIDE:
            raise ValueError('Choose named domains or enterprise.')
        named = data.get('named') or []
        if not isinstance(named, list) or len(named) > 8 or any(not isinstance(n, str) or not n.strip() or len(n) > 80 for n in named):
            raise ValueError('Name up to eight domains.')
        named = [n.strip() for n in named] if reach == 'named-domains' else []
        if reach == 'named-domains' and not named:
            raise ValueError('Name the domains this meaning should reach.')
        reason = txt(data, 'reason', 1000, True)
        if origin.get('project') not in memberships:
            raise PermissionError('You do not have access to this project.')
        project = self._project(origin['project'])
        entry = self._concept(project, origin.get('domain'), origin.get('entry'))
        domain = project['domains'][origin['domain']]
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    roles = self.roles(store)
                    if actor not in roles['semantic_services'] and actor not in domain['leaders']:
                        raise PermissionError('Only Semantic services or this team’s lead can propose wider reach.')
                    key = (origin['project'], origin['domain'], origin['entry'])
                    if any(p['body']['status'] == 'proposed' and (p['body']['origin']['project'], p['body']['origin']['domain'], p['body']['origin']['entry']) == key
                           for p in self._latest(store, 'enterprise-proposal')):
                        raise ValueError('A proposal for this concept is already open.')
                    view = concept_view(entry)
                    body = dict(status='proposed', reach=reach, named=named, reason=reason, proposed_by=actor, at=now(), decisions={},
                                origin=dict(project=project['id'], project_title=project['title'], domain=origin['domain'], domain_label=domain['label'],
                                            entry=entry['id'], knowledge=domain['knowledge']),
                                concept=view, fingerprint=fingerprint(view))
                    ref = store.put('EPROPOSAL-' + uuid4().hex[:12], 'enterprise-proposal', ENTERPRISE, body)
            finally:
                store.close()
        return dict(message='Proposed. The team lead and an enterprise steward both decide.', ref=asdict(ref))

    def _open(self, store, data, kind):
        raw = data.get('ref') or {}
        record = store.latest(str(raw.get('id', '')), {ENTERPRISE})
        if record['kind'] != kind:
            raise ValueError('Choose an enterprise record.')
        if asdict(record['ref']) != raw:
            raise StaleBasis('This changed. Reopen it before acting.')
        return record

    def decide(self, actor, memberships, data):
        outcome = data.get('outcome')
        if outcome not in {'approve', 'decline'}:
            raise ValueError('Approve or decline.')
        reason = txt(data, 'reason', 1000, True)
        if data.get('confirm') is not True:
            raise ValueError('Explicitly confirm your decision.')
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    record = self._open(store, data, 'enterprise-proposal')
                    body = record['body']
                    if body['status'] != 'proposed':
                        raise ValueError('This proposal is already closed.')
                    roles = self.roles(store)
                    if actor in roles['semantic_services']:
                        raise PermissionError('Semantic services proposes and facilitates. It does not decide.')
                    project = self._project(body['origin']['project'])
                    leaders = project['domains'].get(body['origin']['domain'], {}).get('leaders', [])
                    capacity = None
                    if 'lead' not in body['decisions'] and actor in leaders and project['id'] in memberships:
                        capacity = 'lead'
                    elif 'steward' not in body['decisions'] and actor in roles['stewards'] and body['decisions'].get('lead', {}).get('actor') != actor:
                        capacity = 'steward'
                    if not capacity:
                        raise PermissionError('The team lead and an enterprise steward decide this, as two different people.')
                    if outcome == 'approve' and self._changed(body, project):
                        raise StaleBasis('The concept changed since this was proposed. Decline or withdraw it and propose again.')
                    body['decisions'][capacity] = dict(actor=actor, outcome=outcome, reason=reason, at=now())
                    message = 'Your approval is recorded. Waiting on the other decision.'
                    if outcome == 'decline':
                        body.update(status='declined', closed=dict(actor=actor, at=now(), reason=reason))
                        message = 'Declined. The proposal is kept.'
                    elif all(body['decisions'].get(c, {}).get('outcome') == 'approve' for c in CAPACITIES):
                        body.update(status='approved', closed=dict(actor=actor, at=now(), reason=reason))
                        key = (body['origin']['project'], body['origin']['domain'], body['origin']['entry'])
                        existing = next((c for c in self._latest(store, 'enterprise-concept')
                                         if (c['body']['origin']['project'], c['body']['origin']['domain'], c['body']['origin']['entry']) == key), None)
                        concept = dict({k: body['concept'][k] for k in ('kind', 'title', 'definition', 'includes', 'excludes', 'not_confused_with')},
                                       reach=body['reach'], named=body['named'], origin=body['origin'], status='active', at=now(),
                                       approved=dict(lead=body['decisions']['lead']['actor'], steward=body['decisions']['steward']['actor']),
                                       proposal=dict(id=record['ref'].id, revision=record['ref'].revision + 1),
                                       previous=asdict(existing['ref']) if existing else None)
                        cref = store.put(existing['ref'].id if existing else 'ECONCEPT-' + uuid4().hex[:12], 'enterprise-concept', ENTERPRISE, concept,
                                         existing['ref'].revision if existing else 0)
                        body['result'] = asdict(cref)
                        message = 'Approved. The concept now has wider reach, at this exact wording.'
                    ref = store.put(record['ref'].id, 'enterprise-proposal', ENTERPRISE, body, record['ref'].revision)
            finally:
                store.close()
        return dict(message=message, ref=asdict(ref))

    def close(self, actor, data):
        """Withdraw an open proposal (its proposer) or retire an enterprise concept (a steward)."""
        reason = txt(data, 'reason', 1000, True)
        with self.lock:
            store = Store(self.path)
            try:
                with store.transaction():
                    raw = data.get('ref') or {}
                    record = store.latest(str(raw.get('id', '')), {ENTERPRISE})
                    if asdict(record['ref']) != raw:
                        raise StaleBasis('This changed. Reopen it before acting.')
                    body = record['body']
                    if record['kind'] == 'enterprise-proposal':
                        if body['status'] != 'proposed':
                            raise ValueError('This proposal is already closed.')
                        if body['proposed_by'] != actor:
                            raise PermissionError('Only the person who proposed this can withdraw it.')
                        body.update(status='withdrawn', closed=dict(actor=actor, at=now(), reason=reason))
                        message = 'Withdrawn.'
                    elif record['kind'] == 'enterprise-concept':
                        if body['status'] != 'active':
                            raise ValueError('This concept is already retired.')
                        if actor not in self.roles(store)['stewards']:
                            raise PermissionError('Only an enterprise steward can retire an enterprise concept.')
                        body.update(status='retired', retired=dict(actor=actor, at=now(), reason=reason), previous=asdict(record['ref']))
                        message = 'Retired. Its reach returns to what the team set; the record is kept.'
                    else:
                        raise ValueError('Choose an enterprise proposal or concept.')
                    ref = store.put(record['ref'].id, record['kind'], ENTERPRISE, body, record['ref'].revision)
            finally:
                store.close()
        return dict(message=message, ref=asdict(ref))
