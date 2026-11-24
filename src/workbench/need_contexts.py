"""Situated claims in the existing store; packets select exact versions of them.

This bounded first slice uses already shared evidence only. Private findings still
cross through the existing domain publication/release, never through this service.
"""
from dataclasses import asdict
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .validation import reference, required

KIND = 'need-context'
DIMENSIONS = ('people', 'job', 'situation', 'triggers', 'pains', 'gains', 'boundaries', 'dependencies')
RELATIONS = {'supports', 'challenges', 'refines', 'depends-on', 'constrains', 'measures', 'decision-needed'}
KNOWLEDGE_STATES = {'source-stated', 'interpretation', 'proposal', 'unknown'}
LINK_KINDS = {'intent', 'project-context', 'requirement', 'goal', 'success-measure', 'policy',
              'contribution', 'source', 'intake-source', 'evidence', 'bridge-issue', 'decision-case', 'decision'}
EVIDENCE_KINDS = {'source', 'intake-source', 'evidence', 'contribution'}
RULE = '''SITUATED RESEARCH CONTEXT: Keep a consequential claim connected to the specific
actor, job, situation/triggers, pains, gains, boundaries and dependencies that give
it meaning. Do not combine different actors or situations into an unsupported
composite. Tie each supported detail to exact evidence; distinguish source-stated
content, interpretation, proposal and unknown. A quote establishes what the source
says, not prevalence, causality or approval. Retain counterevidence and limitations.
Relationships need a type, rationale and applicable conditions; co-occurrence or
similar vocabulary does not establish dependency. Preserve active and historical
bases separately. Use only relevant permitted records. New findings can challenge
intent or propose requirements/criteria; humans decide consequential changes.'''


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values(): yield from strings(item)
    elif isinstance(value, list):
        for item in value: yield from strings(item)


def bounded(data, key, limit=2400):
    value = required(data, key)
    if len(value) > limit: raise ValueError('Shorten '+key)
    return value


class NeedContexts:
    def __init__(self, workspace):
        self.w, self.store = workspace, workspace.store

    def author(self):
        if self.w.actor != 'priya' and not self.w.domains.key:
            raise PermissionError('Use the sponsor or an assigned domain author to propose situated context')

    def shared(self, raw, kinds):
        record = self.store.read(reference(raw), {SCOPE})
        if record['kind'] not in kinds: raise ValueError('Choose a permitted shared evidence or project record')
        return record

    def save(self, data):
        self.author()
        if data.get('confirm_shared') is not True:
            raise ValueError('Confirm sharing this proposed context with project participants')
        with self.store.transaction():
            previous = None
            if data.get('expected'):
                previous = self.shared(data['expected'], {KIND})
                if previous['body']['owner'] != self.w.actor: raise PermissionError('Only its author may revise this context')
                if self.store.latest(previous['ref'].id, {SCOPE})['ref'] != previous['ref']:
                    raise StaleBasis('Reopen the current context before editing')
            evidence = data.get('evidence', [])
            links = data.get('links', [])
            if not isinstance(evidence, list) or not 1 <= len(evidence) <= 12:
                raise ValueError('Provide 1–12 exact evidence passages')
            if not isinstance(links, list) or not 1 <= len(links) <= 24:
                raise ValueError('Provide 1–24 explicit relationships')
            checked_evidence = []
            for index, item in enumerate(evidence):
                record = self.shared(item.get('ref'), EVIDENCE_KINDS)
                quote = bounded(item, 'quote', 2000)
                if not any(quote in text for text in strings(record['body'])):
                    raise ValueError('The quoted evidence was not found in its exact source version')
                checked_evidence.append(dict(id='E'+str(index+1), ref=asdict(record['ref']), quote=quote,
                                             use=self.use(item), rationale=bounded(item, 'rationale', 800)))
            checked_links = []
            for item in links:
                record = self.shared(item.get('ref'), LINK_KINDS)
                if item.get('relation') not in RELATIONS: raise ValueError('Choose an explicit relationship type')
                checked_links.append(dict(ref=asdict(record['ref']), relation=item['relation'],
                    rationale=bounded(item, 'rationale', 800), conditions=bounded(item, 'conditions', 800), use=self.use(item)))
            dimensions = data.get('dimensions', {})
            if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
                raise ValueError('Keep all situation dimensions; mark missing knowledge as unknown')
            checked_dimensions = {}
            for key in DIMENSIONS:
                item = dimensions[key]
                if not isinstance(item, dict) or item.get('state') not in KNOWLEDGE_STATES:
                    raise ValueError('Distinguish supported content, interpretation, proposal and unknown')
                ids = item.get('evidence_ids', [])
                if not isinstance(ids, list) or any(i not in {e['id'] for e in checked_evidence} for i in ids):
                    raise ValueError('Link each detail to evidence in this context')
                if item['state'] == 'source-stated' and not ids:
                    raise ValueError('A source-stated detail needs evidence')
                checked_dimensions[key] = dict(text=bounded(item, 'text'), state=item['state'], evidence_ids=sorted(set(ids)))
            review_items=self.review_items(data.get('review_items', []), checked_evidence)
            body = dict(title=bounded(data, 'title', 160), claim=bounded(data, 'claim'),
                limitation=bounded(data, 'limitation'), rationale=bounded(data, 'rationale'),
                dimensions=checked_dimensions, evidence=checked_evidence, links=checked_links,
                status='proposed-for-review', owner=self.w.actor, domain=self.w.domains.key or 'business',
                at=now(), previous=asdict(previous['ref']) if previous else None)
            if review_items:body['review_items']=review_items
            if previous:
                body['change_summary']=bounded(data,'change_summary') if data.get('change_summary') else body['rationale']
                body['changed_fields']=[key for key in ('claim', 'limitation', *DIMENSIONS)
                    if (previous['body']['dimensions'][key] if key in DIMENSIONS else previous['body'].get(key)) != (body['dimensions'][key] if key in DIMENSIONS else body.get(key))]
            if data.get('example'):
                if data['example']!='fictional-follow-up':raise ValueError('Unknown demonstration label')
                body['example']='fictional-follow-up'
            # Active assertions must have one current version per identity. Historical
            # alternatives are retained without turning an old issue snapshot into a gate.
            refs = self.active_references(body)
            self.fresh(refs)
            result = self.store.put(previous['ref'].id if previous else 'NEED-'+uuid4().hex[:12], KIND, SCOPE,
                                    body, previous['ref'].revision if previous else 0)
            for ref in refs: self.store.depend(result, ref, {SCOPE})
        return dict(id=result.id, ref=asdict(result), message='Situated context shared as a proposal. Requirements and approvals are unchanged.')

    def review_items(self, values, evidence):
        if not isinstance(values,list) or len(values)>6:raise ValueError('Choose at most six focused reconsideration items')
        result=[];seen=set();allowed_ids={e['id'] for e in evidence if e['use']=='active'}
        for item in values:
            target=self.shared(item.get('target'), {'requirement','project-design-brief'})
            if self.store.latest(target['ref'].id,{SCOPE})['ref']!=target['ref']:raise StaleBasis('Review the current target before proposing changes')
            field=item.get('field')
            if (target['kind']=='requirement' and field not in {'text','acceptance_criteria'}) or (target['kind']=='project-design-brief' and field!='objectives'):
                raise ValueError('Choose requirement wording, acceptance criteria or published brief objectives')
            key=(target['ref'].id,field)
            if key in seen:raise ValueError('Combine duplicate proposals for the same target field')
            seen.add(key);ids=item.get('evidence_ids',[])
            if not isinstance(ids,list) or not ids or any(v not in allowed_ids for v in ids):raise ValueError('Each proposed change needs active evidence in this context')
            b=target['body']
            current='\n'.join(o.get('title','') for o in b.get('objectives',[])) if field=='objectives' else b.get(field,'')
            result.append(dict(target=asdict(target['ref']),field=field,title=b.get('title') or ('Working brief objectives' if field=='objectives' else target['ref'].id),
                current_text=current,proposed_text=bounded(item,'proposed_text',1600),rationale=bounded(item,'rationale',800),evidence_ids=sorted(set(ids)),status='reconsideration-needed'))
        return result

    @staticmethod
    def use(item):
        if item.get('use') not in {'active', 'historical'}: raise ValueError('Mark each reference active or historical')
        return item['use']

    @staticmethod
    def active_references(body):
        refs = sorted({reference(item['ref']) for item in body['evidence']+body['links'] if item['use']=='active'})
        if len({r.id for r in refs}) != len(refs): raise ValueError('Choose one active version per identity')
        return refs

    def fresh(self, refs):
        for ref in refs:
            if self.store.latest(ref.id, {SCOPE})['ref'] != ref:
                raise StaleBasis('Situated context or its active evidence changed. Review its current meaning before preparing a new commitment.')

    def related(self, refs):
        ids = {reference(r).id if isinstance(r, dict) else r.id for r in refs}
        result = [r for r in self.w.latest_records(KIND)
                  if any(x['ref']['id'] in ids for x in r['body']['links'])]
        if len(result) > 8: raise ValueError('Narrow the selected work; more than eight related situations were found')
        return result

    def basis(self, records, *, history=False, require_current=False):
        refs = set()
        for record in records:
            active = self.active_references(record['body'])
            if require_current: self.fresh([record['ref'], *active])
            refs.update([record['ref'], *active])
            if history:
                refs.update(reference(i['ref']) for i in record['body']['evidence']+record['body']['links'])
                if record['body'].get('previous'):refs.add(reference(record['body']['previous']))
                refs.update(reference(item['target']) for item in record['body'].get('review_items',[]))
        return sorted(refs)

    def selected_basis(self, raw):
        if not isinstance(raw, list) or len(raw)>8: raise ValueError('Choose at most eight exact situations')
        return self.basis([self.shared(r, {KIND}) for r in raw], require_current=True)

    def for_plan(self, plan):
        pinned = [self.shared(raw, {KIND}) for raw in plan['body'].get('basis', [])
                  if self.store.read(reference(raw), self.w.scopes)['kind']==KIND]
        reqs = plan['body'].get('design_inputs', {}).get('requirements', [])
        refs = [r['ref'] for r in reqs] or [raw for raw in plan['body'].get('basis', [])
                                           if self.store.read(reference(raw), self.w.scopes)['kind']=='requirement']
        current = self.related(refs)
        return dict(included=[asdict(r['ref']) for r in pinned],
                    to_review=[asdict(r['ref']) for r in current if r['ref'] not in {p['ref'] for p in pinned}])

    def packet(self, data):
        self.author()
        with self.store.transaction():
            record = self.shared(data.get('expected'), {KIND})
            if record['body']['owner'] != self.w.actor: raise PermissionError('Only the context author prepares its review packet')
            purpose = bounded(data, 'purpose', 600)
            refs = self.basis([record], history=True, require_current=True)
            packet_id = 'PKT-NEED-'+uuid4().hex[:12];revision=1
            if data.get('previous_packet'):
                prior=reference(data['previous_packet'])
                packet=self.store.read_packet(prior.id,prior.revision,{SCOPE})
                if not prior.id.startswith('PKT-NEED-') or set(packet['audience_scopes'])!={SCOPE}:
                    raise ValueError('Choose an existing situated-context review packet')
                contexts=[self.store.read(reference(r),{SCOPE}) for r in packet['refs'] if self.store.read(reference(r),{SCOPE})['kind']==KIND]
                if not contexts or any(r['ref'].id!=record['ref'].id or r['body']['owner']!=self.w.actor for r in contexts):
                    raise PermissionError('The prior packet belongs to a different situation or author')
                if record['ref'].revision<=max(r['ref'].revision for r in contexts):raise ValueError('Choose a later version of the same context')
                latest=self.store.db.execute('SELECT MAX(revision) FROM packets WHERE id=?',(prior.id,)).fetchone()[0]
                if latest!=prior.revision:raise StaleBasis('A later packet version exists; reopen its latest manifest')
                packet_id=prior.id;revision=prior.revision+1
            self.store.packet(packet_id, revision, purpose, refs, {SCOPE}, {SCOPE})
        return dict(packet=dict(id=packet_id, revision=revision), message='Review packet prepared from exact shared records. No requirement or decision was changed.')
