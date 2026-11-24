"""Regression coverage for dropped gaps; synthetic judgments, no provider calls."""
from copy import deepcopy
import unittest

from workbench import integrity_recommendation as projection, integrity_options
from workbench.integrity import model_context
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import SimulatedOptionsModel, synthetic_output


class CompleteRecommendationTests(unittest.TestCase):
    def trace(self, states=('uncertain', 'absent', 'contradicted', 'supported')):
        parts=[]
        for n,state in enumerate(states):
            parts.append(dict(part_ref='C/P'+str(n+1),status=state,
                interpretation=dict(state='settled',reading='Synthetic explicit meaning.',basis='Synthetic projection test only.',alternatives=[],clarification=None),
                remaining_gap='' if state=='supported' else 'Missing policy condition '+str(n+1),
                source=dict(quote='Exact material condition '+str(n+1),material=True),evidence_refs=['C-source']))
        return dict(packet_findings=[dict(packet_ref='P:v1',obligation_ref='C',material=False,parts=parts)],
            recommendation=dict(conditions=['Retain source limits.'],would_change_if=['Inspect the first condition.']),
            differences=[dict(packet_refs=['P:v1'],obligation_ref='C',would_disprove='Only inspect view parity.')])

    def test_all_unsupported_statuses_reach_summary_and_closure_without_rewriting_evidence(self):
        out=self.trace();before=deepcopy(out['packet_findings'])
        summary=projection.project(out,'Investigate before deciding.',{'P:v1':'Research'})
        gaps=out['recommendation']['unresolved_material_gaps']
        self.assertEqual([g['part_ref'] for g in gaps],['C/P1','C/P2','C/P3'])
        self.assertEqual(out['packet_findings'],before)
        for gap in gaps:
            self.assertIn(gap['text'],summary)
            self.assertIn(gap['text'],out['recommendation']['conditions'])
            self.assertIn(gap['text'],out['recommendation']['would_change_if'])
        self.assertIn('Contrary evidence',summary)
        self.assertIn(projection.CLOSURE,summary)

    def test_policy_gap_is_added_to_incomplete_difference_closure(self):
        out=self.trace();gap='Configurable confirmation, reopening and no-response policy is unestablished.'
        out['packet_findings'][0]['parts'][2]['remaining_gap']=gap
        projection.project(out,'Check view parity and resolution notes.',{'P:v1':'Research'})
        difference=out['differences'][0]
        self.assertEqual(difference['model_would_disprove'],'Only inspect view parity.')
        self.assertIn(gap,difference['would_disprove'])
        self.assertEqual(difference['unresolved_material_gap_keys'],['G1','G2','G3'])

    def test_same_wording_in_different_packets_retains_each_identity(self):
        out=self.trace(('uncertain',));other=deepcopy(out['packet_findings'][0]);other['packet_ref']='Q:v2'
        out['packet_findings'].append(other)
        summary=projection.project(out,'Investigate.',{'P:v1':'Research','Q:v2':'Design'})
        gaps=out['recommendation']['unresolved_material_gaps']
        self.assertEqual([g['packet_ref'] for g in gaps],['P:v1','Q:v2'])
        self.assertIn('Research — Uncertain',summary);self.assertIn('Design — Uncertain',summary)
        self.assertEqual(out['differences'][0]['unresolved_material_gap_keys'],['G1'])

    def test_long_checklist_cannot_be_clipped_to_model_summary_or_list_limits(self):
        out=self.trace(('uncertain',)*40)
        summary=projection.project(out,'Investigate.',{'P:v1':'Research'})
        self.assertGreater(len(summary),1500)
        self.assertIn('Missing policy condition 40',summary)
        self.assertEqual(len(out['recommendation']['unresolved_material_gaps']),40)
        self.assertEqual(len(out['recommendation']['conditions']),42)
        self.assertEqual(len(out['differences'][0]['unresolved_material_gap_keys']),40)

    def test_no_material_gaps_does_not_invent_a_closure_requirement(self):
        out=self.trace(('supported',));before=deepcopy(out)
        summary=projection.project(out,'Proposed next step.',{'P:v1':'Research'})
        self.assertEqual(summary,'Proposed next step.')
        self.assertEqual(out['recommendation']['unresolved_material_gaps'],[])
        self.assertEqual(out['recommendation']['conditions'],before['recommendation']['conditions'])
        self.assertEqual(out['differences'],before['differences'])

    def test_actual_command_saves_complete_recommendation_and_retains_raw_model_summary(self):
        fixture=Fixture();self.addCleanup(fixture.store.close)
        gap='No explicit configurable confirmation, reopening or no-response policy.'
        class Model(SimulatedOptionsModel):
            def generate(self,**kwargs):
                result=super().generate(**kwargs)
                if 'summary' in result['output']:result['output']['summary']='Check view parity and resolution notes.'
                if 'decision' in result['output']:result['output']['decision']['packet_findings'][0]['parts'][0]['remaining_gap']=gap
                return result
        model=Model(phase='investigate')
        result=fixture.w('alex',model).command('integrity-assess',dict(packets=[fixture.a['packet']],
            mode='advisory',evaluation_scope='within-domain',semantic=True,consent=True))
        body=fixture.review(result['ref'])['body'];rec=body['decision_trace']['recommendation']
        self.assertEqual(result['summary'],body['summary'])
        self.assertEqual(body['summary'],body['decision_trace']['summary'])
        self.assertIn(gap,body['summary'])
        self.assertEqual(body['model_summary'],'Check view parity and resolution notes.')
        self.assertEqual(len(rec['unresolved_material_gaps']),3)
        self.assertEqual(body['approval'],'not-granted');self.assertEqual(rec['approval'],'not-granted')
        self.assertEqual(model.calls,3)

    def test_provider_cannot_supply_a_fake_empty_derived_gap_list(self):
        fixture=Fixture();self.addCleanup(fixture.store.close);service=fixture.w('alex').integrity
        ctx=service.assemble(dict(packets=[fixture.a['packet']],mode='advisory',evaluation_scope='within-domain'))
        out=synthetic_output(model_context(ctx),phase='investigate')['decision']
        out['recommendation']['unresolved_material_gaps']=[]
        with self.assertRaisesRegex(ValueError,'extra decision trace fields'):
            integrity_options.validate(service,out,ctx,[])

    def test_provider_owner_is_named_participant_or_unassigned_never_invented_team(self):
        fixture=Fixture();self.addCleanup(fixture.store.close);service=fixture.w('alex').integrity
        ctx=service.assemble(dict(packets=[fixture.a['packet']],mode='advisory',evaluation_scope='within-domain'))
        owner=integrity_options.wire_schema(ctx)['properties']['options']['items']['properties']['owner']
        for value in ('alex','sam','lee',None):integrity_options.shape(value,owner)
        with self.assertRaises(ValueError):integrity_options.shape('engineering',owner)

    def test_failed_option_gate_still_displays_all_unresolved_parts(self):
        fixture=Fixture();self.addCleanup(fixture.store.close)
        result=fixture.assessment(semantic=True,model=SimulatedOptionsModel(phase='investigate',preferred='B'))
        body=fixture.review(result['ref'])['body'];rec=body['decision_trace']['recommendation']
        self.assertIsNone(rec['preferred_option']);self.assertEqual(rec['disposition'],'unresolved')
        self.assertEqual(len(rec['unresolved_material_gaps']),6)
        self.assertTrue(all(g['text'] in body['summary'] for g in rec['unresolved_material_gaps']))


if __name__=='__main__':unittest.main()
