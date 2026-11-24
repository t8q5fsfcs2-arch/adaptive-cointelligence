"""Project-scoped sponsor setup handoff; no model or automatic approval."""
from dataclasses import asdict
from .core import Ref, StaleBasis
from .decisions import SCOPE, DecisionBlocked, now
from .validation import reference

POLICY = 'sponsor-setup-accountability-v1'
MESSAGE = ('Initial setup has been shared. Propose later changes in Decisions & Issues using a '
           'published Outcomes report, then prepare the sponsor response. Saved draft work is preserved.')


def latest_records(store, kind):
    return [store.read(Ref(r['id'], r['rev']), {SCOPE}) for r in store.db.execute(
        'SELECT id,MAX(revision) rev FROM records WHERE kind=? AND scope=? GROUP BY id ORDER BY MIN(rowid)', (kind, SCOPE))]


def enabled(store):
    try:
        return store.latest('PROJECT-001', {SCOPE})['body'].get('setup_governance') == POLICY
    except PermissionError:
        return False


def baseline(store):
    return next((r for r in latest_records(store, 'intake-case') if r['body'].get('status') == 'published'), None)


def published_report(store, raw):
    try:
        r = store.read(reference(raw), {SCOPE})
        return r if r['kind'] == 'contribution' and store.latest(r['ref'].id, {SCOPE})['ref'] == r['ref'] else None
    except (ValueError, PermissionError, KeyError, TypeError):
        return None


def active_issue(store, draft):
    """A sponsor response must originate in a current, report-backed public issue."""
    selected = {r['id'] for r in (draft or {}).get('refinements', [])}
    for issue in latest_records(store, 'bridge-issue'):
        b = issue['body']; link = b.get('linked') or {}
        if b.get('route') != 'intent' or b.get('status') == 'resolved' or link.get('kind') != 'intent' or link.get('ref', {}).get('id') not in selected:
            continue
        try:
            request = store.latest(link['ref']['id'], {SCOPE})
            rb = request['body']
            if request['kind'] != 'intent-refinement' or rb.get('status') != 'drafted' or rb.get('responded_by') != 'priya':
                continue
            if reference(rb['base_intent']) != store.latest('INT-001', {SCOPE})['ref']:
                continue
            source = published_report(store, rb['source'])
            if not source or asdict(source['ref']) not in b.get('basis', []):
                continue
            return issue
        except (ValueError, PermissionError, KeyError, TypeError):
            continue
    return None


def context(store, draft=None):
    on = enabled(store); first = baseline(store) if on else None
    issue = active_issue(store, draft) if first else None
    editable = not first or issue is not None
    return dict(enabled=on, baseline=asdict(first['ref']) if first else None,
                editable=editable, phase='proposal' if issue else 'shared' if first else 'initial',
                issue=asdict(issue['ref']) if issue else None,
                issue_title=issue['body']['title'] if issue else None,
                message=('Editing a sponsor response to "'+issue['body']['title']+'". Requirements change only after the existing reviews and publication decision.') if issue else MESSAGE if first else 'Prepare the initial setup. Saving a draft does not publish or lock it.')


def require_edit(store, draft):
    c = context(store, draft)
    if c['enabled'] and not c['editable']:
        raise DecisionBlocked(MESSAGE)
    return c


def require_publication(store, draft):
    # Later publications can change goals, measures, scope and category structure.
    return require_edit(store, draft)


def require_requirement_proposal(store, data):
    if not enabled(store) or not baseline(store):
        return
    raw = data.get('expected_issue')
    if not raw:
        raise DecisionBlocked('Start this requirement revision in Decisions & Issues using published Outcomes reports.')
    issue = store.latest(reference(raw).id, {SCOPE})
    b = issue['body']
    if issue['ref'] != reference(raw) or issue['kind'] != 'bridge-issue' or b.get('route') != 'requirement' or b.get('status') == 'resolved' or b.get('target') != data.get('target'):
        raise DecisionBlocked('Use the current Decisions & Issues issue for this requirement.')
    if not any(published_report(store, r) for r in b.get('basis', [])):
        raise DecisionBlocked('Include a published Outcomes report in the issue basis.')


def require_requirement_approval(store, case):
    if not enabled(store) or not baseline(store):
        return
    reports = [r for r in case['body'].get('basis', []) if published_report(store, r)]
    linked = [i for i in latest_records(store, 'bridge-issue') if i['body'].get('status') != 'resolved'
              and (i['body'].get('linked') or {}).get('kind') == 'requirement'
              and i['body'].get('route') == 'requirement'
              and i['body'].get('target') == case['body'].get('target')
              and i['body']['linked']['ref']['id'] == case['ref'].id]
    if not reports or not linked or not any(all(r in i['body'].get('basis', []) for r in reports) for i in linked):
        raise DecisionBlocked('Approval must resolve a Decisions & Issues issue with the selected published Outcomes reports.')


def enable(store, actor, data):
    if actor != 'priya':
        raise PermissionError('Only the business sponsor can enable the setup workflow.')
    if data.get('confirm') is not True:
        raise ValueError('Confirm the sponsor setup workflow.')
    with store.transaction():
        project = store.latest('PROJECT-001', {SCOPE})
        if project['ref'] != reference(data.get('expected')):
            raise StaleBasis('The project changed. Reload it before configuring its workflow.')
        if project['body'].get('setup_governance') == POLICY:
            return dict(message='Sponsor setup workflow is already enabled.', ref=asdict(project['ref']))
        ref = store.put(project['ref'].id, project['kind'], SCOPE,
                        {**project['body'], 'setup_governance': POLICY, 'setup_governance_enabled_at': now()}, project['ref'].revision)
    return dict(message='Sponsor setup workflow enabled. Saved work and shared history are unchanged.', ref=asdict(ref))
