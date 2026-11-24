"""Native HTTP/session boundary with synthetic evidence and a scripted model."""
import unittest
import test_web
from workbench.integrity_example import Fixture
from workbench.decisions import SCOPE
from test_integrity_condition_batches import TEXT
from workbench import integrity_corrections as corrections
from test_integrity_corrections import CorrectionModel


class CorrectionHTTPTests(unittest.TestCase):
    def setUp(self):
        self.h=test_web.WebTests();self.h.setUp();self.addCleanup(self.h.tearDown)
        self.model=CorrectionModel();self.h.server.model=self.model
        self.f=Fixture(self.h.server.path);self.addCleanup(self.f.store.close)
        # The strict wire fixture describes these synthetic events; the older
        # personnel example emits substrings unsuitable for this sentence schema.
        self.f.anchor=self.f.store.put('HTTP-EVENTS','requirement',SCOPE,dict(title='Synthetic events',text=TEXT,
            conditions='Keep original event identities.',acceptance_criteria='Retain every required event.',status='approved',owner='alex'))
        text='A synthetic event record is available for inspection.'
        source=self.f.store.put('HTTP-EVENT-SOURCE','contribution',SCOPE,dict(title='Synthetic evidence',text=text,owner='sam',domain='Research',status='published-for-review'))
        self.f.a=self.f.expression('sam','research','Events',text,[],source=source)
        self.h.post('profile',dict(actor='alex'))
        self.data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory',semantic=True,consent=True)

    def post(self,action,data):
        status,result=self.h.post(action,data);self.assertEqual(status,200,result);return result

    def test_native_prepare_correct_compare_read_and_session_guards(self):
        self.post('integrity-inventory-prepare',self.data)
        checkpoint=self.post('integrity-mapping-checkpoint',self.data)
        saved=self.post('integrity-correction-read',dict(ref=checkpoint['ref']))
        pair=next(iter(corrections.index(saved['bundle']['mappings'])))
        target=dict(packet_ref=pair[0],part_ref=pair[1],mode='judgment',quote_refs=[],
            reason='Review whether the cited assertion establishes this specific required relationship.')
        payload=dict(checkpoint=checkpoint['ref'],targets=[target])
        self.assertEqual(self.h.post('integrity-correction-prepare',payload,{'X-CSRF-Token':''})[0],403)
        self.assertEqual(self.h.post('integrity-correction-prepare',payload,{'Origin':'https://outside.invalid'})[0],403)
        plan=self.post('integrity-correction-prepare',payload)
        self.h.post('profile',dict(actor='sam'))
        self.assertEqual(self.h.post('integrity-correction-run',dict(plan=plan['ref'],consent=True,semantic=True))[0],403)
        self.h.post('profile',dict(actor='alex'))
        corrected=self.post('integrity-correction-run',dict(plan=plan['ref'],consent=True,semantic=True))
        self.assertEqual(corrected['status'],'ready-for-comparison')
        before=len(self.model.calls)
        final=self.post('integrity-assess',dict(self.data,mapping_checkpoint=corrected['ref']))
        self.assertEqual(len(self.model.calls),before+1)
        self.assertEqual(self.model.calls[-1]['context']['assessment_phase'],'joint-comparison')
        reviewed=self.post('integrity-review-read',dict(assessment=final['ref']))
        self.assertEqual(reviewed['approval'],'not-granted')
        self.assertEqual(reviewed['decision_trace']['checkpoint_provenance']['checkpoint'],corrected['ref'])
        self.assertEqual(self.post('integrity-correction-read',dict(ref=checkpoint['ref'])),saved)
