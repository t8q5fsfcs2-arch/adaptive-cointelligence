"""Material coverage invariants, including the observed false full-support case."""
from copy import deepcopy
import unittest
from workbench.integrity_example import Fixture
from workbench.integrity import model_context
from workbench.integrity_options_example import synthetic_output
from workbench import integrity_options as options,integrity_parts as parts

class MaterialPartsTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close);self.service=self.f.w('alex').integrity
        self.ctx=self.service.assemble(dict(packets=[self.f.a['packet']],mode='advisory',evaluation_scope='within-domain'))
        self.contract=options.context(self.ctx)
        self.out=synthetic_output(model_context(self.ctx))['decision']

    def test_review_units_preserve_every_character_and_full_clause_scope(self):
        text='Show the same current status; require a resolution note; confirmation, reopening and no-response policy remains explicit and configurable. Act within 3.5 seconds.'
        units=parts.catalog({'C':dict(quote=text)})
        self.assertEqual(len(units),4)
        self.assertEqual(''.join(text.split()),''.join(''.join(p['quote'].split()) for p in units.values()))
        for p in units.values():
            self.assertEqual(text[p['start']:p['end']],p['quote']);self.assertTrue(p['material'])
        self.assertIn('3.5 seconds',list(units.values())[-1]['quote'])

    def test_partial_material_condition_prevents_full_clause_support(self):
        units=parts.catalog({'C':dict(quote='Same current status; resolution note; confirmation, reopening and no-response policy is explicit and configurable.')})
        judgments=[dict(part_ref=k,status='supported',evidence_refs=['C-source'],reasoning='Cited packet claim.',remaining_gap='') for k in units]
        judgments[-1].update(status='uncertain',remaining_gap='The packet does not establish configurable confirmation, reopening or no-response policy.')
        result=parts.parent(judgments,units)
        self.assertEqual(result['status'],'uncertain');self.assertTrue(result['material'])
        self.assertIn('no-response',result['reasoning']);self.assertEqual(len(result['parts']),3)

    def test_unsupported_part_cannot_be_hidden_by_parent_status_or_material_flag(self):
        finding=self.out['packet_findings'][0]
        finding['parts'][0].update(status='uncertain',remaining_gap='No applicable evidence.')
        with self.assertRaisesRegex(ValueError,'Whole-clause support'):
            parts.validate_finding(finding,self.ctx,self.contract)
        finding['status']='uncertain';finding['material']=False
        parts.validate_finding(finding,self.ctx,self.contract)
        self.assertTrue(finding['material'])

    def test_each_supported_part_needs_its_own_packet_evidence(self):
        finding=self.out['packet_findings'][0]
        finding['parts'][0]['evidence_refs']=[]
        with self.assertRaisesRegex(ValueError,'own evidence'):parts.validate_finding(finding,self.ctx,self.contract)
        finding['parts'][0]['evidence_refs']=[finding['obligation_ref']]
        with self.assertRaisesRegex(ValueError,'not a requirement'):parts.validate_finding(finding,self.ctx,self.contract)

    def test_missing_duplicate_foreign_and_declared_gap_parts_fail_closed(self):
        for mutate in (lambda f:f['parts'].pop(),lambda f:f['parts'].append(deepcopy(f['parts'][0])),lambda f:f['parts'][0].update(part_ref='foreign')):
            finding=deepcopy(self.out['packet_findings'][0]);mutate(finding)
            with self.assertRaisesRegex(ValueError,'every material part'):parts.validate_finding(finding,self.ctx,self.contract)
        finding=deepcopy(self.out['packet_findings'][0]);finding['parts'][0]['remaining_gap']='A material condition is unverified.'
        with self.assertRaisesRegex(ValueError,'unresolved gap'):parts.validate_finding(finding,self.ctx,self.contract)

    def test_supported_contradicted_and_absent_aggregate_without_erasing_trace(self):
        self.assertEqual(parts.aggregate([dict(status='supported'),dict(status='supported')]),'supported')
        self.assertEqual(parts.aggregate([dict(status='supported'),dict(status='contradicted')]),'contradicted')
        self.assertEqual(parts.aggregate([dict(status='absent'),dict(status='absent')]),'absent')
        self.assertEqual(parts.aggregate([dict(status='supported'),dict(status='absent')]),'uncertain')
        out,_=options.validate(self.service,self.out,self.ctx,[])
        finding=out['packet_findings'][0]
        self.assertEqual(finding['status_derivation'],parts.VERSION)
        self.assertTrue(finding['parts'][0]['source']['quote'])
        self.assertEqual(finding['parts'][0]['support_verification'],'model-judgment-awaiting-human-review')

if __name__=='__main__':unittest.main()
