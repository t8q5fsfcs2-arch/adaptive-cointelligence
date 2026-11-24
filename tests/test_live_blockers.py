"""Regressions for observed live request failures; synthetic transport only."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from workbench import integrity_options as io,project_implications as pi,decision_context
from workbench.integrity import model_context
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import synthetic_output
from workbench.model_provider import OpenAIModel

class LiveBlockerTests(unittest.TestCase):
    def test_required_coverage_is_structural_and_normalization_preserves_judgments(self):
        f=Fixture();self.addCleanup(f.store.close);service=f.w('alex').integrity
        ctx=service.assemble(dict(packets=[f.a['packet']],mode='advisory',evaluation_scope='within-domain'))
        canonical=synthetic_output(model_context(ctx),phase='investigate')['decision']
        for o in canonical['obligations']:
            for e in o['elements'].values():
                if e['status']=='specified':e['quote']=next(p for p in io.clause_passages(io.context(ctx)['clauses'][o['clause_ref']]['quote']) if e['quote'] in p)
        from workbench.integrity_parts import parent
        for f in canonical['packet_findings']:f.update(parent(f['parts'],io.context(ctx)['material_parts']))
        wire=deepcopy(canonical)
        wire['obligations']={o['clause_ref']:dict(elements={k:(None if e['status']=='unspecified' else e) for k,e in o['elements'].items()}) for o in canonical['obligations']}
        slots=io.packet_slots(ctx)
        wire['packet_findings']={slot:dict(parts={p['part_ref']:{k:v for k,v in p.items() if k not in ('part_ref','evidence_refs')} for p in next(x for x in canonical['packet_findings'] if all(x[k]==v for k,v in pair.items()))['parts']}) for slot,pair in slots.items()}
        from workbench.integrity_parts import quote_catalog
        choices=quote_catalog(ctx,io.context(ctx))
        for f in wire['packet_findings'].values():
            for p in f['parts'].values():p['evidence_quotes']=[next(k for k,v in choices.items() if all(v[a]==b for a,b in q.items())) for q in p['evidence_quotes']]
        io.shape(wire,io.wire_schema(ctx));decoded=io.normalize_wire(wire,ctx)
        order=lambda f:(f['packet_ref'],f['obligation_ref'])
        decoded['packet_findings']=sorted(decoded['packet_findings'],key=order)
        canonical['packet_findings']=sorted(canonical['packet_findings'],key=order)
        self.assertEqual(decoded,canonical)
        missing=deepcopy(wire);missing['obligations'].pop(next(iter(missing['obligations'])))
        with self.assertRaises(ValueError):io.shape(missing,io.wire_schema(ctx))
        bad=deepcopy(wire);first=next(iter(bad['obligations'].values()))
        first['elements']['threshold']=dict(status='unspecified',quote='',interpretation='99 percent')
        with self.assertRaises(ValueError):io.shape(bad,io.wire_schema(ctx))
        bad=deepcopy(wire);next(iter(bad['packet_findings'].values()))['status']='supported'
        with self.assertRaises(ValueError):io.shape(bad,io.wire_schema(ctx))

    def test_bounded_pipeline_preserves_every_mapping_and_stops_on_invalid_evidence(self):
        from workbench import integrity_pipeline as pipeline
        from workbench.integrity import citation_catalog
        f=Fixture();self.addCleanup(f.store.close);service=f.w('alex').integrity
        ctx=service.assemble(dict(packets=[f.a['packet']],mode='advisory',evaluation_scope='within-domain'))
        anchor=next(r for r in ctx['records'] if r['kind']=='requirement')
        for n in range(2):
            extra=deepcopy(anchor);extra['ref']['id']='EXTRA-'+str(n)
            ctx['records'].append(extra);ctx['requirements'].append(extra['ref'])
        for r in ctx['records']:
            if r['kind']=='integrity-expression':r['body']['requirements']=ctx['requirements']
        ctx['citation_catalog']=citation_catalog(ctx)
        class Model:
            def __init__(self,bad=False):self.calls=[];self.bad=bad
            def generate(self,**kw):
                self.calls.append(kw);out=synthetic_output(kw['context'],phase='investigate')
                if kw['context']['assessment_phase']=='clause-mapping':
                    out={k:out['decision'][k] for k in ('obligations','packet_findings')}
                    out['applicability']={k:dict(status='shared',rationale='Explicit synthetic equivalence judgment for copied governing records.',occurrences={x['clause_ref']:dict(status='same-meaning',rationale='This synthetic parent has the identical applicable meaning.') for x in v['occurrences']}) for k,v in kw['context']['governing_targets'].items()}
                    if self.bad:out['obligations'][0]['elements']['action']=dict(status='specified',quote='fabricated quote',interpretation='fabricated')
                else:
                    for k in ('obligations','packet_findings'):out['decision'].pop(k)
                return dict(output=out,model='synthetic',response_id=str(len(self.calls)),usage=dict(input_tokens=10,output_tokens=5,total_tokens=15))
        model=Model();response=pipeline.generate(service,model,ctx)
        self.assertEqual(len(model.calls),2);self.assertEqual(len(response['output']['decision']['obligations']),9)
        self.assertEqual(response['usage']['total_tokens'],30);self.assertEqual(len(response['phase_receipts']),2)
        self.assertTrue(all(len(t['occurrences'])==3 for t in model.calls[0]['context']['governing_targets'].values()))
        self.assertEqual(len(model.calls[-1]['context']['current_governing_requirements']),3)
        bad=Model(True)
        with self.assertRaises(ValueError):pipeline.generate(service,bad,ctx)
        self.assertEqual(len(bad.calls),1)

    def test_owner_projection_preserves_governing_words_and_located_source_evidence(self):
        requirement=dict(ref=dict(id='R',revision=2),kind='requirement',body=dict(text='At execution '+('x'*5000),conditions='No exception',acceptance_criteria='A recorded event',status='proposed',owner='alex'))
        source=dict(ref=dict(id='S',revision=1),kind='source',body=dict(title='Interview',text='a'*3000+'Relevant exact quote.'+'b'*3000))
        need=dict(ref=dict(id='N',revision=1),kind='need-context',body=dict(claim='Bounded inference',dimensions=dict(actor='Supervisor',job='Follow up',situation='Shift handoff'),evidence=[dict(ref=source['ref'],quote='Relevant exact quote.')]))
        records=[requirement,source,need];before=deepcopy(records)
        projected,manifest,selected=decision_context.project(records)
        self.assertEqual(projected[0]['body'],requirement['body']);self.assertEqual(records,before)
        self.assertEqual(projected[2]['body'],need['body']);self.assertEqual(len(projected[1]['body']['text']),2000)
        self.assertTrue(manifest['omitted']);self.assertEqual(selected[0]['quote'],'Relevant exact quote.')

    def test_research_contract_binds_parent_criterion_and_evidence_strength(self):
        ctx=dict(requirements=[dict(ref=dict(id='R',revision=1),kind='requirement',body=dict(acceptance_criteria='A specific event'))],goals_and_measures=[dict(ref=dict(id='G',revision=1),kind='goal',body={})],evidence_passages=[dict(id='EV1',source='S:v1',quote='Exact evidence',page=None)])
        p=dict(kind='refine-requirement',title='Refine',statement='Candidate wording',rationale='Evidence needs a precise event',requirement_basis='IB2',targets=['G:v1'],support=dict(assessment='limited',basis='One interview',scope='One shift',corroboration='None',counterevidence='Unknown',gaps=['Operational data absent']),evidence=[dict(passage='EV1')])
        io.shape([p],pi.wire_schema(ctx));decoded=pi.normalize_wire([p],ctx)[0]
        self.assertEqual(decoded['targets'],['R:v1','G:v1']);self.assertEqual(decoded['criterion'],'A specific event')
        bad=deepcopy(p);bad['support'].update(assessment='substantive',gaps=[]);bad['evidence']=[]
        with self.assertRaises(ValueError):io.shape([bad],pi.wire_schema(ctx))
        bad=deepcopy(p);bad.pop('requirement_basis');bad.update(kind='new-criterion',criterion='',targets=['G:v1'])
        with self.assertRaises(ValueError):io.shape([bad],pi.wire_schema(ctx))

    def test_budget_tracks_explicit_contract_without_changing_other_tasks(self):
        model=OpenAIModel('not-a-key','gpt-5-mini')
        self.assertEqual(model.request_settings(dict(skill='integrity-review'))['max_output_tokens'],6000)
        settings=model.request_settings(dict(skill='integrity-review',option_contract=dict(clauses={str(i):{} for i in range(21)},required_packet_findings={str(i):{} for i in range(21)})))
        self.assertGreater(settings['max_output_tokens'],6000);self.assertLessEqual(settings['max_output_tokens'],24000)
        self.assertEqual(model.request_settings(dict(skill='coach-field'))['max_output_tokens'],8000)

    def test_empty_plan_is_canonical_empty_without_a_provider_generation_task(self):
        from workbench.domain_submission import SubmissionAgent,wire_schema
        ctx=dict(requirements=[],goals_and_measures=[],evidence_passages=[],brief_evaluation=dict(sections=[]))
        contract=wire_schema(ctx)
        self.assertNotIn('plan_review',contract['properties']);self.assertNotIn('objective_review',contract['properties'])
        class Model:
            def generate(self,**kw):return dict(output=dict(summary='No submitted evidence establishes performance.',implications=[],limitations=['No evidence supplied.']))
        result=SubmissionAgent(Model(),dict(config=dict(persona_id='P-test'))).run(ctx)
        self.assertEqual(result['output']['plan_review'],[]);self.assertEqual(result['output']['objective_review'],[])

    def test_clause_selection_preserves_numeric_thresholds_and_exact_source(self):
        text='Return within 3.5 seconds. Preserve the exact source; never substitute an inferred event.'
        passages=io.clause_passages(text)
        self.assertEqual(passages[0],'Return within 3.5 seconds.')
        self.assertTrue(all(p in text and len(p)<=500 for p in passages))

    def test_owner_rejects_invented_inline_citation_with_a_valid_citation_array(self):
        from workbench.workspace import Workspace
        f=Fixture();self.addCleanup(f.store.close)
        assessment=f.assessment(associations=[f.association()])['ref'];issue=f.issue(assessment)
        class Model:
            def status(self):return dict(configured=True,provider='synthetic',model='test')
            def generate(self,**kw):return dict(output=dict(reply='Claim supported by C-INVENTED-SOURCE.',citations=list(kw['context']['citation_catalog'])[:1]))
        w=Workspace(f.store,'alex',Model());before=f.current(issue);r=w.decision_review.read(dict(expected=asdict(before['ref'])))
        with self.assertRaisesRegex(ValueError,'citation outside'):
            w.decision_review.send(dict(expected=r['issue'],thread=r['thread'],question='Which evidence matters?',consent=True,request_id='inline-evidence-test'))
        self.assertEqual(f.current(issue),before)
        self.assertEqual(w.decision_review.read(dict(expected=r['issue']))['messages'][0]['status'],'failed')

if __name__=='__main__':unittest.main()
