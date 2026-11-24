from contextlib import closing
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workbench.core import Ref, Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.intake import PRIVATE
from workbench.clinic_demo import NoEvaluation, populate
from test_intake import VALUE, CONTEXT

class SponsorVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'sponsor.sqlite3')
        self.w=Workspace(self.store,'priya',NoEvaluation());self.w.command('intake-start',dict(title='Fictional sponsor flow'))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.w.intake.draft()['ref'])
    def save(self,**data):return self.w.command('sponsor-save',dict(expected=self.ref(),**data))
    def test_renaming_preserves_independently_updated_context_and_saved_questions(self):
        from copy import deepcopy
        framing=deepcopy(self.w.sponsor.state()['brief']['framing'])
        self.save(answers={'q4':dict(items=[],roles=[dict(name='Technician',does='Respond to an event',needs='Status',where='Hangar',often='On demand')])})
        previous=deepcopy(self.w.intake.draft()['body'])
        framing['name']='Project_Human Simulation'
        self.save(framing=framing)
        current=self.w.intake.draft()['body']
        self.assertEqual(current['values'],previous['values'])
        self.assertEqual(current['sponsor_brief']['answers'],previous['sponsor_brief']['answers'])
        self.assertEqual(current['title'],'Project_Human Simulation')

    def test_business_intent_completion_is_bound_to_saved_content_and_preserves_other_answers(self):
        before=self.w.sponsor.state()['brief']['answers']
        self.save(fit={'value':'An explicit but unverified hypothesis.'},framing_completed={'fit-value':True})
        state=self.w.sponsor.state()['brief']
        self.assertTrue(state['framing_completed']['fit-value'])
        self.assertEqual(state['answers'],before)
        self.save(fit={'gains':'A different field can change.'})
        self.assertTrue(self.w.sponsor.state()['brief']['framing_completed']['fit-value'])
        self.save(fit={'value':'A revised hypothesis.'})
        self.assertFalse(self.w.sponsor.state()['brief']['framing_completed']['fit-value'])
        self.save(fit={'value':'An explicit but unverified hypothesis.'})
        self.assertFalse(self.w.sponsor.state()['brief']['framing_completed']['fit-value'])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='decision'").fetchone()[0],0)
    def test_business_intent_completion_rejects_empty_invalid_and_stale_saves(self):
        for completed in [{'fit-value':True},{'fit-value':'yes'},{'made-up':True}]:
            before=self.ref()
            with self.assertRaises(ValueError):self.save(framing_completed=completed)
            self.assertEqual(self.ref(),before)
        old=self.ref();self.save(fit={'value':'Draft text'})
        with self.assertRaises(StaleBasis):self.w.command('sponsor-save',dict(expected=old,framing_completed={'fit-value':True}))
        self.assertFalse(self.w.sponsor.state()['brief']['framing_completed']['fit-value'])
    def test_business_intent_read_does_not_migrate_saved_answers_or_infer_completion(self):
        before=self.ref();state=self.w.sponsor.state()
        self.assertFalse(any(state['brief']['framing_completed'].values()))
        self.assertEqual(self.ref(),before)

    def test_completion_is_separate_from_confirmation_and_preserves_unknowns(self):
        self.save(answers={'q12':dict(items=['The fallback owner is unknown.'],completed=True,confirmed=False)})
        a=self.w.sponsor.state()['brief']['answers']['q12']
        self.assertTrue(a['completed']);self.assertFalse(a['confirmed'])
        self.assertEqual(a['items'],['The fallback owner is unknown.'])
        self.save(answers={'q12':dict(items=a['items'],completed=False,confirmed=False)})
        self.assertFalse(self.w.sponsor.state()['brief']['answers']['q12']['completed'])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='decision'").fetchone()[0],0)
    def test_completion_requires_content_and_legacy_edits_do_not_inherit_completion(self):
        for patch in [dict(items=[],completed=True),dict(items=['Answer'],completed='yes'),dict(items=['Answer'],completed=None)]:
            before=self.ref()
            with self.assertRaises(ValueError):self.save(answers={'q12':patch})
            self.assertEqual(self.ref(),before)
        self.save(answers={'q12':dict(items=['Known answer'],completed=True)})
        self.save(answers={'q12':dict(items=['Known answer'])})
        self.assertTrue(self.w.sponsor.state()['brief']['answers']['q12']['completed'])
        self.save(answers={'q12':dict(items=['Changed answer'])})
        self.assertFalse(self.w.sponsor.state()['brief']['answers']['q12']['completed'])
    def test_legacy_confirmation_is_not_converted_to_completion_on_read(self):
        self.save(answers={'q12':dict(items=['Historic answer'],confirmed=True)})
        before=self.w.intake.draft()
        state=self.w.sponsor.state()['brief']['answers']['q12']
        self.assertTrue(state['confirmed']);self.assertFalse(state['completed'])
        self.assertEqual(self.w.intake.draft(),before)
    def test_structured_responses_and_role_cards_persist_without_source_or_approval_invention(self):
        q=dict(items=['Capture a usable non-safety report'],confirmed=True)
        role=dict(name='Technician · primary',does='Reports process friction',needs='Clear status',where='Shared mobile device',often='Weekly')
        self.save(answers={'q10':q,'q4':dict(roles=[role],confirmed=False)})
        state=self.w.state();self.assertEqual(len(state['sponsor']['questions']),22)
        self.assertEqual(state['sponsor']['brief']['answers']['q4']['roles'],[role])
        self.assertEqual(state['intake']['draft']['body']['values']['must_haves'],q['items'][0])
        self.assertEqual(state['intake']['draft']['body']['values']['beneficiaries'],role['name'])
        self.assertFalse(state['intake']['published']);self.assertEqual(state['decisions'],[])
        path=self.store.db.execute('PRAGMA database_list').fetchone()[2];self.store.close();self.store=Store(path);self.w=Workspace(self.store,'priya',NoEvaluation())
        self.assertEqual(self.w.sponsor.state()['brief']['answers']['q4']['roles'],[role])
        for actor in ('sam','lee','alex'):
            other=Workspace(self.store,actor,NoEvaluation());self.assertIsNone(other.sponsor.state())
            with self.assertRaises(PermissionError):other.command('sponsor-save',dict(expected=self.ref(),answers={'q2':q}))
    def test_core_value_edit_keeps_risks_alternatives_and_financial_case_distinct(self):
        framing=dict(name='Fictional Clinic',context='A bounded pilot',statement='Interrupted submissions',summary=dict(problem='Lost input',solution='Save and resume',risk='Triage effort',options='Manual pilot'))
        self.save(framing=framing,fit=dict(value='Support technicians completing their reporting task',gains='Less lost work',why_now='A pilot is being planned',investment_case='Estimate run costs before investment'))
        d=self.w.intake.draft();self.assertEqual(d['body']['sponsor_brief']['framing']['summary']['risk'],'Triage effort')
        self.assertEqual(d['body']['sponsor_brief']['framing']['summary']['options'],'Manual pilot')
        self.assertEqual(d['body']['values']['gains'],'Less lost work');self.assertEqual(d['body']['values']['why_now'],'A pilot is being planned')
        self.assertEqual(d['body']['values']['investment_case'],'Estimate run costs before investment')
        self.assertNotEqual(d['body']['values']['business_challenge'],d['body']['values']['value'])
        self.assertIsNone(self.w.intake.latest('INT-001'))

    def test_stale_edits_and_malformed_framing_do_not_partially_change_project(self):
        prior=self.ref();self.save(answers={'q10':dict(items=['A stored confirmation'],confirmed=False)})
        with self.assertRaises(StaleBasis):self.w.command('sponsor-save',dict(expected=prior,answers={}))
        before=list(self.store.db.iterdump())
        with self.assertRaises(ValueError):self.save(framing=dict(name='Wrong partial rename',context='',statement='',summary={}),fit={'assumption_owner':'unknown'})
        self.assertEqual(list(self.store.db.iterdump()),before)
        with self.assertRaises(ValueError):self.save(answers={'q99':dict(items=['Unknown'])})
    def test_all_extra_questions_reach_the_actual_review_and_published_intent(self):
        i=self.w.intake;i.save(dict(expected=self.ref(),step='value',**VALUE));i.accept_value(dict(expected=self.ref(),confirm=True));i.save(dict(expected=self.ref(),step='context',**CONTEXT))
        self.save(answers={'q10':dict(items=['Retain a report after a failed upload'],confirmed=True),'q12':dict(items=['Preserve input and offer retry'],confirmed=False)})
        i.build(dict(expected=self.ref()));self.assertFalse(i.gaps(i.draft()['body']))
        p=self.w.command('intake-preflight',dict(expected=self.ref(),research_focus='Confirm interruption needs',design_focus='Explore recovery'))
        prepared=i.latest(p['id']);case=self.w.command('intake-request',dict(expected=self.ref(),preflight=asdict(prepared['ref']),confirm=True))
        for actor in ('sam','lee'):
            Workspace(self.store,actor,NoEvaluation()).command('intake-review',dict(expected=asdict(i.latest(case['id'])['ref']),disposition='ready-for-investigation',rationale='Fictional bounded review'))
        self.w.command('intake-publish',dict(expected=asdict(i.latest(case['id'])['ref']),confirm=True,rationale='Publish for investigation'))
        intent=self.store.latest('INT-001',{SCOPE});self.assertEqual(intent['body']['business_brief']['answers']['q12']['items'],['Preserve input and offer retry'])
        self.assertEqual(intent['body']['intake']['must_haves'],'Retain a report after a failed upload')
        packet=self.store.resolve_packet('PKT-INTENT',1,{SCOPE});self.assertIn(intent['ref'],[r['ref'] for r in packet['records']])
        shared=self.store.latest(case['id'],{SCOPE});self.assertEqual(shared['body']['snapshot']['sponsor_brief']['answers']['q10']['confirmed'],True)
    def test_coaching_requires_consent_and_uses_exact_question_with_a_bounded_existing_expert(self):
        self.save(answers={'q10':dict(items=['Preserve input'],confirmed=False)})
        with patch.object(self.w.coaching,'run',return_value={'ref':{'id':'COACH', 'revision':1}}) as run:
            with self.assertRaises(ValueError):self.w.command('sponsor-coach',dict(expected=self.ref(),question='q10'))
            run.assert_not_called()
            self.w.command('sponsor-coach',dict(expected=self.ref(),question='q10',consent=True))
            context=run.call_args.args[0];self.assertEqual(context['skill'],'coach-field');self.assertEqual(context['sources'],[])
            self.assertIn('Preserve input',context['message']);self.assertIn('What must the system always do?',context['message'])
            self.assertEqual(context['expected'],self.ref())

    def test_question_advice_changes_only_its_actual_response_and_retains_provenance(self):
        self.save(answers={'q10':dict(items=['Keep a report reference'],confirmed=False)})
        before_scope=self.w.intake.draft()['body']['values']['in_scope']
        settings=self.w.coaching.settings.coaching()
        run=self.store.put('COACH-QUESTION','intake-coach-run',PRIVATE,dict(question_context={'id':'q10'},basis=self.ref(),configuration_fingerprint=settings['fingerprint'],sources=[],applied={},output={'suggestions':[dict(field='in_scope',text='Keep the stored report reference visible after submission.',rationale='Fictional suggestion for the selected must-have.',citations=[])]}))
        self.w.command('sponsor-apply-advice',dict(expected=self.ref(),run_id=run.id,question='q10',confirm=True))
        d=self.w.intake.draft();a=d['body']['sponsor_brief']['answers']['q10']
        self.assertEqual(a['items'],['Keep the stored report reference visible after submission.']);self.assertFalse(a['confirmed'])
        self.assertEqual(d['body']['values']['in_scope'],before_scope)
        self.assertEqual(d['body']['sponsor_question_provenance']['q10']['run'],asdict(run))
        self.assertIn('question:q10',self.store.latest(run.id,{PRIVATE})['body']['applied'])
        with self.assertRaises(StaleBasis):self.w.command('sponsor-apply-advice',dict(expected=self.ref(),run_id=run.id,question='q10',confirm=True))

class DeliveryVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'delivery.sqlite3');self.sample=populate(self.store);self.w=Workspace(self.store,'priya',NoEvaluation())
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def prepare(self,target='jira',**extra):return self.w.command('delivery-prepare',dict(target=target,work_item_type='Story' if target=='jira' else 'User Story',destination='FICTIONAL',requirements=[self.sample['requirement_after']])|extra)
    def test_jira_preview_is_deduplicated_traceable_private_and_not_a_send_receipt(self):
        before=self.store.latest(self.sample['requirement_after']['id'],{SCOPE});result=self.prepare();self.assertEqual(self.prepare()['id'],result['id'])
        draft=self.store.latest(result['id'],self.w.scopes);item=draft['body']['items'][0]
        self.assertEqual(item['payload']['fields']['project']['key'],'FICTIONAL');self.assertEqual(item['payload']['fields']['description']['type'],'doc')
        self.assertEqual(item['source'],self.sample['requirement_after']);self.assertTrue(item['goal_refs']);self.assertEqual(draft['body']['external_receipts'],[])
        self.assertFalse(self.w.delivery.state()['connected']);self.assertEqual(self.store.latest(before['ref'].id,{SCOPE}),before)
        self.assertEqual(self.w.command('delivery-export',dict(expected=asdict(draft['ref'])))['export']['status'],'preview-only')
        with self.assertRaises(PermissionError):Workspace(self.store,'lee',NoEvaluation()).command('delivery-export',dict(expected=asdict(draft['ref'])))
    def test_ado_uses_process_specific_type_acceptance_field_and_explicit_parent(self):
        result=self.prepare('ado',parent='https://dev.azure.com/example/project/_apis/wit/workItems/42');draft=self.store.latest(result['id'],self.w.scopes);item=draft['body']['items'][0]
        self.assertIn('$User%20Story',item['endpoint']);self.assertEqual(item['content_type'],'application/json-patch+json')
        self.assertTrue(any(x['path']=='/fields/Microsoft.VSTS.Common.AcceptanceCriteria' for x in item['payload']))
        relation=next(x for x in item['payload'] if x['path']=='/relations/-');self.assertEqual(relation['value']['rel'],'System.LinkTypes.Hierarchy-Reverse')
        with self.assertRaises(ValueError):self.prepare('ado',work_item_type='Unsupported')
    def test_changed_requirement_invalidates_export_without_silently_rebuilding_old_payload(self):
        result=self.prepare();draft=self.store.latest(result['id'],self.w.scopes);r=self.store.latest(self.sample['requirement_after']['id'],{SCOPE})
        self.store.put(r['ref'].id,r['kind'],r['scope'],{**r['body'],'text':'A newer fictional requirement'},r['ref'].revision)
        self.assertTrue(self.w.delivery.state()['drafts'][0]['changed'])
        with self.assertRaises(StaleBasis):self.w.command('delivery-export',dict(expected=asdict(draft['ref'])))
        self.assertEqual(self.store.read(draft['ref'],self.w.scopes),draft)
