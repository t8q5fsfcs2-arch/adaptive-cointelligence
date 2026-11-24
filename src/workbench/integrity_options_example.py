"""Explicitly scripted synthetic decision trace. Never a fallback or live evaluator."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import sqlite3

from .integrity_options import ELEMENTS,label


def synthetic_output(ctx,*,phase='ready',preferred=None):
    """Known fixture output for code/interaction tests; no semantic-quality claim."""
    if ctx.get('assessment_phase')=='condition-inventory':
        return dict(parts={k:dict(conditions=[dict(source_ref=k,meaning=v['quote'])],coverage_rationale='Scripted qualification fixture: one condition per supplied source unit.') for k,v in ctx['source_units'].items()},
            applicability={g[0]:dict(status='shared',rationale='Scripted copied contexts have the same meaning.',occurrences={cid:dict(status='same-meaning',rationale='The synthetic fixture declares this occurrence equivalent.') for cid in g}) for g in ctx['candidate_groups']})
    if ctx.get('assessment_phase')=='condition-inventory-review':
        return dict(parts={k:dict(complete=True,faithful=True,rationale='Explicit scripted fixture judgment, not semantic evidence.',omissions=[],source_limitations=[]) for k in ctx['source_units']})
    c=ctx['option_contract'];catalog=ctx['citation_catalog'];clauses=c['clauses'];packets=c['packets'];pids=list(packets)
    root=next(iter(clauses));owner=ctx['required_authority']['decider']
    observations=[k for k,v in catalog.items() if v['field']=='observation']
    expressions={label(e['packet']):e['body'] for e in ctx.get('domain_expressions',[])}
    obligations=[]
    for cid,source in clauses.items():
        elements={k:dict(status='unspecified',quote='',interpretation='') for k in ELEMENTS}
        # This is a scripted example for the known synthetic fixture, not an NLP
        # implementation. Every emitted explicit value must still match its source.
        for key,quote in [('actor','personnel'),('action','perform'),('object','assigned task'),('timing','at work execution')]:
            if quote in source['quote']:elements[key]=dict(status='specified',quote=quote,interpretation=quote)
        if source['field'] in ('conditions','acceptance_criteria'):
            element='condition' if source['field']=='conditions' else 'acceptance_criterion'
            elements[element]=dict(status='specified',quote=source['quote'][:500],interpretation=source['quote'][:500])
        obligations.append(dict(clause_ref=cid,elements=elements))
    pf=[]
    for pid,p in packets.items():
        for cid,source in clauses.items():
            if not any(label(r)==label(source) for r in p['requirements']):continue
            claim=next(k for k,v in catalog.items() if label(v)==label(p['expression']) and v['field']=='expression')
            parts=[dict(part_ref=k,status='supported' if phase=='ready' else 'uncertain',evidence_refs=[claim],
                evidence_quotes=[dict(citation_ref=claim,quote=catalog[claim]['quote'][:600])],
                claim_interpretation=v['quote'],support_scope='Synthetic attributable source statement only; not operational verification.',
                reasoning='Scripted code fixture judgment; not semantic or operational evidence.',remaining_gap='' if phase=='ready' else 'Fixture evidence is unverified.') for k,v in c['material_parts'].items() if v['clause_ref']==cid]
            if ctx.get('frozen_inventory'):
                from .integrity_inventory import LEVELS
                for atom in parts:atom.update(claim_interpretation=c['material_parts'][atom['part_ref']]['meaning'],support_scope=LEVELS[ctx['evidence_level']],
                    evidence_level=ctx['evidence_level'],entailment_check=dict(counterexample_possible=phase!='ready',explanation='Explicit scripted entailment check; no independent semantic validation.'))
            for atom in parts:
                if ctx.get('frozen_inventory'):
                    atom['evidence_relationship']=dict(required_relationship=atom['claim_interpretation'],
                        source_assertion='Scripted source declaration in the selected fixture passage.',
                        relation='full' if phase=='ready' else 'partial',
                        connection='Explicit synthetic relationship; not independently validated semantic evidence.',
                        unstated_premise='',missing_link=atom['remaining_gap'],
                        evidence_request='' if phase=='ready' else 'Inspect the fixture control coverage before accepting it.')
                if (ctx.get('follow_up') or {}).get('judgments'):
                    prior=ctx['follow_up']['judgments'][pid][atom['part_ref']]['judgment']
                    atom['change_review']=dict(outcome='uphold' if prior['status']==atom['status'] else 'revise',
                        reason_type='prior-error',explanation='Explicit scripted reconsideration for application tests only.')
                atom['interpretation']=dict(state='settled',reading=atom['claim_interpretation'],
                    basis='Scripted interpretation for a synthetic code fixture; no semantic validation or human ratification.',
                    alternatives=[],clarification=None)
            pf.append(dict(packet_ref=pid,obligation_ref=cid,status='supported' if phase=='ready' else 'uncertain',parts=parts,
                evidence_refs=[cid,next(k for k,v in catalog.items() if label(v)==label(p['expression']) and v['field']=='expression')],reasoning='Scripted fixture: inspect the exact author declaration and its evidence limits.' if phase=='ready' else 'The proposed check has not yet been demonstrated to cover and enforce this obligation.',material=False))
    def option(id,kind,action,retained,*,support='uncertain',implementation='unknown',conditions=None):
        return dict(id=id,kind=kind,action=action,owner=owner,retained_packets=retained,proposed_conditions=conditions or [],
            implementation=implementation,evidence_refs=[root,*observations[:2]],support=support,hard_gate='passes',
            comparison=dict(fidelity='Preserve the selected current governing condition.',evidence='Fixture evidence only; author claims are not independent verification.',
                workability='Local walkthrough assertions retain their stated limitations; confirm joint enforcement.',risk_and_change='Retain useful existing controls; investigate gaps before changing a requirement.',
                effort_and_cost='Implementation cost and reviewer effort are not measured; do not assume a cheapest option.'),
            dependencies=[],uncertainties=[])
    if phase=='ready':
        options=[option('A','retain','Retain the selected controls within their documented scope for the named human review.',pids,support='supported',implementation='reported-existing')]
        rec=preferred or 'A';conditions=[]
    else:
        # Explicit proposed values describe an implementation target only.
        targets=[dict(rule=k,value=v['expected']) for k,v in c['declared_rules'].items()]
        options=[option('A','add-control','Retain useful assignment checks and verify or implement enforcement of the current governing condition.',pids,implementation='proposed',conditions=targets)]
        assignment=[p for p,e in expressions.items() if e['facts'].get('qualification_check_at',{}).get('value')==['assignment']]
        options[0]['comparison']['fidelity']='Proposes the current required condition as a control target; does not yet demonstrate it.'
        options[0]['comparison']['workability']='Depends on identifying a feasible owner, coverage and enforcement mechanism.'
        if assignment:options.append(option('B','retain','Rely only on the assignment-check contribution.',assignment,support='supported',implementation='reported-existing'))
        if assignment:
            options[-1]['comparison']['fidelity']='Retains assignment timing only. Its adequacy depends on the actual current anchor; inspect the declared-condition gate below.'
            options[-1]['comparison']['evidence']='The Scheduling packet describes an assignment check; it does not demonstrate maintained validity through execution.'
            options[-1]['comparison']['risk_and_change']='Little design change, but an execution requirement could fail if qualification expires after assignment.'
        options.append(option('C','investigate','Ask the Operations owner to inspect the identified existing control and its accessible execution records before choosing an implementation change.',pids))
        options[-1]['comparison']['fidelity']='Requests evidence against the current governing requirement; makes no claim that it is already satisfied.'
        options[-1]['comparison']['evidence']='A fictional owner identifies an accessible control candidate. Its existence, scope and enforcement still need inspection.'
        options[-1]['comparison']['workability']='Ask the named control owner for the applicable rule, event records, negative cases and coverage limits.'
        options[-1]['dependencies']=['Access to the identified control records and the accountable control owner.']
        rec=preferred or 'C';conditions=['Existing-control coverage and enforcement remain unverified; inspect the identified records before accepting the interpretation.']
    differences=[]
    if len(pids)>1:
        differences=[dict(classification='complementary',packet_refs=pids,obligation_ref=root,
            consequence='Assignment and execution checks may complement each other, but an expired qualification between the two events could violate an execution-time requirement.',
            evidence_refs=[root],would_disprove='Applicable current-source wording or actual control records showing that the proposed scenario cannot occur within the stated scope.',material=False)]
    return dict(summary='Scripted fixture response; not live semantic evidence.',workability='supported-with-limits',findings=[],unresolved=[],decision=dict(
        obligations=obligations,packet_findings=pf,differences=differences,options=options,
        recommendation=dict(preferred_option=rec,why='Investigate accessible existing evidence before selecting an unnecessary implementation change.' if phase!='ready' else 'The fixture has supplied the selected declarations and retained evidence limits for human review.',
            conditions=conditions,would_change_if=['The inspected evidence contradicts the proposed coverage, or an authorized new requirement version changes the governing condition.'],
            requested_decision='Authorize the named investigation; defer acceptance pending its results.' if phase!='ready' else 'The named owner reviews the exact interpretation and required reviewer responses.',disposition='proposed')))


class SimulatedOptionsModel:
    def __init__(self,phase='investigate',preferred=None):self.phase=phase;self.preferred=preferred;self.calls=0
    def status(self):return dict(configured=True,provider='scripted-synthetic',model='integrity-options-fixture')
    def generate(self,*,instructions,context,schema):
        self.calls+=1
        return dict(output=synthetic_output(context,phase=self.phase,preferred=self.preferred),model='scripted-synthetic-fixture',usage={})


def build(output):
    from .integrity_example import Fixture
    from .core import Ref
    from .decisions import SCOPE
    db=output/'options-example.sqlite3'
    if db.exists():raise ValueError('Use a fresh output directory; existing examples are retained.')
    output.mkdir(parents=True,exist_ok=True);f=Fixture(db)
    try:
        f.store.put('PROJECT-001','project',SCOPE,dict(title='AI partner — synthetic options and gates'))
        f.store.put('OPTIONS-EXAMPLE','demo-fixture',SCOPE,dict(synthetic=True,simulated=True))
        hint=f.store.put('CONTROL-LEAD','evidence',SCOPE,dict(observation='The fictional Operations owner identifies an existing start-control candidate and confirms its execution records are accessible for review. Neither the records nor coverage have been inspected.',limitation='Synthetic lead, not proof of enforcement.'))
        old=f.review(f.b['ref'])['body'];facts=deepcopy(old['facts']);facts['existing_control_lead']=dict(value=True,citations=[dict(id=hint.id,revision=1,field='observation',quote=f.store.read(hint,{SCOPE})['body']['observation'])])
        f.b=f.w('lee').integrity.expression(dict(source=old['source'],domain='design',label='Operations',requirements=old['requirements'],facts=facts,expected=f.b['ref']))
        model=SimulatedOptionsModel();local=[]
        for actor,e in [('sam',f.a),('lee',f.b)]:
            a=f.assessment([e['packet']],actor=actor,semantic=True,model=model)['ref'];local.append(a)
            f.w(actor).integrity.approve_domain(dict(assessment=a,disposition='approved-with-limits',rationale='Synthetic local review retains the coverage and evidence limitations.'))
        initial=f.assessment(associations=[f.association()],semantic=True,model=model)['ref'];issue=f.issue(initial)
        f.w('alex').integrity.option_response(dict(expected=asdict(f.current(issue)['ref']),option='C',disposition='accept-next-step',rationale='Inspect the identified accessible records before choosing a control change. This is not ratification.'))
        for finding in f.review(initial)['body']['findings']:
            if finding['material']:f.w('alex').integrity.dispose(dict(expected=asdict(f.current(issue)['ref']),finding=finding['key'],disposition='investigate-and-defer',rationale='Preserve the gap pending the named investigation.'))
        initial_view=f.w('alex').integrity.decision_view(f.current(issue))
        with sqlite3.connect(output/'preview.sqlite3') as preview:
            f.store.db.backup(preview)
        # Append revised source-backed declarations via the existing fixture. This
        # demonstrates workflow mechanics only, not independent evidence grading.
        f.a=f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=f.a['ref'],source=Ref('SOURCE-sam',1))
        f.b=f.expression('lee','design','Operations','Validate qualification immediately before execution.',['execution'],True,previous=f.b['ref'],source=Ref('SOURCE-lee',1))
        initial_staleness=f.w('alex').integrity.freshness(f.review(initial))
        model.phase='ready';f.local_approvals();revised=f.assessment(associations=[f.association()],semantic=True,model=model)['ref']
        f.w('alex').bridge.refresh(dict(expected=asdict(f.current(issue)['ref']),packet_refs=[f.a['packet'],f.b['packet']],requirement_refs=[asdict(f.anchor)],target=asdict(f.anchor),note='Synthetic investigation appended revised declarations; reassess exact affected packets.'))
        f.w('alex').integrity.attach(dict(expected=asdict(f.current(issue)['ref']),assessment=revised))
        for actor in ['sam','lee']:f.w(actor).integrity.reconcile(dict(expected=asdict(f.current(issue)['ref']),clear=True,rationale='Synthetic named review of the revised scope and retained evidence limitations.'))
        f.close(issue)
        reuse=f.w('alex').integrity.promote(dict(expected=asdict(f.current(issue)['ref'])))
        again=f.w('alex').integrity.promote(dict(expected=asdict(f.current(issue)['ref'])))
        result=dict(synthetic=True,model_calls='scripted only; no network',local_assessments=local,initial=initial_view,initial_staleness=initial_staleness,revised=f.w('alex').integrity.decision_view(f.current(issue)),reuse=reuse,reuse_repeated=again,
            semantic_quality='Not measured. Source support judgments in this demonstration are scripted and remain provisional.',database=str(db),issue=issue)
        (output/'trace.json').write_text(json.dumps(result,indent=2,default=asdict))
        return result
    finally:f.store.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();r=build(args.output)
    print(json.dumps(dict(database=r['database'],issue=r['issue'],simulated=True,live_calls=0,trace=str(args.output/'trace.json'))))


if __name__=='__main__':main()
