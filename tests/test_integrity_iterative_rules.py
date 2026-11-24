"""Native contract/retention checks with scripted fixtures, not model-quality tests."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from unittest.mock import patch

from workbench.integrity_example import Fixture
from workbench.integrity_options_example import synthetic_output
from workbench import integrity_methodology as method, integrity_recommendation, integrity_grounding as grounding
from workbench.decisions import SCOPE


BASIS = ('Whole solution confidence is low: the synthetic research sample may not '
         'represent intended users, and the business benefit remains unproven. '
         'Coverage of the stated clauses does not validate that benefit.')


class ReviewModel:
    def __init__(self, gaps=False, experiment=False):
        self.calls=[]; self.gaps=gaps; self.experiment=experiment
    def status(self):return dict(configured=True,provider='scripted',model='iterative-rules-contract-test')
    def generate(self,**request):
        self.calls.append(deepcopy(request));ctx=request['context'];phase=ctx.get('assessment_phase')
        out=synthetic_output(ctx,phase='investigate' if self.gaps or self.experiment else 'ready')
        if phase in ('condition-inventory','condition-inventory-review'):
            return dict(output=out,model='scripted',usage={})
        rec=out['decision']['recommendation']
        rec.update(why=BASIS,preferred_option='C' if self.experiment else None,
            disposition='proposed' if self.experiment else 'unresolved',
            requested_decision='Keep the thesis unendorsed; review whether a bounded investigation is worthwhile.',
            conditions=['The business benefit is unproven; a reply or completed task does not establish it.'],
            would_change_if=['Relevant new research changes the evidence for the business benefit.'])
        out.update(workability='unknown',summary=BASIS,
            unresolved=['The business thesis remains unverified by the synthetic sample.'])
        if phase=='clause-mapping':
            out={k:out['decision'][k] for k in ('obligations','packet_findings')}
            out['applicability']={key:dict(status='shared',rationale='Synthetic copied clauses have the same meaning.',
                occurrences={o['clause_ref']:dict(status='same-meaning',rationale='Synthetic copied qualifiers are identical.') for o in target['occurrences']}) for key,target in ctx['governing_targets'].items()}
        elif phase=='joint-comparison':
            for key in ('obligations','packet_findings'):out['decision'].pop(key)
        return dict(output=out,model='scripted',usage={})


class IterativeRulesTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close)
        self.data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory',semantic=True,consent=True)

    def assess(self, model):
        w=self.f.w('sam',model);result=w.command('integrity-assess',self.data)
        return w,result,self.f.review(result['ref'])['body']

    def assert_review_rules(self, calls):
        for call in calls:
            if call['context'].get('assessment_phase') in ('condition-inventory','condition-inventory-review'):
                # Keep faithful source extraction separate; no new inventory or
                # condition meaning is produced merely by changing review rules.
                self.assertNotIn(method.INSTRUCTIONS,call['instructions'])
                self.assertNotIn(grounding.RUBRIC,call['instructions'])
            else:
                self.assertEqual(call['instructions'].count(method.INSTRUCTIONS),1)
                self.assertEqual(call['instructions'].count(grounding.RUBRIC),1)
                self.assertEqual(call['context']['option_contract']['contract'],grounding.SEMANTIC_VERSION)
                if call['context'].get('assessment_phase')=='clause-mapping':
                    self.assertEqual(call['context']['material_rubric'],grounding.RUBRIC)
                    self.assertEqual(call['context']['semantic_contract'],grounding.SEMANTIC_VERSION)
                # Calibration examples must travel as instructions, never as
                # source evidence or governing conditions in the native request.
                for passage in call['context']['citation_catalog'].values():
                    self.assertNotIn('DOCUMENTARY CALIBRATION EXAMPLES:',passage['quote'])

    def test_whole_solution_uncertainty_survives_with_all_clauses_supported(self):
        model=ReviewModel();_,result,saved=self.assess(model)
        rec=saved['decision_trace']['recommendation']
        self.assertEqual(rec['unresolved_material_gaps'],[])
        self.assertTrue(all(p['status']=='supported' for f in saved['decision_trace']['packet_findings'] for p in f['parts']))
        self.assertIn(BASIS,result['summary']);self.assertEqual(rec['why'],BASIS)
        self.assertIsNone(rec['preferred_option']);self.assertEqual(rec['disposition'],'unresolved')
        self.assertEqual(saved['approval'],'not-granted')
        self.assertTrue(any(f['key']=='model:workability' for f in saved['findings']))
        self.assert_review_rules(model.calls)

    def test_bounded_pipeline_carries_same_rules_and_unresolved_solution_basis(self):
        model=ReviewModel();w=self.f.w('sam',model)
        refs=[asdict(self.f.anchor)];body=self.f.store.read(self.f.anchor,{SCOPE})['body']
        for n in range(2):refs.append(asdict(self.f.store.put('COPY-'+str(n),'requirement',SCOPE,deepcopy(body))))
        expression=self.f.review(self.f.a['ref'])['body']
        revised=w.integrity.expression(dict(source=expression['source'],domain='research',label='Scheduling',
            requirements=refs,facts=expression['facts'],expected=self.f.a['ref']))
        self.data['packets']=[revised['packet']]
        _,result,saved=self.assess(model)
        phases=[c['context'].get('assessment_phase') for c in model.calls]
        self.assertIn('clause-mapping',phases);self.assertIn('joint-comparison',phases)
        self.assert_review_rules(model.calls)
        self.assertIn(BASIS,result['summary']);self.assertEqual(saved['approval'],'not-granted')

    def test_useful_investigation_does_not_erase_low_confidence_or_gaps(self):
        model=ReviewModel(experiment=True);_,result,saved=self.assess(model)
        rec=saved['decision_trace']['recommendation']
        self.assertEqual(rec['preferred_option'],'C')
        self.assertTrue(rec['unresolved_material_gaps'])
        self.assertIn(BASIS,result['summary'])
        self.assertIn(integrity_recommendation.CLOSURE,result['summary'])
        self.assertEqual(saved['approval'],'not-granted')
        self.assertTrue(all(p['status']=='uncertain' for f in saved['decision_trace']['packet_findings'] for p in f['parts']))

    def test_unresolved_review_reuses_without_forcing_another_answer(self):
        model=ReviewModel(gaps=True);w,first,saved=self.assess(model)
        count=len(model.calls);again=w.command('integrity-assess',self.data)
        self.assertTrue(again['cached']);self.assertEqual(again['ref'],first['ref'])
        self.assertEqual(len(model.calls),count)
        self.assertEqual(self.f.review(first['ref'])['body'],saved)
        self.assertIsNone(saved['decision_trace']['recommendation']['preferred_option'])

    def test_rule_change_does_not_reuse_an_old_contract_review_as_current(self):
        import workbench.integrity as service
        model=ReviewModel()
        with patch.object(service,'PROMPT_VERSION','integrity-review-v16-iterative-honesty'):
            _,old,saved=self.assess(model)
        before=len(model.calls)
        w=self.f.w('sam',model)
        self.assertTrue(w.integrity.freshness(self.f.review(old['ref'])))
        new=w.command('integrity-assess',self.data)
        self.assertFalse(new['cached']);self.assertNotEqual(new['ref'],old['ref'])
        self.assertEqual(self.f.review(old['ref'])['body'],saved)
        updated=self.f.review(new['ref'])['body']
        self.assertEqual(updated['context']['condition_inventory'],saved['context']['condition_inventory'])
        self.assertEqual(updated['context']['evidence_level'],saved['context']['evidence_level'])
        self.assertFalse(any(c['context'].get('assessment_phase') in ('condition-inventory','condition-inventory-review') for c in model.calls[before:]))
        after=len(model.calls);again=w.command('integrity-assess',self.data)
        self.assertTrue(again['cached']);self.assertEqual(again['ref'],new['ref'])
        self.assertEqual(len(model.calls),after)


if __name__=='__main__':unittest.main()
