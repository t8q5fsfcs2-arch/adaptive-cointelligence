"""Contract and workflow tests using explicit scripted responses, not semantic evals."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Ref, StaleBasis
from workbench.decisions import DecisionBlocked, SCOPE
from workbench.integrity import model_context
from workbench import integrity_options
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import SimulatedOptionsModel, synthetic_output, build


class IntegrityOptionsTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close)
        self.service=self.f.w('alex').integrity

    def context(self,packets=None):
        ps=packets or [self.f.a['packet'],self.f.b['packet']]
        proposal=self.service.proposal(dict(packets=ps,text='Inspect coverage and enforcement.',rationale='Synthetic test.'))['ref'] if len(ps)>1 else None
        return self.service.assemble(dict(proposal=proposal,packets=ps,mode='formal',evaluation_scope='within-domain' if len(ps)==1 else 'cross-domain'))

    def output(self,ctx,phase='investigate',preferred=None):
        return synthetic_output(model_context(ctx),phase=phase,preferred=preferred)['decision']

    def validate(self,out,ctx):
        return integrity_options.validate(self.service,out,ctx,self.service.checks(ctx)[0])

    def attached(self):
        a=self.f.assessment(associations=[self.f.association()],semantic=True,model=SimulatedOptionsModel())['ref']
        return self.f.issue(a),a

    def test_execution_gates_block_assignment_only_and_preserve_conditional_choice(self):
        ctx=self.context();out,findings=self.validate(self.output(ctx),ctx)
        opts={o['id']:o for o in out['options']}
        self.assertEqual(opts['B']['hard_gate'],'blocked')
        self.assertEqual(opts['A']['hard_gate'],'passes');self.assertTrue(opts['A']['uncertainties'])
        self.assertEqual(out['recommendation']['preferred_option'],'C')
        self.assertFalse(any(o['approval_eligible'] for o in opts.values()))
        self.assertTrue(any(f['key']=='options:recommendation' and f['origin']=='deterministic' for f in findings))

    def test_model_preference_cannot_override_failed_gate_or_supply_display_summary(self):
        a=self.f.assessment(semantic=True,model=SimulatedOptionsModel(preferred='B'))['ref']
        body=self.f.review(a)['body'];rec=body['decision_trace']['recommendation']
        self.assertIsNone(rec['preferred_option']);self.assertEqual(rec['model_preferred_option'],'B')
        self.assertEqual(rec['disposition'],'unresolved');self.assertIn('unresolved',body['summary'])
        self.assertNotEqual(body['summary'],body['model_summary'])
        self.assertEqual(body['approval'],'not-granted')

    def test_authorized_assignment_anchor_changes_gate_and_absent_timing_is_unresolved(self):
        old=self.f.anchor
        self.f.change_anchor('Only personnel with valid qualification at assignment may perform the assigned task.');self.f.declare(['assignment'])
        self.f.a=self.f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=self.f.a['ref'],source=Ref('SOURCE-sam',1))
        ctx=self.context([self.f.a['packet']]);out,_=self.validate(self.output(ctx,preferred='B'),ctx)
        self.assertEqual(out['recommendation']['preferred_option'],'B')
        self.assertEqual(next(o for o in out['options'] if o['id']=='B')['hard_gate'],'passes')
        self.f.change_anchor('Only qualified personnel may perform the assigned task.');self.f.declare([])
        self.f.a=self.f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=self.f.a['ref'],source=Ref('SOURCE-sam',1))
        ctx=self.context([self.f.a['packet']]);out,_=self.validate(self.output(ctx,preferred='B'),ctx)
        self.assertIsNone(out['recommendation']['preferred_option'])
        self.assertTrue(all(o['elements']['timing']['status']=='unspecified' for o in out['obligations']))
        self.assertIn('execution',self.f.store.read(old,{SCOPE})['body']['text'])

    def test_complete_local_mapping_is_required_even_without_second_packet(self):
        ctx=self.context([self.f.a['packet']]);out=self.output(ctx)
        good,_=self.validate(out,ctx);self.assertEqual(good['scope'],'within-domain')
        self.assertEqual(good['differences'],[])
        out['packet_findings'].pop()
        with self.assertRaisesRegex(ValueError,'each packet'):self.validate(out,ctx)

    def test_fabricated_span_invented_unspecified_value_and_foreign_reference_rejected(self):
        ctx=self.context()
        for change in ('quote','unspecified','reference'):
            out=self.output(ctx)
            if change=='quote':out['obligations'][0]['elements']['timing']=dict(status='specified',quote='every twenty minutes',interpretation='Invented')
            elif change=='unspecified':out['obligations'][0]['elements']['threshold']=dict(status='unspecified',quote='',interpretation='99 percent')
            else:out['packet_findings'][0]['evidence_refs']=['C-not-in-context']
            with self.subTest(change=change),self.assertRaises(ValueError):self.validate(out,ctx)

    def test_requirement_citation_alone_does_not_establish_packet_support(self):
        ctx=self.context();out=self.output(ctx,'ready')
        out['packet_findings'][0]['evidence_refs']=[out['packet_findings'][0]['obligation_ref']]
        with self.assertRaisesRegex(ValueError,'packet claim'):self.validate(out,ctx)
        good,_=self.validate(self.output(ctx,'ready'),ctx)
        self.assertEqual(good['packet_findings'][0]['support_verification'],'model-judgment-awaiting-human-review')

    def test_manifest_limits_and_conflicting_rules_block_substantive_options(self):
        ctx=self.context();ctx['manifest']['unavailable']=[dict(reason='Unavailable dependency')]
        out,_=self.validate(self.output(ctx),ctx)
        self.assertEqual(out['options'][0]['hard_gate'],'blocked')
        self.assertEqual(out['recommendation']['preferred_option'],'C');self.assertTrue(any('incomplete' in x for x in out['recommendation']['conditions']))
        ctx=self.context();out,_=integrity_options.validate(self.service,self.output(ctx),ctx,[dict(key='anchor-conflict:timing')])
        self.assertEqual(out['options'][0]['hard_gate'],'blocked')

    def test_amendment_missing_owner_and_contrary_evidence_cannot_be_approved(self):
        ctx=self.context()
        for key,value,gate in [('kind','amend-requirement','requires_authorized_requirement_change'),('owner',None,'blocked'),('support','contradicted','blocked')]:
            out=self.output(ctx,preferred='A');out['options'][0][key]=value
            checked,_=self.validate(out,ctx)
            self.assertEqual(checked['options'][0]['hard_gate'],gate);self.assertIsNone(checked['recommendation']['preferred_option'])
        out=self.output(ctx);out['options'][0]['owner']='unknown-person'
        with self.assertRaises(ValueError):self.validate(out,ctx)

    def test_option_response_permissions_rationale_version_and_governing_preservation(self):
        issue,a=self.attached();original=self.f.anchor;expected=asdict(self.f.current(issue)['ref'])
        payload=dict(expected=expected,option='C',disposition='accept-next-step',rationale='Inspect the identified candidate.')
        with self.assertRaises(PermissionError):self.f.w('sam').command('integrity-option-response',payload)
        with self.assertRaises(DecisionBlocked):self.service.option_response({**payload,'option':'B'})
        with self.assertRaises(ValueError):self.service.option_response({**payload,'rationale':''})
        self.f.w('alex').command('integrity-option-response',payload)
        with self.assertRaises(StaleBasis):self.service.option_response(payload)
        view=self.service.decision_view(self.f.current(issue));r=view['option_responses']['C']
        self.assertEqual(r['actor'],'alex');self.assertEqual(r['assessment'],a);self.assertTrue(r['at'])
        self.assertIsNone(view['ratification']);self.assertEqual(self.f.store.latest(original.id,{SCOPE})['ref'],original)

    def test_material_correction_is_retained_and_stale_option_response_rejected(self):
        issue,a=self.attached();key=next(f['key'] for f in self.f.review(a)['body']['findings'] if f['material'])
        payload=dict(expected=asdict(self.f.current(issue)['ref']),finding=key,disposition='modify-with-rationale',rationale='Narrow the scenario.')
        with self.assertRaises(ValueError):self.service.dispose(payload)
        self.service.dispose({**payload,'proposed_correction':'Ask for the existing control scope before asserting it is absent.'})
        view=self.service.decision_view(self.f.current(issue));finding=next(f for f in view['findings'] if f['key']==key)
        self.assertIn('existing control',finding['disposition']['body']['proposed_correction'])
        self.f.a=self.f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=self.f.a['ref'],source=Ref('SOURCE-sam',1))
        with self.assertRaises(StaleBasis):self.service.option_response(dict(expected=asdict(self.f.current(issue)['ref']),option='C',disposition='defer',rationale='Inputs changed.'))

    def test_incomplete_model_contract_has_failed_receipt_and_no_canned_result(self):
        class Incomplete(SimulatedOptionsModel):
            def generate(self,**kwargs):
                response=super().generate(**kwargs)
                if 'decision' in response['output']:response['output'].pop('decision')
                return response
        with self.assertRaisesRegex(ValueError,'requires a source-linked'):self.f.assessment(semantic=True,model=Incomplete())
        self.assertEqual(self.service.records('integrity-assessment'),[])
        self.assertEqual(next(r for r in self.service.records('agent-execution') if r['body']['skill']=='integrity-review')['body']['status'],'failed')

    def test_scripted_full_cycle_preserves_prior_choices_and_promotes_once(self):
        with tempfile.TemporaryDirectory() as folder:
            result=build(Path(folder));initial=result['initial'];revised=result['revised']
            self.assertTrue(result['initial_staleness']);self.assertTrue(revised['ratification'])
            self.assertEqual(initial['execution_receipt']['mode'],'simulated')
            self.assertEqual(initial['option_responses']['C']['disposition'],'accept-next-step')
            self.assertEqual(revised['history_records'][0]['option_responses']['C']['rationale'],initial['option_responses']['C']['rationale'])
            self.assertEqual(len(revised['history_records'][0]['decision_trace']['options']),3)
            self.assertEqual(result['reuse']['ref'],result['reuse_repeated']['ref'])
            self.assertTrue(result['reuse_repeated']['idempotent']);self.assertTrue((Path(folder)/'preview.sqlite3').exists())

    def test_truncated_source_tail_is_visible_and_blocks_substantive_acceptance(self):
        row=self.f.store.read(self.f.anchor,{SCOPE});body=deepcopy(row['body']);body['conditions']='Bounded statement. '*150
        self.f.store.put(self.f.anchor.id,'requirement',SCOPE,body,self.f.anchor.revision)
        self.f.anchor=self.f.store.latest(self.f.anchor.id,{SCOPE})['ref'];self.f.declare(['execution'])
        self.f.a=self.f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],True,previous=self.f.a['ref'],source=Ref('SOURCE-sam',1))
        ctx=self.context([self.f.a['packet']]);self.assertTrue(any('Citation span' in x['reason'] for x in ctx['manifest']['omitted']))
        out,_=self.validate(self.output(ctx),ctx);self.assertEqual(out['options'][0]['hard_gate'],'blocked')

    def test_exclusions_are_bounded_accessible_and_part_of_the_cache_basis(self):
        ps=[self.f.a['packet']]
        data=dict(packets=ps,mode='advisory',evaluation_scope='within-domain',intended_use='Inspect local timing only.')
        ctx=self.service.assemble({**data,'excluded_packets':[dict(packet=self.f.b['packet'],reason='Separate domain review follows.')]})
        self.assertEqual(ctx['intended_use'],data['intended_use'])
        self.assertEqual(ctx['manifest']['excluded_packets'][0]['packet'],self.f.b['packet'])
        with self.assertRaises(ValueError):self.service.assemble({**data,'excluded_packets':[dict(packet=ps[0],reason='Contradictory selection.')]})
        private=self.f.store.put('EXCLUDED-PRIVATE','source','domain:design',dict(text='Unreleased context'))
        self.f.store.packet('EXCLUDED-PRIVATE',1,'Private',[private],{'domain:design'},{'domain:design'})
        with self.assertRaises(PermissionError):self.service.assemble({**data,'excluded_packets':[dict(packet=dict(id='EXCLUDED-PRIVATE',revision=1),reason='Must not reveal private packet.')]})
