"""Synthetic change cycle. Test doubles establish contracts, not model quality."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile, unittest
from unittest.mock import patch

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import DecisionBlocked, SCOPE
from workbench.intake import PROPOSITION_FIELDS, PRIVATE
from workbench.model_provider import ModelUnavailable
from workbench.workspace import Workspace


class ChangeModel:
    def __init__(self):self.custom=None;self.during=None
    def status(self):return dict(configured=True,provider='Synthetic test double',model='fixture')
    def generate(self,**request):
        self.request=deepcopy(request);c=request['context']
        p=next(s['passages'][0]['id'] for s in c['sources'] if s['id']==c['trigger_source']['id'])
        item=dict(effect='not-addressed',reason='The new source does not address this field.',evidence_kind='none',limitation='No conclusion about this field.',passage_ids=[],proposed_text=None)
        assessments={k:deepcopy(item) for k in PROPOSITION_FIELDS}
        assessments['value']=dict(effect='challenges',reason='Capture alone does not address the reported handoff problem.',evidence_kind='reported-finding',limitation='A small study; effectiveness is not established.',passage_ids=[p],proposed_text='For requesters awaiting a usable decision, visible ownership could reduce repeated chasing; the effect remains to be tested.')
        out=dict(summary='Shift the proposed value from faster capture toward clearer ownership.',recommendation='revise',assessments=assessments,
                 impacts=[dict(field='measures',effect='refines',reason='Measure the intended reduction in chasing.',evidence_kind='reported-finding',limitation='Baseline and target unknown.',passage_ids=[p],proposed_text='Repeated status enquiries per case; baseline and target remain unknown.')],requirements=[],questions=['Who can verify that a case has a usable decision?'])
        if self.during:self.during()
        return dict(output=self.custom or out,model='fixture',usage={})


class DocumentChangeTests(unittest.TestCase):
    def test_compact_model_targets_keep_full_freshness_receipt_and_detect_real_wording_changes(self):
        targets=[dict(key='drawer:0',kind='draft-drawer',body=dict(intake_fields=['value']*100,label='Needs',requirement='Current wording',acceptance_criteria='Current test'))]
        with patch.object(self.ws.document_changes,'downstream',return_value=targets):
            result=self.assess();record=self.store.read(Ref(**result),{PRIVATE})
            self.assertEqual(record['body']['downstream'],targets)
            self.assertNotIn('intake_fields',self.model.request['context']['downstream'][0]['body'])
            self.assertEqual(self.ws.document_changes.freshness(record['body']),[])
            targets[0]['body']['requirement']='Changed wording'
            self.assertIn('The requirement inventory changed.',self.ws.document_changes.freshness(record['body']))
    def test_change_instructions_name_the_actual_new_source_citation_prefix(self):
        self.assess()
        self.assertIn(self.new['id']+'@'+str(self.new['revision'])+':p',self.model.request['instructions'])
        self.assertIn('Earlier-source citations may accompany it but cannot replace it',self.model.request['instructions'])
    def test_assessment_context_retains_target_meaning_without_repeated_intake_field_lists(self):
        from workbench.document_changes import assessment_targets
        original=[dict(key='drawer:0',kind='draft-drawer',body=dict(label='Needs',question='Who needs what?',intake_fields=['value']*1000,children=[dict(key='jobs',requirement='Keep the user job',acceptance_criteria='Observe the outcome',basis_fields=['jobs'])])),dict(key='REQ-1:v2',ref=dict(id='REQ-1',revision=2),kind='requirement',body=dict(text='Existing exact wording',acceptance_criteria='Exact criterion',source_refs=[dict(id='SRC-1',revision=3)]))]
        prior=deepcopy(original);result=assessment_targets(original)
        self.assertEqual(original,prior)
        self.assertEqual(result[1],original[1])
        self.assertEqual(result[0]['body']['children'][0]['requirement'],'Keep the user job')
        self.assertEqual(result[0]['body']['children'][0]['acceptance_criteria'],'Observe the outcome')
        self.assertNotIn('intake_fields',result[0]['body'])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.model=ChangeModel()
        self.ws=Workspace(self.store,'priya',self.model);self.ws.intake.start({'title':'Fictional handoffs'})
        self.old=self.ws.coaching.add_source({'title':'Earlier proposal','text':'A faster form could improve capture. This is a proposal.','role':'hypothesis'})['ref']
        values={k:'Stated but untested '+k for k in PROPOSITION_FIELDS};values['value']='A faster form could improve capture.'
        self.ws.intake.save(dict(expected=self.ref(),step='value',**values))
        self.ws.intake.accept_value(dict(expected=self.ref(),confirm=True))
        self.base=self.ref()
        self.new=self.ws.coaching.add_source({'title':'Small fictional study','text':'Four participants reported repeated chasing after submission. Ownership was unclear. No performance study was run.','role':'evidence'})['ref']
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.ws.intake.draft()['ref'])
    def assess(self,**overrides):
        return self.ws.document_changes.assess({**dict(expected=self.ref(),trigger_source=self.new,sources=[self.old,self.new],consent=True),**overrides})['ref']
    def resolve(self,r,action='apply',**overrides):
        data=dict(expected=self.ref(),review=r,disposition=action,confirm=True,reason='The reported handoff failure merits a bounded draft revision.')
        if action=='apply':data['changes']={'value':'My edited proposition: clearer ownership could reduce chasing, pending validation.'}
        data.update(overrides);return self.ws.document_changes.resolve(data)
    def test_complete_comparison_preserves_draft_and_exact_excerpts(self):
        r=self.assess();saved=self.store.read(Ref(**r),{PRIVATE})['body']
        self.assertEqual(self.ref(),self.base);self.assertEqual(saved['basis'],self.base)
        c=self.model.request['context'];self.assertEqual(c['pre_upload_draft']['ref'],self.base)
        self.assertEqual([s['ref'] for s in c['sources']],[self.old,self.new])
        citation=saved['output']['assessments']['value']['citations'][0]
        source=self.store.read(Ref(**self.new),{PRIVATE})['body']['text']
        self.assertEqual(citation['quote'],source[citation['start']:citation['end']]);self.assertEqual(citation['source_ref'],self.new)
        self.assertEqual(set(saved['output']['assessments']),set(PROPOSITION_FIELDS))
        self.assertTrue(self.ws.document_changes.state()['pending_sources'])
        self.assertIsNone(self.ws.intake.latest('INT-001'))

    def test_repeated_provenance_excerpts_do_not_exhaust_document_context(self):
        draft=self.ws.intake.draft()
        provenance={'origin':'document', 'status':'draft', 'text':'Prior generated answer',
                    'rationale':'A source-supported proposal.', 'answer_basis':self.base,
                    'citations':[dict(source_id=self.old['id'], source_ref=self.old,
                                      start=0,end=30,quote='Repeated source excerpt '*10000)]}
        draft['body']['field_provenance']={'value':deepcopy(provenance)}
        self.ws.intake.save_draft(draft,draft['body'])
        basis=self.ref();self.assess()
        lineage=self.model.request['context']['field_provenance']['value']
        self.assertNotIn('text',lineage)
        self.assertNotIn('quote',lineage['citations'][0])
        self.assertEqual(lineage['citations'][0]['source_ref'],self.old)
        self.assertEqual(lineage['rationale'],provenance['rationale'])
        self.assertEqual(self.ws.intake.draft()['body']['field_provenance']['value'],provenance)
        self.assertEqual(self.ref(),basis)

    def test_known_metric_definition_error_is_visible_and_cannot_be_applied_unchanged(self):
        self.assess()
        r=self.ws.document_changes.state()['reviews'][0]
        raw=deepcopy(r['body']['output'])
        for item in [*raw['assessments'].values(),*raw['impacts']]:item.pop('citations',None)
        raw['impacts'][0]['proposed_text']='Average time to assignment = median minutes from submission to assignment.'
        self.model.custom=raw;r=self.assess()
        flags=self.ws.document_changes.state()['reviews'][0]['quality_flags']
        self.assertEqual(flags[0]['field'],'measures');self.assertTrue(flags[0]['blocks_application'])
        with self.assertRaisesRegex(ValueError,'statistic'):
            self.resolve(r,changes={'value':'Edited value still pending.','measures':raw['impacts'][0]['proposed_text']})
        self.assertEqual(self.ref(),self.base)
        self.resolve(r,changes={'measures':'Candidate: median minutes from submission to assignment for assigned cases; baseline and target unknown.'})
        self.assertTrue(self.ws.intake.draft()['body']['values']['measures'].startswith('Candidate: median'))
    def test_apply_is_explicit_versioned_and_does_not_approve_or_publish(self):
        r=self.assess();self.resolve(r)
        self.assertEqual(self.ref()['revision'],self.base['revision']+1)
        self.assertEqual(self.store.read(Ref(**self.base),{PRIVATE})['body']['values']['value'],'A faster form could improve capture.')
        self.assertTrue(self.ws.intake.draft()['body']['values']['value'].startswith('My edited'))
        self.assertEqual(self.ws.intake.draft()['body']['field_provenance']['value']['status'],'sponsor-edited-after-coaching')
        self.assertFalse(self.ws.document_changes.state()['pending_sources'])
        self.assertFalse(self.ws.intake.value_checkpoint(self.ws.intake.draft()['body'])['current'])
        self.assertIsNone(self.ws.intake.latest('INT-001'))
        b=self.store.latest(r['id'],{PRIVATE})['body'];self.assertEqual(b['decisions'][0]['prior_draft'],self.base)
        self.assertEqual(b['decisions'][0]['not_adopted'],['measures'])
        with self.assertRaises(StaleBasis):self.resolve(r)
    def test_keep_records_reason_and_reuses_review_only_after_resolution(self):
        self.assertFalse(self.ws.intake.value_checkpoint(self.ws.intake.draft()['body'])['current'])
        with self.assertRaises(DecisionBlocked):self.ws.intake.accept_value(dict(expected=self.ref(),confirm=True))
        r=self.assess();self.resolve(r,'keep',reason='Treat the small study as a question; retain this conditional wording for now.')
        self.assertEqual(self.ref(),self.base)
        self.assertTrue(self.ws.intake.value_checkpoint(self.ws.intake.draft()['body'])['current'])
        self.assertEqual(self.store.latest(r['id'],{PRIVATE})['body']['status'],'kept')
    def test_defer_keeps_reconsideration_open(self):
        r=self.assess();self.resolve(r,'defer',reason='Ask the local owner how the handoff operates.')
        self.assertEqual(self.ref(),self.base);self.assertTrue(self.ws.document_changes.state()['pending_sources'])
        r=asdict(self.store.latest(r['id'],{PRIVATE})['ref']);self.resolve(r,'keep')
        self.assertEqual(len(self.store.latest(r['id'],{PRIVATE})['body']['decisions']),2)
    def test_stale_draft_source_configuration_and_requirement_block_adoption(self):
        for mutation in ('draft','source','config','requirement'):
            with self.subTest(mutation=mutation):
                r=self.assess()
                if mutation=='draft':self.ws.intake.save(dict(expected=self.ref(),step='value',jobs='A changed human answer.'))
                elif mutation=='source':
                    source=self.store.latest(self.new['id'],{PRIVATE});self.store.put(source['ref'].id,source['kind'],PRIVATE,{**source['body'],'text':'Revised findings'},source['ref'].revision)
                elif mutation=='config':
                    cfg=self.ws.coaching.settings.coaching();self.ws.coaching.settings.save_coaching(dict(expected=cfg['ref'],area='skill',key='assess-change',config={'instructions':'Require explicit counterevidence.'}))
                else:self.store.put('REQ-TEST','requirement',SCOPE,dict(text='A recorded requirement',owner='alex'))
                with self.assertRaises(StaleBasis):self.resolve(r,'keep')
                if mutation=='source':self.new=asdict(self.store.latest(self.new['id'],{PRIVATE})['ref'])
    def test_partial_source_selection_and_missing_consent_are_rejected(self):
        with self.assertRaises(ValueError):self.assess(sources=[self.new])
        with self.assertRaises(ValueError):self.assess(consent=False)
        with self.assertRaises(PermissionError):Workspace(self.store,'sam',self.model).document_changes.assess({})
        self.assertIsNone(Workspace(self.store,'sam',self.model).document_changes.state())
    def test_invalid_claim_references_and_invented_target_fail_closed(self):
        self.assess();good=deepcopy(self.store.latest(self.ws.document_changes.state()['reviews'][0]['ref'].id,{PRIVATE})['body']['output'])
        for i in good['assessments'].values():i.pop('citations',None)
        for i in good['impacts']:i.pop('citations',None)
        for mode in ('invented','old-only','missing-field','invented-target','duplicate-impact'):
            bad=deepcopy(good)
            if mode=='invented':bad['assessments']['value']['passage_ids']=['missing']
            elif mode=='old-only':bad['assessments']['value']['passage_ids']=[self.old['id']+'@1:p1']
            elif mode=='missing-field':bad['assessments'].pop('jobs')
            elif mode=='invented-target':bad['requirements']=[dict(target='JIRA-123',reason='Invented',passage_ids=[self.new['id']+'@1:p1'])]
            else:bad['impacts'].append(deepcopy(bad['impacts'][0]))
            self.model.custom=bad
            with self.subTest(mode=mode),self.assertRaises(ModelUnavailable):self.assess()
        self.assertEqual(self.ref(),self.base)
    def test_result_is_retained_but_stale_if_answers_change_during_inference(self):
        self.model.during=lambda:self.ws.intake.save(dict(expected=self.ref(),step='value',jobs='Human edit during analysis.'))
        r=self.assess();state=self.ws.document_changes.state()['reviews'][0]
        self.assertTrue(state['stale']);self.assertTrue(state['body']['output'])
        with self.assertRaises(StaleBasis):self.resolve(r)
    def test_decisions_require_reason_confirmation_and_only_assessed_edits(self):
        r=self.assess()
        for options in ({'reason':''},{'confirm':False},{'changes':{}},{'changes':{'business_challenge':'Unassessed edit'}},{'changes':{'value':''}}):
            with self.subTest(options=options),self.assertRaises(ValueError):self.resolve(r,**options)
        self.assertEqual(self.ref(),self.base)

    def test_pending_private_material_pauses_publication_without_disclosing_its_content(self):
        body=dict(snapshot=self.ws.intake.draft()['body'],source_draft=self.ref(),base_intent=None,status='pending-review',reviews={},decision_ids=[])
        r=self.store.put('INTREV-TEST','intake-case',SCOPE,body)
        messages=self.ws.intake.freshness(body)
        self.assertTrue(any('new material' in x for x in messages))
        self.assertNotIn('Small fictional study',str(messages))
        with self.assertRaises(StaleBasis):self.ws.intake.publish(dict(expected=asdict(r),confirm=True))
        self.assertIsNone(self.ws.intake.latest('INT-001'))

    def test_full_document_assessment_has_a_bounded_document_timeout(self):
        from workbench.model_provider import request_timeout
        self.assertEqual(request_timeout({'skill':'assess-change'}),180)
        self.assertEqual(request_timeout({'skill':'coach-field'}),55)
