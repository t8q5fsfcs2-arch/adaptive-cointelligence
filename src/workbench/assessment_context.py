"""Read-only, exact shared assessment receipts for handoffs and delivery drafts.

This projects recorded judgments. It neither grades a claim nor grants authority.
Private intake analysis is deliberately outside this shared traversal.
"""
from copy import deepcopy
from dataclasses import asdict

from .core import Ref
from .decisions import SCOPE, fingerprint
from .validation import reference
from .requirement_assessments import SOURCE_KINDS, standard_ref

BOUNDARY = ('Recorded assessment context only; confidence, suitability, ratification, '
            'execution authority and delivered fulfillment remain separate.')


def _ref(raw):
    return raw if isinstance(raw, Ref) else reference(raw)


def shared_assessment_records(workspace, refs, requirement=None):
    """Validate a bounded explicit assessment graph, never arbitrary dependencies."""
    store = workspace.store
    service = workspace.requirement_assessments
    pending = [(_ref(raw), False) for raw in refs]
    records = {}
    base = {'requirement', 'goal', 'success-measure', 'intent', 'policy',
            'requirement-assessment', 'requirement-condition-inventory',
            'requirement-assessment-standard', 'business-assessment-release',
            'evidence-reasoning-standard'}
    while pending:
        ref, linked = pending.pop()
        if ref in records:
            continue
        if len(records) >= 512:
            raise ValueError('Select a narrower assessment context')
        row = store.read(ref, {SCOPE})
        kind, body = row['kind'], row['body']
        if kind not in base and (not linked or kind not in SOURCE_KINDS):
            raise ValueError('Only exact published assessment context can be carried')
        links = []
        if kind in {'requirement-assessment', 'requirement-condition-inventory'}:
            target = reference(body.get('requirement'))
            if requirement is not None and target.id != _ref(requirement).id:
                raise ValueError('The assessment must concern the selected requirement')
            links += [target, reference(body['standard'])]
            if kind == 'requirement-assessment':
                inventory = store.read(reference(body['inventory']), {SCOPE})
                if (inventory['kind'] != 'requirement-condition-inventory' or
                        inventory['body'].get('requirement') != body['requirement'] or
                        inventory['body'].get('standard') != body['standard']):
                    raise ValueError('Retain the exact assessment inventory and standard')
                links.append(inventory['ref'])
                for judgment in body['condition_judgments'] + body['use_judgments']:
                    links += [reference(raw) for raw in judgment.get('dependencies', [])]
                    for citation in judgment.get('evidence', []):
                        links.append(reference(service._citation(citation, level=True)['ref']))
            else:
                for condition in body['material_conditions']:
                    citation = service._citation(condition['source'])
                    if reference(citation['ref']) != target:
                        raise ValueError('Retain the exact requirement clause')
                    links += [reference(raw) for raw in condition.get('dependencies', [])]
        elif kind in {'requirement-assessment-standard', 'evidence-reasoning-standard'}:
            if body.get('id') != ref.id or body.get('revision') != ref.revision:
                raise ValueError('The standard snapshot does not match its exact reference')
        elif kind in {'intent', 'requirement'}:
            release = body.get('business_assessment')
            if release:
                released = store.read(reference(release['ref']), {SCOPE})
                if released['kind'] != 'business-assessment-release':
                    raise ValueError('Use an explicitly released Business Intent assessment')
                links.append(released['ref'])
        elif kind == 'business-assessment-release':
            if reference(body.get('assessment_ref')) != ref:
                raise ValueError('The released assessment receipt must identify itself')
            standard = body.get('standard', {})
            saved_standard = store.read(reference(standard.get('ref')), {SCOPE})
            if saved_standard['kind'] != 'evidence-reasoning-standard' or saved_standard['body'] != standard.get('body'):
                raise ValueError('Retain the exact shared evidence and reasoning standard')
            links.append(saved_standard['ref'])
            sources = {reference(raw) for raw in body.get('sources', [])}
            for source_ref in sources:
                source = store.read(source_ref, {SCOPE})
                if source['kind'] not in {'source', 'evidence'}:
                    raise ValueError('Released evidence must be an explicit shared source')
            def citations(value):
                if isinstance(value, dict):
                    if 'source_ref' in value and 'passage_id' in value:
                        cited = reference(value['source_ref'])
                        if cited not in sources:
                            raise ValueError('The assessment cites an unreleased source')
                        text = store.read(cited, {SCOPE})['body'].get('text', '')
                        start, end = value.get('start'), value.get('end')
                        if (type(start) is not int or type(end) is not int or start < 0 or
                                end <= start or text[start:end] != value.get('quote')):
                            raise ValueError('The released quote does not match its exact source')
                    else:
                        for child in value.values(): citations(child)
                elif isinstance(value, list):
                    for child in value: citations(child)
            # Original private publication basis is metadata, never a shared edge.
            citations(body.get('assessment', {}))
            citations(body.get('inventory', {}))
            links += list(sources)
        records[ref] = row
        pending += [(raw, True) for raw in links]
    return [records[ref] for ref in sorted(records)]


def assessment_context(workspace, requirements=(), intent=None):
    """Project scoped current judgments and keep original intent separate.

Historical requirements never borrow the latest requirement's assessment.
No records, scores or defaults are created by this function.
"""
    store = workspace.store
    service = workspace.requirement_assessments
    refs, traces = set(), []
    def retain(raw):
        if raw:
            refs.add(_ref(raw))
    def release_trace(raw):
        records = shared_assessment_records(workspace, [raw])
        record = store.read(_ref(raw), {SCOPE})
        if record['kind'] != 'business-assessment-release':
            raise ValueError('Use an explicitly released Business Intent assessment')
        for row in records: retain(row['ref'])
        body = record['body']
        from .business_assessments import standard as business_standard, standard_ref as business_standard_ref
        configured_standard = business_standard()
        return dict(ref=asdict(record['ref']), standard=deepcopy(body.get('standard')),
            inventory=deepcopy(body.get('inventory')), assessment=deepcopy(body.get('assessment')),
            assessor=deepcopy(body.get('assessor')), assessed_at=body.get('assessed_at'),
            sources=deepcopy(body.get('sources', [])),
            current_standard=business_standard_ref(configured_standard),
            standard_current=body['standard']['ref']==business_standard_ref(configured_standard) and
                             body['standard']['body']==configured_standard)
    def intent_trace(raw):
        row = store.read(_ref(raw), {SCOPE})
        if row['kind'] != 'intent':
            raise ValueError('Choose an exact published Business Intent')
        retain(row['ref'])
        release = row['body'].get('business_assessment')
        out = dict(intent=asdict(row['ref']), current=store.latest(row['ref'].id, {SCOPE})['ref'] == row['ref'],
                   assessment=None, limitation='No shared Business Intent assessment is recorded for this version.')
        if release:
            out.update(assessment=release_trace(release['ref']),
                limitation='This Business Intent assessment is not a requirement grade or execution authority.')
        return out
    if intent is None:
        if store.db.execute('SELECT 1 FROM records WHERE id=? AND kind=? AND scope=?', ('INT-001', 'intent', SCOPE)).fetchone():
            intent = store.latest('INT-001', {SCOPE})['ref']
    current_intent = intent_trace(intent) if intent else None
    for raw in requirements:
        req = store.read(_ref(raw), {SCOPE})
        if req['kind'] != 'requirement':
            raise ValueError('Choose exact published requirements')
        retain(req['ref'])
        current = store.latest(req['ref'].id, {SCOPE})['ref'] == req['ref']
        original = service.business_intent_basis(req['body'].get('intake_case'))
        original_intent = intent_trace(original['published_intent_ref']) if original and original.get('published_intent_ref') else None
        original_assessment = req['body'].get('business_assessment')
        original_claim_links = deepcopy(original_assessment.get('claim_links', [])) if original_assessment else []
        if not original_assessment and req['body'].get('intake_case'):
            case = store.read(reference(req['body']['intake_case']), {SCOPE})
            if case['kind'] != 'intake-case':
                raise ValueError('Use the requirement’s exact published intake case')
            original_assessment = case['body'].get('snapshot', {}).get('business_assessment')
        original_assessment = release_trace(original_assessment['ref']) if original_assessment else None
        if original:
            retain(original.get('case_ref'))
            for review in original.get('reviews', []): retain(review['ref'])
        item = service.read({'requirement': asdict(req['ref'])}) if current else None
        uses = {}
        inventory = item.get('inventory') if item else None
        if inventory and not inventory['body'].get('access_limited'):
            retain(inventory['ref'])
        for use, value in (item['uses'].items() if item else []):
            selected = value.get('current')
            limited = bool(selected and selected['body'].get('access_limited'))
            basis = []
            if selected and not limited:
                records = shared_assessment_records(workspace, [selected['ref']], req['ref'])
                basis = [asdict(record['ref']) for record in records]
                for record in records: retain(record['ref'])
            gaps = [dict(key=result['key'], kind=kind, status=result['status'],
                         rationale=result.get('rationale', ''), stale=deepcopy(result.get('stale', [])))
                    for kind, results in [('material', value['condition_results']), ('intended-use', value['use_results'])]
                    for result in results if result['status'] not in {'met', 'not-applicable'} or result.get('stale')]
            uses[use] = dict(status=value['status'], confidence=deepcopy(value['confidence']),
                assessment=selected['ref'] if selected and not limited else None,
                inventory=selected['body'].get('inventory') if selected and not limited else inventory['ref'] if inventory and not inventory['body'].get('access_limited') else None,
                standard=selected['body'].get('standard') if selected and not limited else inventory['body'].get('standard') if inventory and not inventory['body'].get('access_limited') else None,
                basis=basis, gaps=gaps, stale=deepcopy(value['stale']),
                limits=selected['body'].get('confidence', {}).get('limits', '') if selected and not limited else '',
                access_limited=limited)
        traces.append(dict(requirement=asdict(req['ref']), current=current,
            inventory=inventory['ref'] if inventory and not inventory['body'].get('access_limited') else None,
            standard=standard_ref(), uses=uses, coverage=deepcopy(item['coverage']) if item else None,
            original_business_intent=original_intent, original_intake_basis=original,
            original_business_assessment=original_assessment, business_claim_links=original_claim_links,
            limitation=None if current else 'Historical requirement; no assessment from a later requirement version is supplied.'))
    # Inventory-only context must retain its source clause and durable standard too.
    if refs:
        inventory_refs = [ref for ref in refs if store.read(ref, {SCOPE})['kind'] == 'requirement-condition-inventory']
        for row in shared_assessment_records(workspace, inventory_refs): retain(row['ref'])
    return dict(requirements=traces, current_business_intent=current_intent,
                basis=[asdict(ref) for ref in sorted(refs)],
                basis_currentness=[dict(ref=asdict(ref), current=asdict(store.latest(ref.id, {SCOPE})['ref']))
                                   for ref in sorted(refs)], boundary=BOUNDARY)


def context_changes(workspace, saved):
    """Report changed exact evidence or new judgments, including absent→recorded."""
    requirements = [value['requirement'] for value in saved.get('requirements', [])]
    intent = saved.get('current_business_intent')
    if intent:
        intent = workspace.store.latest(intent['intent']['id'], {SCOPE})['ref']
    fresh = assessment_context(workspace, requirements, intent)
    return [] if fingerprint(fresh) == fingerprint(saved) else [dict(
        reason='The recorded assessment, evidence, standard or Business Intent basis changed.',
        previous_basis=deepcopy(saved.get('basis', [])), current_basis=fresh['basis'])]
