from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import json
import unittest
from workbench.core import Store, StaleBasis
from workbench.workspace import Workspace
from workbench.decisions import SCOPE
from workbench.model_provider import ModelUnavailable
from workbench.agent_runs import monitoring
from test_intake import VALUE, CONTEXT

class CoachModel:
    def __init__(self):self.calls=[];self.during=None;self.bad=None;self.fail=False
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='fake')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw))
        if self.during:self.during()
        if self.fail:raise ModelUnavailable('Synthetic failure')
        out=dict(assessment='Clarify what counts as a successful handoff.',why_it_matters='This makes the result reproducible and tied to reduced repeat work.',next_question='What evidence shows that the receiving worker can continue?',suggested_wording='Track handoffs that allow the receiving worker to continue without repeating the interview.')
        if kw['context']['field']=='basis_fields':
            out['basis_suggestions']=[dict(field='need',reason='The stated loss of progress explains the proposed effort-reduction outcome.')]
        if self.bad:self.bad(out)
        return dict(output=out,model='fake',usage=dict(total_tokens=60))

class FieldCoachTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite3');self.model=CoachModel()
        self.w=Workspace(self.store,'priya',self.model);self.i=self.w.intake
        self.i.start(dict(title='Synthetic coach project'));self.i.save(dict(expected=self.ref(),step='value',**VALUE));self.i.save(dict(expected=self.ref(),step='context',**CONTEXT));self.i.build(dict(expected=self.ref()))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.i.draft()['ref'])
    def data(self,**extra):return dict(mode='draft',kind='measure',field='definition',id='M-new',working=dict(name='Handoff success',definition='Most handoffs work',goal_ids=[]),expected=self.ref(),consent=True,**extra)
    def test_unsaved_response_coached_without_saving_or_publication(self):
        before=deepcopy(self.i.draft());r=self.w.command('field-coach',self.data())
        self.assertEqual(self.i.draft(),before);self.assertEqual(r['mode'],'simulated')
        ctx=self.model.calls[0]['context'];self.assertEqual(ctx['working_copy']['definition'],'Most handoffs work');self.assertIn('not saved',ctx['working_copy_status'])
        self.assertIn('GOV.UK',self.model.calls[0]['instructions']);self.assertIn('NASA',self.model.calls[0]['instructions'])
        runs=monitoring(self.store,'priya')['runs'];self.assertEqual(runs[0]['skill'],'coach-item');self.assertFalse(runs[0]['applied']);self.assertNotIn('context',runs[0])
        self.assertFalse(any(r['kind']=='field-coach-advice' for r in self.w.state()['records']))
    def test_guidance_and_question_bounds(self):
        for fields in self.w.field_coach.public_guidance()['groups'].values():
            for guide in fields.values():self.assertTrue(all(guide[k] for k in ('title','what','why','example')))
        with self.assertRaises(ValueError):self.w.command('field-coach',self.data(question='x'*1201))
        self.assertFalse(self.model.calls)
    def test_scope_enforced_before_model(self):
        for actor in ('sam','lee','alex'):
            w=Workspace(self.store,actor,self.model)
            with self.assertRaises(PermissionError):w.command('field-coach',self.data())
            with self.assertRaises(PermissionError):w.command('field-coach',dict(mode='record',kind='goal',field='outcome',expected=self.ref(),consent=True))
        self.assertFalse(self.model.calls)
    def test_shared_record_exact_links_and_no_private_intake(self):
        goal=self.store.put('G-shared','goal',SCOPE,dict(title='Shared goal',outcome='Less effort'))
        r=self.store.put('REQ-shared','requirement',SCOPE,dict(title='Shared requirement',text='Visible history',status='proposed',goal_refs=[asdict(goal)]))
        Workspace(self.store,'lee',self.model).command('field-coach',dict(mode='record',kind='requirement',field='text',expected=asdict(r),working={'text':'FAKE CLIENT OVERRIDE'},consent=True))
        ctx=self.model.calls[-1]['context'];self.assertNotIn('intent',ctx);self.assertEqual(ctx['working_copy']['text'],'Visible history');self.assertEqual(ctx['linked_outcomes'][0]['ref'],asdict(goal));self.assertNotIn('FAKE CLIENT',str(ctx))
        for actor in ('priya','sam','alex'):self.assertFalse(any(x['kind']=='field-coach-advice' for x in Workspace(self.store,actor).state()['records']))
    def test_changes_and_failures_preserve_user_work(self):
        before=deepcopy(self.i.draft());self.model.fail=True
        with self.assertRaises(ModelUnavailable):self.w.command('field-coach',self.data())
        self.assertEqual(before,self.i.draft());self.assertEqual(monitoring(self.store,'priya')['runs'][0]['status'],'failed')
        self.model.fail=False;self.model.bad=lambda out:out.update(assessment=42)
        with self.assertRaises(ModelUnavailable):self.w.command('field-coach',self.data())
        self.model.bad=None;self.model.during=lambda:self.i.save(dict(expected=self.ref(),step='value',value='Changed intake'))
        with self.assertRaises(StaleBasis):self.w.command('field-coach',self.data())
        self.assertEqual(monitoring(self.store,'priya')['runs'][0]['status'],'stale')
        self.model.during=lambda:self.w.requirement_agent.configure(dict(expected=self.w.requirement_agent.state()['settings']['ref'],draft='Draft carefully',review='Prioritize observability',tailor='Use project context'))
        with self.assertRaises(StaleBasis):self.w.command('field-coach',self.data())
    def test_requirement_criteria_and_structured_links(self):
        area=self.i.draft()['body']['scaffold'][1];child=area['children'][0];path=area['key']+'/'+child['key']
        d=self.data();d.update(kind='requirement',field='requirement',id=path,working=dict(requirement='Make it accessible',goal_ids=[]))
        self.w.command('field-coach',d);self.assertEqual(self.model.calls[-1]['context']['area']['criteria'],child['criteria'])
        d['field']='goal_ids';r=self.w.command('field-coach',d);self.assertEqual(r['output']['suggested_wording'],'')
    def test_invalid_input_rejected_before_model(self):
        for patch in [dict(consent=False),dict(field='password'),dict(working={'definition':'x'*20001}),dict(working={'private_source':'secret'})]:
            d=self.data();d.update(patch)
            with self.assertRaises(ValueError):self.w.command('field-coach',d)
        self.assertFalse(self.model.calls)

    def connection_data(self):
        d=self.data();d.update(field='basis_fields',working=dict(name='Handoff success',definition='Reduce repeated effort',basis_fields=['value'],goal_ids=[]));return d

    def test_connections_use_exact_answers_and_do_not_save_or_publish(self):
        d=self.connection_data();before=deepcopy(self.i.draft());r=self.w.command('field-coach',d)
        self.assertEqual(before,self.i.draft());o=r['output'];self.assertEqual(o['suggested_wording'],'')
        self.assertEqual(o['basis_suggestions'][0]['source_answer'],VALUE['need'])
        self.assertIn('business_challenge',self.model.calls[-1]['context']['intake_answers'])
        self.assertEqual(self.w.command('field-coach-check',{**d,'advice':r['ref']}),dict(current=True))
        self.assertEqual(before,self.i.draft())
        self.assertFalse(any(x['kind'] in ('goal','success-measure') for x in self.w.state()['records']))

    def test_bad_connections_never_pass_output_validation(self):
        cases=[None,[dict(field='invented',reason='Claim')],[dict(field='review_plan',reason='Empty answer')],
            [dict(field='need',reason='')],[dict(field='need',reason='x'*501)],
            [dict(field='need',reason='Valid')]*2,[dict(field='need',reason='Valid',source_answer='Fabrication')]]
        for suggestions in cases:
            with self.subTest(suggestions=suggestions):
                self.model.bad=lambda out:out.update(basis_suggestions=suggestions)
                with self.assertRaises(ModelUnavailable):self.w.command('field-coach',self.connection_data())

    def test_empty_recommendations_are_valid_and_shared_basis_is_private(self):
        self.model.bad=lambda out:out.update(basis_suggestions=[])
        self.assertEqual(self.w.command('field-coach',self.connection_data())['output']['basis_suggestions'],[])
        d=self.connection_data();d['mode']='record'
        with self.assertRaises(ValueError):self.w.command('field-coach',d)
        for actor in ('sam','lee','alex'):
            with self.assertRaises(PermissionError):Workspace(self.store,actor,self.model).command('field-coach',self.connection_data())

    def test_advice_rechecked_for_changed_draft_config_and_actor(self):
        d=self.connection_data();r=self.w.command('field-coach',d);check={**d,'advice':r['ref']}
        modified=deepcopy(check);modified['working']['definition']='A different outcome'
        with self.assertRaises(StaleBasis):self.w.command('field-coach-check',modified)
        with self.assertRaises(PermissionError):Workspace(self.store,'sam',self.model).command('field-coach-check',check)
        self.w.requirement_agent.configure(dict(expected=self.w.requirement_agent.state()['settings']['ref'],draft='Draft carefully',review='Prioritize observability',tailor='Use project context'))
        with self.assertRaises(StaleBasis):self.w.command('field-coach-check',check)
        r=self.w.command('field-coach',d);check['advice']=r['ref']
        self.i.save(dict(expected=self.ref(),step='value',need='Changed underlying need'))
        with self.assertRaises(StaleBasis):self.w.command('field-coach-check',check)

    def test_invalid_selected_connections_and_blank_items_stop_before_inference(self):
        for working in ({'name':'Measure','basis_fields':['invented']},{'name':'Measure','basis_fields':'value'},{'basis_fields':[]}):
            d=self.connection_data();d['working']=working
            with self.assertRaises(ValueError):self.w.command('field-coach',d)
        self.assertFalse(self.model.calls)

    def test_same_target_followup_reuses_only_the_previous_exchange_without_changing_work(self):
        data=self.data(question='What makes a handoff measurable?');before=deepcopy(self.i.draft())
        first=self.w.command('field-coach',data)
        followup={**data,'question':'What evidence would answer that?','previous_advice':first['ref']}
        second=self.w.command('field-coach',followup)
        ctx=self.model.calls[-1]['context'];exchange=ctx['previous_exchange']
        self.assertEqual(ctx['question'],followup['question']);self.assertEqual(exchange['question'],data['question'])
        self.assertEqual(exchange['reply'],first['output']);self.assertIn('not project evidence or human approval',exchange['status'])
        self.assertEqual(ctx['working_copy'],data['working']);self.assertEqual(self.i.draft(),before)
        self.w.command('field-coach',{**data,'question':'Please explain the next step.','previous_advice':second['ref']})
        latest=self.model.calls[-1]['context']['previous_exchange']
        self.assertEqual(latest['question'],followup['question']);self.assertNotIn('previous_exchange',latest['reply'])
        self.assertEqual(self.i.draft(),before)

    def test_private_saved_page_followup_keeps_its_exact_sponsor_basis(self):
        data=dict(mode='draft-page',field='question',expected=self.ref(),question='What should I clarify in this page?',consent=True)
        before=deepcopy(self.i.draft());first=self.w.command('field-coach',data)
        self.w.command('field-coach',{**data,'question':'Why is that the next step?','previous_advice':first['ref']})
        ctx=self.model.calls[-1]['context'];self.assertEqual(ctx['saved_intake'],before['body']['values'])
        self.assertEqual(ctx['previous_exchange']['question'],data['question']);self.assertEqual(ctx['previous_exchange']['reply'],first['output'])
        self.assertIn('Private saved sponsor context',ctx['working_copy_status']);self.assertEqual(self.i.draft(),before)

    def test_changed_working_copy_cannot_reuse_previous_advice_even_at_the_same_saved_revision(self):
        data=self.data(question='What is missing?');first=self.w.command('field-coach',data);before=deepcopy(self.i.draft())
        changed=deepcopy(data);changed.update(question='Does that still apply?',previous_advice=first['ref']);changed['working']['definition']='Measure a different outcome.'
        with self.assertRaises(StaleBasis):self.w.command('field-coach',changed)
        self.assertEqual(len(self.model.calls),1);self.assertEqual(self.i.draft(),before)

    def test_previous_advice_cannot_move_to_another_field_target_or_saved_basis(self):
        data=self.data(question='How can I refine this?');first=self.w.command('field-coach',data)
        for patch in (dict(field='baseline'),dict(id='M-other')):
            changed={**data,**patch,'previous_advice':first['ref']}
            with self.subTest(patch=patch),self.assertRaises(StaleBasis):self.w.command('field-coach',changed)
        self.i.save(dict(expected=self.ref(),step='value',need='New underlying business need'))
        with self.assertRaises(StaleBasis):self.w.command('field-coach',{**data,'expected':self.ref(),'previous_advice':first['ref']})
        self.assertEqual(len(self.model.calls),1)

    def test_previous_advice_requires_the_same_coach_configuration(self):
        data=self.data(question='What is missing?');first=self.w.command('field-coach',data)
        self.w.requirement_agent.configure(dict(expected=self.w.requirement_agent.state()['settings']['ref'],draft='Draft carefully',review='Prioritize observability',tailor='Use project context'))
        with self.assertRaises(StaleBasis):self.w.command('field-coach',{**data,'question':'Explain that advice.','previous_advice':first['ref']})
        self.assertEqual(len(self.model.calls),1)
        self.w.command('field-coach',{**data,'question':'Review this independently.'})
        self.assertEqual(len(self.model.calls),2)

class RequirementAssessmentCoachContextTests(unittest.TestCase):
    def test_shared_requirement_gets_versioned_standards_without_grading_or_writes(self):
        store=Store(':memory:')
        self.addCleanup(store.close)
        req=store.put('REQ-CONTEXT','requirement',SCOPE,dict(title='Keep a draft',text='Retain an entered draft after save failure.',status='proposed'))
        before=[tuple(r) for r in store.db.execute('SELECT * FROM records')]
        coach=Workspace(store,'lee').field_coach
        ctx,refs=coach.context(dict(mode='record',kind='requirement',field='text',expected=asdict(req),question='What needs clarification?'))
        assessment=ctx['requirement_assessment']
        self.assertEqual(assessment['standard']['ref'],dict(id='REQ-ASSESSMENT-STANDARD',revision=1))
        self.assertEqual(set(assessment['standard']['body']['profiles']),{'investigation','prototype','implementation'})
        self.assertNotIn('inventory',assessment)
        self.assertTrue(all(v['status']=='not-assessed' for v in assessment['assessments'].values()))
        self.assertEqual([tuple(r) for r in store.db.execute('SELECT * FROM records')],before)
        self.assertEqual(refs,[req])

class PageQuestionTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:');self.addCleanup(self.store.close)
        self.req=self.store.put('REQ-PAGE','requirement',SCOPE,dict(title='Shared handoff',text='Retain handoff context.',status='proposed'))
        self.store.put('PRIVATE-PAGE','requirement','domain:research',dict(title='PRIVATE SECRET',text='Never shared'))
        self.model=CoachModel();self.w=Workspace(self.store,'lee',self.model)
    def request(self):
        return dict(mode='project',field='question',basis=[asdict(self.req)],question='What needs clarification?',consent=True)
    def test_page_context_is_shared_only_and_advice_never_proposes_an_unselected_edit(self):
        before=self.store.latest(self.req.id,{SCOPE})
        result=self.w.command('field-coach',self.request())
        self.assertEqual(result['output']['suggested_wording'],'')
        self.assertNotIn('PRIVATE SECRET',str(self.model.calls))
        self.assertEqual(self.model.calls[0]['context']['question'],'What needs clarification?')
        self.assertEqual(self.store.latest(self.req.id,{SCOPE}),before)
    def test_blank_question_and_stale_page_stop_before_inference(self):
        d=self.request();d['question']=' '
        with self.assertRaises(ValueError):self.w.command('field-coach',d)
        d=self.request();self.store.put(self.req.id,'requirement',SCOPE,dict(title='Changed',text='New wording',status='proposed'),expected_revision=1)
        with self.assertRaises(StaleBasis):self.w.command('field-coach',d)
        self.assertFalse(self.model.calls)
    def test_page_changes_during_inference_do_not_store_current_advice(self):
        self.model.during=lambda:self.store.put(self.req.id,'requirement',SCOPE,dict(title='Changed',text='New wording',status='proposed'),expected_revision=1)
        with self.assertRaises(StaleBasis):self.w.command('field-coach',self.request())
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='field-coach-advice'").fetchone()[0],0)
    def test_shared_view_cannot_request_private_saved_sponsor_page(self):
        d=dict(mode='draft-page',field='question',question='Show private draft',expected=asdict(self.req),consent=True)
        with self.assertRaises(PermissionError):self.w.command('field-coach',d)
        self.assertFalse(self.model.calls)


    def test_page_followup_keeps_the_same_exact_shared_basis_and_excludes_private_material(self):
        data=self.request();first=self.w.command('field-coach',data)
        self.w.command('field-coach',{**data,'question':'What should we clarify first?','previous_advice':first['ref']})
        ctx=self.model.calls[-1]['context'];self.assertEqual(ctx['previous_exchange']['reply'],first['output'])
        self.assertEqual(ctx['shared_records'][0]['ref'],asdict(self.req));self.assertNotIn('PRIVATE SECRET',str(ctx))
        self.assertEqual(self.store.latest(self.req.id,{SCOPE})['body']['text'],'Retain handoff context.')

    def test_previous_advice_from_another_actor_is_unavailable_before_inference(self):
        first=self.w.command('field-coach',self.request())
        with self.assertRaises(PermissionError):Workspace(self.store,'sam',self.model).command('field-coach',{**self.request(),'previous_advice':first['ref']})
        self.assertEqual(len(self.model.calls),1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='field-coach-advice' AND scope='coach:sam'").fetchone()[0],0)

    def test_changed_shared_page_cannot_reuse_earlier_page_advice(self):
        first=self.w.command('field-coach',self.request())
        self.req=self.store.put(self.req.id,'requirement',SCOPE,dict(title='Shared handoff',text='Changed condition.',status='proposed'),expected_revision=1)
        with self.assertRaises(StaleBasis):self.w.command('field-coach',{**self.request(),'previous_advice':first['ref']})
        self.assertEqual(len(self.model.calls),1)

    def test_previous_exchange_counts_toward_the_combined_context_limit(self):
        refs=[self.req]
        for index in range(4):refs.append(self.store.put('REQ-PAGE-EXTRA-'+str(index),'requirement',SCOPE,dict(title='Synthetic condition '+str(index),text='x',status='proposed')))
        refs.sort(key=lambda raw:raw.id)
        data={**self.request(),'basis':[asdict(raw) for raw in refs]}
        ctx,_=self.w.field_coach.context(data);remaining=89900-len(json.dumps(ctx))
        self.assertGreater(remaining,0)
        updated=[]
        for raw in refs:
            row=self.store.read(raw,{SCOPE});body=deepcopy(row['body']);added=min(19000,remaining);body['text']+='x'*added;remaining-=added
            updated.append(self.store.put(raw.id,'requirement',SCOPE,body,expected_revision=raw.revision))
        self.assertEqual(remaining,0);data['basis']=[asdict(raw) for raw in updated]
        ctx,_=self.w.field_coach.context(data);self.assertLessEqual(len(json.dumps(ctx)),90000);self.assertGreater(len(json.dumps(ctx)),89500)
        first=self.w.command('field-coach',data)
        with self.assertRaisesRegex(ValueError,'earlier exchange makes this request too large'):
            self.w.command('field-coach',{**data,'previous_advice':first['ref']})
        self.assertEqual(len(self.model.calls),1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='field-coach-advice'").fetchone()[0],1)
        self.w.command('field-coach',data);self.assertEqual(len(self.model.calls),2)
