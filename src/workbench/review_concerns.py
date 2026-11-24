"""Explicit private review-to-issue handoff. No model calls or governing changes."""
from dataclasses import asdict
from copy import deepcopy
from uuid import uuid4
from .core import StaleBasis
from .decisions import SCOPE, fingerprint, now
from .validation import reference
from .bridge import text
from .assessment_context import shared_assessment_records

BOUNDARY = 'A flagged concern, not validated evidence, requirement approval or execution authority.'


class ReviewConcerns:
    def __init__(self, workspace):
        self.w, self.store, self.actor = workspace, workspace.store, workspace.actor
        self.scope = 'coach:' + self.actor

    def prepare(self, data):
        with self.store.transaction():
            return self._prepare(data)

    def assessment_context(self, req, intended_use=None):
        """Resolve the selected shared judgment without grading or changing it."""
        service = self.w.requirement_assessments
        item = service.read({'requirement': asdict(req['ref'])})
        if intended_use is not None and intended_use not in item['uses']:
            raise ValueError('Choose investigation, a bounded prototype, or implementation')
        if intended_use is None:
            intended_use = next((r['body'].get('intended_use') for r in item['history']
                                 if r['body'].get('intended_use') in item['uses']), None)
        selected = item['uses'].get(intended_use, {})
        assessment = selected.get('current')
        inventory = item.get('inventory')
        if assessment and assessment['body'].get('access_limited'):
            raise PermissionError('The selected assessment basis is unavailable for sharing')
        if assessment:
            inventory = self.store.read(reference(assessment['body']['inventory']), {SCOPE})
            inventory_ref = asdict(inventory['ref'])
            standard_ref = assessment['body']['standard']
        elif inventory:
            if inventory['body'].get('access_limited'):
                raise PermissionError('The selected material checks are unavailable for sharing')
            inventory_ref, standard_ref = inventory['ref'], inventory['body']['standard']
        else:
            return [], None
        refs = [reference(inventory_ref), reference(standard_ref)]
        if assessment:
            refs.append(reference(assessment['ref']))
        return refs, dict(intended_use=intended_use, assessment=assessment['ref'] if assessment else None,
            inventory=inventory_ref, standard=standard_ref, status=selected.get('status', 'not-assessed'),
            confidence=selected.get('confidence', {}).get('level', 'not-rated'),
            boundary='Recorded assessment context, not a new judgment or approval.')

    def shared_context(self, refs, req):
        return shared_assessment_records(self.w, refs, req['ref'])

    def _prepare(self, data):
        self.w.bridge.author()
        req = self.store.read(reference(data.get('requirement')), {SCOPE})
        if req['kind'] != 'requirement' or self.store.latest(req['ref'].id, {SCOPE})['ref'] != req['ref']:
            raise StaleBasis('Reopen the current published requirement before carrying this concern.')
        field = data.get('field', 'text')
        from .field_coach import GUIDANCE
        if field not in GUIDANCE['groups']['requirement']:
            raise ValueError('Choose a published requirement field.')
        # A handoff assembles saved references, not a model request. Large public
        # intent/scaffold bodies must not inherit the model-context size limit.
        refs = [req['ref']]
        for key in ('goal_refs','measure_refs'):
            for raw in req['body'].get(key, []):
                linked = self.store.read(reference(raw), {SCOPE})
                if linked['kind'] not in {'goal','success-measure'}:
                    raise ValueError('Choose valid published outcome links.')
                refs.append(linked['ref'])
        for identity in ('INT-001','POL-001'):
            if self.store.db.execute('SELECT 1 FROM records WHERE id=? AND scope=?',(identity,SCOPE)).fetchone():
                refs.append(self.store.latest(identity,{SCOPE})['ref'])
        assessment_refs, assessment_context = self.assessment_context(req, data.get('intended_use'))
        advice = None; excerpt = None
        if data.get('advice'):
            advice = self.store.read(reference(data['advice']), {self.scope})
            b = advice['body']
            if advice['kind'] != 'field-coach-advice' or b.get('actor') != self.actor or asdict(req['ref']) not in b.get('basis', []):
                raise ValueError('Choose your saved review of this exact published requirement.')
            refs = [reference(r) for r in b['basis']]
            excerpt = {k: b['output'].get(k, '') for k in ('assessment', 'why_it_matters', 'next_question', 'suggested_wording')}
        records = self.shared_context([*refs, *assessment_refs], req)
        observed = [asdict(self.store.latest(r['ref'].id, {SCOPE})['ref']) for r in records]
        question = text(data, 'question', 1200, required=False)
        body = dict(requirement=asdict(req['ref']), field=field, basis=[asdict(r['ref']) for r in records], observed=observed,
                    source_review=asdict(advice['ref']) if advice else None, review_excerpt=excerpt, user_question=question,
                    assessment_context=assessment_context,
                    assessment_selection_use=data.get('intended_use') or (assessment_context or {}).get('intended_use'),
                    historical_context=any(r['ref'] != reference(current) for r,current in zip(records,observed)),
                    actor=self.actor, at=now(), boundary=BOUNDARY)
        with self.store.transaction():
            ref = self.store.put('REVIEW-HANDOFF-'+uuid4().hex[:12], 'review-concern-draft', self.scope, body)
        return dict(ref=asdict(ref), requirement_record=req, context=records, **body,
                    title=('Review concern: '+(req['body'].get('title') or req['ref'].id))[:200],
                    question=question or (excerpt or {}).get('next_question') or (excerpt or {}).get('assessment',''),
                    consequence=(excerpt or {}).get('why_it_matters',''))

    def publish(self, data):
        self.w.bridge.author()
        if data.get('confirm') is not True:
            raise ValueError('Confirm sharing this concern, the shown review excerpt and its published context.')
        expected = reference(data.get('expected'))
        with self.store.transaction():
            draft = self.store.read(expected, {self.scope})
            if draft['kind'] != 'review-concern-draft' or draft['body'].get('actor') != self.actor:
                raise PermissionError('Use your own prepared review concern.')
            b = draft['body']; supplied = {k: deepcopy(data.get(k)) for k in ('title','question','consequence','boards','kind','owner','route')}
            signature = fingerprint(supplied)
            latest = self.store.latest(expected.id, {self.scope})
            if latest['body'].get('published_issue'):
                if latest['body'].get('publication_signature') != signature:
                    raise StaleBasis('This concern was already shared. Respond on its issue instead.')
                return dict(id=latest['body']['published_issue'], message='This concern is already in Decisions & Issues.')
            if latest['ref'] != expected:
                raise StaleBasis('This prepared concern changed. Reopen it before sharing.')
            if self.store.latest(b['requirement']['id'], {SCOPE})['ref'] != reference(b['requirement']):
                raise StaleBasis('The requirement changed. Your prepared concern remains saved; reopen the current version before sharing.')
            for raw, observed in zip(b['basis'], b['observed']):
                if self.store.latest(raw['id'], {SCOPE})['ref'] != reference(observed):
                    raise StaleBasis('The review context changed after preparation. Your concern remains saved; review the current context before sharing.')
            if 'assessment_selection_use' in b:
                req = self.store.read(reference(b['requirement']), {SCOPE})
                _, current_assessment = self.assessment_context(req, b['assessment_selection_use'])
                if current_assessment != b.get('assessment_context'):
                    raise StaleBasis('The selected assessment changed after preparation. Your concern remains saved; review the current assessment before sharing.')
            # Validate all edited issue fields before creating any shared records.
            title=text(data,'title',200); question=text(data,'question'); consequence=text(data,'consequence')
            payload=dict(text=question, title=title, consequence=consequence, requirement=b['requirement'], field=b['field'],
                         context_refs=b['basis'], source_review=b['source_review'], review_excerpt=b['review_excerpt'],
                         user_question=b['user_question'], historical_context=b['historical_context'], actor=self.actor, at=now(),
                         assessment_context=deepcopy(b.get('assessment_context')),
                         boundary=BOUNDARY, evidence_status='not-validated')
            concern=self.store.put('CONCERN-'+uuid4().hex[:12], 'review-concern', SCOPE, payload)
            for raw in b['basis']:self.store.depend(concern, reference(raw), {SCOPE})
            packet=self.store.packet('PKT-'+concern.id,1,'Flagged review concern and exact published context',
                                     [concern,*[reference(r) for r in b['basis']]],{SCOPE},{SCOPE})
            result=self.w.bridge.create({**supplied,'title':title,'question':question,'consequence':consequence,
                                         'target':b['requirement'],'requirement_refs':[b['requirement']],
                                         'packet_refs':[dict(id=packet['id'],revision=packet['revision'])]})
            self.store.put(expected.id, draft['kind'], self.scope, {**b,'published_issue':result['id'],
                           'publication_signature':signature,'shared_concern':asdict(concern)}, expected.revision)
        return dict(id=result['id'], message='Concern carried into Decisions & Issues. Published requirements are unchanged.')
