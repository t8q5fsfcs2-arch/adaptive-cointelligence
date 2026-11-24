#!/usr/bin/env python3
"""Paired synthetic smoke comparison, never an independent expert-quality grade.

Example: PYTHONPATH=src python scripts/evaluate_integrity.py --output /tmp/eval.json
Add --live --model-settings /path/to/local/settings.json --project PROJECT_ID to
call an existing assigned provider. Credentials never enter results or fixtures.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
from time import monotonic

from workbench.integrity_example import Fixture
from workbench.core import Ref
from workbench.integrity import schema, INSTRUCTIONS, model_context
from workbench.model_connection import ModelConnections

BASELINE='Compare these exact source requirements and domain expressions. Explain consequential differences, cite sources, identify missing evidence and recommend a response. Return the requested structured output. You cannot approve anything.'
CASES=[
    dict(id='execution',timing=['execution'],anchor='Only personnel with valid qualification at work execution may perform the assigned task.',
         expectation='Assignment alone is insufficient for execution. The two checks may be complementary, conditional on coverage and enforcement.'),
    dict(id='assignment',timing=['assignment'],anchor='Only personnel with valid qualification at assignment may perform the assigned task.',
         expectation='Assignment is now the governing timing; do not persist the previous execution-time obligation. Combined check coverage still needs evidence.'),
    dict(id='unspecified',timing=[],anchor='Only qualified personnel may perform the assigned task.',
         expectation='Timing is not specified; identify uncertainty rather than invent an assignment or execution obligation.')]


def run_case(spec,arm,model):
    f=Fixture();started=monotonic()
    try:
        if spec['id']!='execution':
            f.change_anchor(spec['anchor']);f.declare(spec['timing'])
            for actor,domain,key,text,at in [('sam','research','a','Validate qualification when assigning the task.',['assignment']),('lee','design','b','Validate qualification immediately before execution.',['execution'])]:
                old=getattr(f,key)
                setattr(f,key,f.expression(actor,domain,'Scheduling' if actor=='sam' else 'Operations',text,at,previous=old['ref'],source=Ref('SOURCE-'+actor,1)))
        mapping=f.association()
        proposal=f.w('alex').integrity.proposal(dict(packets=[f.a['packet'],f.b['packet']],text='Retain assignment checks and establish any needed execution enforcement.',rationale='Preserve the exact governing condition, with evidence.'))['ref']
        ctx=f.w('alex').integrity.assemble(dict(packets=[f.a['packet'],f.b['packet']],associations=[mapping],proposal=proposal,evaluation_scope='cross-domain',mode='formal'))
        checks=f.w('alex').integrity.checks(ctx)
        prompt=INSTRUCTIONS if arm=='structured' else BASELINE
        supplied=dict(model_context(ctx),deterministic_findings=checks[0]) if arm=='structured' else dict(skill='integrity-review',citation_catalog=ctx['citation_catalog'],records=[r for r in ctx['records'] if r['kind'] in {'requirement','contribution'}],proposal=next(r for r in ctx['records'] if r['ref']==proposal))
        result=dict(case=spec['id'],arm=arm,expectation=spec['expectation'],input_characters=len(json.dumps(supplied)),independent_expert_review='pending',quality_grade=None)
        if model is None: return dict(result,status='not-run',reason='No explicit --live request. No simulated result substituted.')
        try:
            response=model.generate(instructions=prompt,context=supplied,schema=schema(ctx))
            output=response.get('output');validated=f.w('alex').integrity.validate_model(output,ctx)
            result.update(status='returned',output=output,citations_valid=True,validated_findings=validated,
                model=response.get('model'),usage={k:v for k,v in response.get('usage',{}).items() if type(v) in (int,float)})
        except Exception as exc:
            result.update(status='failed',failure_type=type(exc).__name__,failure_message=str(exc) if type(exc).__name__ in {'ModelUnavailable','ValueError'} else 'Assessment failed.',citations_valid=None)
        return dict(result,latency_seconds=round(monotonic()-started,3))
    finally: f.store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--live',action='store_true');parser.add_argument('--model-settings',type=Path);parser.add_argument('--project')
    args=parser.parse_args();model=None
    if args.live:
        if not args.model_settings or not args.project: parser.error('Live evaluation requires an existing settings path and assigned project ID.')
        model=ModelConnections(args.model_settings).select([args.project])
        if not model.status().get('configured'): parser.error('No model is assigned; no substitute will run.')
    jobs=[(c,a) for c in CASES for a in ['baseline','structured']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(lambda job:run_case(job[0],job[1],model),jobs))
    result=dict(fixture_count=3,attempts=6,repeat_count=1,fixture_basis='Three exact worked-case variations supplied in the implementation guide.',
        model=model.status() if model else None,results=rows,
        measurements=dict(returned=sum(r['status']=='returned' for r in rows),failed=sum(r['status']=='failed' for r in rows),
            citation_valid_returns=sum(r.get('citations_valid') is True for r in rows),semantic_detection_rate=None,missed_violations=None,false_alarms=None,
            unsupported_equivalence=None,appropriate_abstention=None,reviewer_effort_seconds=None),
        limits='Smoke comparison only, not an expert-reviewed held-out benchmark. Citation existence is measured, not evidential support or semantic quality. No optimality claim.')
    args.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(output=str(args.output),measurements=result['measurements'])))


if __name__=='__main__': main()
