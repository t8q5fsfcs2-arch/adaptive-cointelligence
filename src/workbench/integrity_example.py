"""Synthetic executable guide example. Does not open or modify a real project.

Run: python -m workbench.integrity_example --output /tmp/integrity-example
Optional --live uses an explicitly configured environment model with synthetic
context only; it is a smoke test, not an expert-reviewed semantic benchmark.
"""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4
import argparse
import json

from .core import Store, Ref
from .decisions import SCOPE
from .workspace import Workspace


def raw(ref): return asdict(ref)


class Fixture:
    def __init__(self,path=':memory:'):
        self.store=Store(path)
        from .decision_rights import DEFAULTS
        self.w('administrator',admin=True).rights.save(dict(expected=None,rules=deepcopy(DEFAULTS),reason='Named authority for this synthetic worked case.'))
        self.anchor=self.store.put('QUALIFICATION','requirement',SCOPE,dict(title='Qualification validity',
            text='Only personnel with valid qualification at work execution may perform the assigned task.',
            status='approved',conditions='Qualification remains valid at execution.',acceptance_criteria='Enforce qualification for every task execution.',
            rationale='Only currently qualified personnel perform work.',owner='alex'))
        self.rule=self.declare(['execution'])
        self.a=self.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'])
        self.b=self.expression('lee','design','Operations','Validate qualification immediately before execution.',['execution'])

    def w(self,actor,model=None,admin=False): return Workspace(self.store,actor,model,admin=admin)

    def declare(self,timing):
        existing=self.w('alex').integrity.records('integrity-conditions')
        return self.w('alex').integrity.declare(dict(requirement=raw(self.anchor),expected=raw(existing[-1]['ref']) if existing else None,
            rationale='Human owner declares the source timing condition for the synthetic fixture.',
            conditions=[dict(key='qualification_check_at',operator='includes',expected=timing,
                citations=[dict(id=self.anchor.id,revision=self.anchor.revision,field='text',quote=self.store.read(self.anchor,{SCOPE})['body']['text'])])] if timing else []))['ref']

    def expression(self,actor,domain,label,text,at,covered=False,workable=True,previous=None,source=None):
        if source is None:
            source=self.store.put('SOURCE-'+actor,'contribution',SCOPE,dict(title=label,text=text,owner=actor,
                domain='Research' if actor=='sam' else 'Design',source='Synthetic exercise, not operational policy.',
                limitation='Illustrative author assertions; not independently verified.',status='published-for-review'))
        cite=dict(id=source.id,revision=source.revision,field='text',quote=text)
        facts=dict(qualification_check_at=dict(value=at,citations=[cite]),locally_workable=dict(value=workable,citations=[cite]))
        if covered: facts['coverage_and_enforcement']=dict(value=True,citations=[cite])
        return self.w(actor).integrity.expression(dict(source=raw(source),domain=domain,label=label,
            requirements=[raw(self.anchor)],facts=facts,expected=previous))

    def assessment(self,packets=None,associations=None,actor='alex',mode='formal',semantic=False,model=None):
        ps=packets or [self.a['packet'],self.b['packet']]
        proposal=None
        if len(ps)>1 and mode=='formal':
            proposal=self.w('alex').integrity.proposal(dict(packets=ps,text='Retain assignment checks and establish execution-time enforcement, with evidence of coverage.',rationale='Preserve the approved qualification condition.'))['ref']
        return self.w(actor,model).integrity.assess(dict(proposal=proposal,packets=ps,associations=associations or [],evaluation_scope='within-domain' if len(ps)==1 else 'cross-domain',
            mode=mode,confirm=mode=='formal',semantic=semantic,consent=semantic))

    def association(self):
        return self.w('alex').integrity.associate(dict(packets=[self.a['packet'],self.b['packet']],relation='implements',
            matching_basis='shared-requirement-id',approve=True,rationale='Same exact requirement; complementary checks are still subject to evaluation.'))['ref']

    def review(self,ref): return self.store.read(Ref(**ref),{SCOPE})

    def issue(self,assessment):
        w=self.w('alex')
        created=w.bridge.create(dict(title='Qualification timing integrity',question='Do these domain checks preserve execution-time qualification?',
            consequence='A person may lose qualification after assignment.',kind='conflict',boards=['research-design'],owner='sam',route='requirement',
            target=raw(self.anchor),packet_refs=[self.a['packet'],self.b['packet']],requirement_refs=[raw(self.anchor)]))
        issue=self.store.latest(created['id'],{SCOPE})
        w.integrity.attach(dict(expected=raw(issue['ref']),assessment=assessment))
        return created['id']

    def current(self,id): return self.store.latest(id,{SCOPE})

    def local_approvals(self):
        for actor,e in [('sam',self.a),('lee',self.b)]:
            a=self.assessment([e['packet']],actor=actor)['ref']
            body=self.review(a)['body']
            self.w(actor).integrity.approve_domain(dict(assessment=a,disposition='approved-with-limits' if any(f['material'] for f in body['findings']) else 'approved',rationale='Local approval retains the explicit limits, not a compliance certificate.'))

    def resolved(self):
        self.a=self.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=self.a['ref'],source=Ref('SOURCE-sam',1))
        self.b=self.expression('lee','design','Operations','Validate qualification immediately before execution.',['execution'],True,previous=self.b['ref'],source=Ref('SOURCE-lee',1))
        mapping=self.association();self.local_approvals()
        a=self.assessment(associations=[mapping])['ref'];issue=self.issue(a)
        for actor in ['sam','lee']:
            self.w(actor).integrity.reconcile(dict(expected=raw(self.current(issue)['ref']),clear=True,rationale='Review the two declared checks together; maintain the evidence limits.'))
        return issue,a,mapping

    def close(self,id):
        return self.w('alex').bridge.close(dict(expected=raw(self.current(id)['ref']),confirm=True,
            rationale='Ratify this bounded interpretation only; governing requirement and source limitations remain unchanged.'))

    def change_anchor(self,text):
        """Use existing named-reviewer/owner decisions, never direct fixture overwrites."""
        p=self.store.packet('GOV-'+uuid4().hex[:8],1,'Authorized governing change',[self.anchor],{SCOPE},{SCOPE})
        loop=self.w('alex').loop
        case=loop.propose('alex',self.anchor,p['id'],1,text,'Confirm the newly authorized condition.','Effective at the recorded human decision.',[self.anchor])
        for actor,clearance in loop.case(case.id)['body']['required_reviews'].items():
            self.w(actor).loop.review(actor,loop.case(case.id)['ref'],clearance,'Reviewed this exact deliberate change of governing timing.')
        result=loop.decide('alex',loop.case(case.id)['ref'],'approve','Explicit synthetic amendment; earlier approvals and requirement versions are retained.')
        self.anchor=Ref(**result['requirement'])
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--live',action='store_true',help='Send only synthetic fixture context to an environment-configured model.')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    db=args.output/'worked-case.sqlite3'
    if db.exists(): raise SystemExit('Choose a new output directory; existing demo data is preserved.')
    f=Fixture(db);trace={}
    try:
        f.store.put('PROJECT-001','project',SCOPE,dict(title='AI partner — synthetic qualification case'))
        original=f.anchor
        local=f.assessment([f.a['packet']],actor='sam')['ref'];trace['local_assignment_check']=f.review(local)
        mapping=f.association();initial=f.assessment(associations=[mapping])['ref'];f.local_approvals()
        issue=f.issue(initial);trace['initial_review']=f.w('alex').integrity.decision_view(f.current(issue))
        for finding in f.review(initial)['body']['findings']:
            if finding['material']:
                f.w('alex').integrity.dispose(dict(expected=raw(f.current(issue)['ref']),finding=finding['key'],disposition='investigate-and-defer',rationale='Establish coverage and execution-time enforcement before reuse.'))
        f.a=f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=f.a['ref'],source=Ref('SOURCE-sam',1))
        f.b=f.expression('lee','design','Operations','Validate qualification immediately before execution.',['execution'],True,previous=f.b['ref'],source=Ref('SOURCE-lee',1))
        revised=f.assessment(associations=[f.association()])['ref'];f.local_approvals()
        for finding in f.review(initial)['body']['findings']:
            if finding['material']:
                f.w('alex').integrity.dispose(dict(expected=raw(f.current(issue)['ref']),finding=finding['key'],disposition='accept-and-address',resolution_assessment=revised,rationale='Current author-declared coverage evidence addresses the selected gap; the synthetic evidence limitations remain.'))
        f.w('alex').bridge.refresh(dict(expected=raw(f.current(issue)['ref']),packet_refs=[f.a['packet'],f.b['packet']],requirement_refs=[raw(f.anchor)],target=raw(f.anchor),note='Review the revised domain-expression versions.'))
        f.w('alex').integrity.attach(dict(expected=raw(f.current(issue)['ref']),assessment=revised))
        trace['decision_point']=f.w('alex').integrity.decision_view(f.current(issue))
        for actor in ['sam','lee']: f.w(actor).integrity.reconcile(dict(expected=raw(f.current(issue)['ref']),clear=True,rationale='Named reviewer reconciles the exact declared check coverage with its source limits.'))
        f.close(issue);trace['ratification']=f.current(issue)
        trace['reuse']=f.w('alex').integrity.promote(dict(expected=raw(f.current(issue)['ref'])))
        trace['reuse_again']=f.w('alex').integrity.promote(dict(expected=raw(f.current(issue)['ref'])))
        trace['governing_change']=f.change_anchor('Only personnel with valid qualification at assignment may perform the assigned task.')
        trace['impact']=f.w('alex').integrity.impact(raw(original),raw(f.anchor));f.declare(['assignment'])
        f.a=f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=f.a['ref'],source=Ref('SOURCE-sam',1))
        trace['assignment_anchor']=f.review(f.assessment([f.a['packet']],actor='sam')['ref'])
        f.change_anchor('Only qualified personnel may perform the assigned task.');f.declare([])
        f.a=f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=f.a['ref'],source=Ref('SOURCE-sam',1))
        trace['timing_removed']=f.review(f.assessment([f.a['packet']],actor='sam')['ref'])
        trace['conditions']='Synthetic owner-declared condition tests; not independent semantic or compliance validation.'
        if args.live:
            from .model_provider import load_model
            model=load_model()
            if not model.status().get('configured'): trace['live_evaluation']=dict(status='not-run',reason='No environment model configured; no simulated result substituted.')
            else:
                try: trace['live_evaluation']=f.assessment([f.a['packet']],actor='sam',semantic=True,model=model)
                except Exception as e: trace['live_evaluation']=dict(status='failed',error_type=type(e).__name__)
        else: trace['live_evaluation']=dict(status='not-run',reason='No --live request; no external call.')
        output=args.output/'worked-case.json';output.write_text(json.dumps(trace,default=lambda v:asdict(v) if isinstance(v,Ref) else str(v),indent=2))
        print(json.dumps(dict(database=str(db),trace=str(output),issue=issue,local_fidelity='not-preserved at execution',revised='bounded interpretation ratified',drift=['assignment anchor changes result','missing timing remains unresolved'],semantic=trace['live_evaluation']['status'] if 'status' in trace['live_evaluation'] else 'evaluated'),indent=2))
    finally: f.store.close()


if __name__=='__main__': main()
