from brief_fixture import complete_design_brief
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store,Ref,StaleBasis
from workbench.decisions import SCOPE,DecisionBlocked
from workbench.domain import EDITABLE,GUARDRAILS
from workbench.workspace import Workspace
from workbench.model_provider import ModelUnavailable

class DomainTestModel:
    def __init__(self):self.calls=[];self.bad=None;self.during=None;self.fail=False
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='synthetic')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));c=kw['context']
        if self.during:self.during()
        if self.fail:raise ModelUnavailable('Synthetic failure')
        out=dict(summary='The observation is bounded; resumption conditions need clarification.',strengths=['Observation and interpretation are separated.'],suggestions=[dict(kind='downstream',direction='next-domain',edit=dict(field='downstream_needs',text='Investigate what information users need to resume after an interruption.'),issue='The observed interruption does not establish what users need to resume.',question='What information did participants need when returning?',basis='observation',quote=c['deliverable']['observation'][:100],requirement_ids=[r['ref']['id'] for r in c['requirements']])])
        if self.bad:self.bad(out)
        return dict(output=out,model='synthetic',usage=dict(input_tokens=50,output_tokens=40,total_tokens=90))

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.path);self.model=DomainTestModel()
        self.owner=Workspace(self.store,'alex');self.owner.setup(dict(title='Synthetic domain project',intent='Reduce repeated effort',boundary='Do not lose user work'))
        self.reqs=[]
        for title in ('Resume work','Recognize current priority'):
            id=self.owner.create_requirement(dict(title=title,text=title,rationale='User outcome',conditions='Scoped evaluation',drawer='Experience',acceptance_criteria='Observe task completion'))['id'];self.reqs.append(self.store.latest(id,{SCOPE})['ref'])
        self.sam=Workspace(self.store,'sam',self.model);self.lee=Workspace(self.store,'lee',self.model)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def payload(self,w=None):
        w=w or self.sam;p=w.domains.profile()
        return dict(title='Interrupted task finding',deliverable_type=p['config']['deliverable_types'][0],observation='Three participants lost their place after interruption.',source='Synthetic study, section 2',interpretation='Resumption may need clearer context.',recommendation='Investigate resumption information needs.',limitation='Three participants; no prevalence estimate.',source_refs=[],links=[dict(ref=asdict(r),relation='refines',rationale='Changes the resumption investigation') for r in self.reqs])
    def draft(self,w=None,p=None):
        w=w or self.sam;result=w.command('domain-save',p or self.payload(w));return self.store.latest(result['id'],w.scopes)
    def review(self,d,w=None):
        w=w or self.sam;r=w.command('domain-review',dict(expected=asdict(d['ref']),consent=True));return self.store.latest(r['domainReport'],w.scopes)
    def respond(self,r,w=None,action='deferred'):
        w=w or self.sam;out=w.command('domain-disposition',dict(expected=asdict(r['ref']),confirm=True,dispositions=[dict(action=action,rationale='Retain this as a focused follow-up') for _ in r['body']['output']['suggestions']]));return self.store.latest(out['domainReport'],w.scopes)
    def prepare(self,d,w=None,**extra):
        w=w or self.sam;complete_design_brief(w,d);result=w.command('domain-prepare',dict(expected=asdict(d['ref']),recipient='design' if w.actor=='sam' else 'research',**extra));return self.store.latest(result['domainHandoff'],w.scopes)
    def publish(self,d,r,w=None,**extra):
        w=w or self.sam
        if r:w.domains.checked_report(asdict(r['ref']))
        prepared=self.prepare(d,w)
        out=w.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(prepared['ref']),confirm=True,**extra));return self.store.latest(out['id'],{SCOPE})
    def test_design_uses_selected_published_findings_with_exact_lineage(self):
        published=self.publish(self.draft(),None)
        unselected=self.publish(self.draft(p={**self.payload(),'title':'Unrelated finding'}),None)
        private=self.draft(p={**self.payload(),'title':'Private draft'})
        before=[self.store.latest(ref.id,{SCOPE}) for ref in self.reqs]
        data={**self.payload(self.lee),'title':'Resume flow proposal','input_refs':[asdict(published['ref'])]}
        design=self.draft(self.lee,data)
        self.model.bad=lambda out:out['suggestions'][0].update(
            basis=published['ref'].id,quote=published['body']['observation'])
        report=self.review(design,self.lee)
        context=self.model.calls[-1]['context']
        self.assertEqual(context['upstream_contributions'][0]['ref'],asdict(published['ref']))
        self.assertEqual(context['upstream_contributions'][0]['body']['limitation'],published['body']['limitation'])
        self.assertNotIn(unselected['ref'].id,str(context))
        self.assertNotIn(private['ref'].id,str(context))
        self.assertIn(published['ref'].id,self.model.calls[-1]['schema']['properties']['suggestions']['items']['properties']['basis']['enum'])
        shared=self.publish(design,report,self.lee)
        self.assertEqual(shared['body']['input_refs'],[asdict(published['ref'])])
        packet=self.store.resolve_packet('PKT-'+shared['ref'].id,1,{SCOPE})
        self.assertIn(published['ref'],[record['ref'] for record in packet['records']])
        self.assertEqual([self.store.latest(ref.id,{SCOPE}) for ref in self.reqs],before)
        self.assertEqual(self.store.read(published['ref'],{SCOPE}),published)

    def test_inputs_reject_private_work_wrong_kinds_and_conflicting_versions(self):
        private=self.draft()
        with self.assertRaises(PermissionError):
            self.draft(self.lee,{**self.payload(self.lee),'input_refs':[asdict(private['ref'])]})
        for values in ([asdict(self.reqs[0])],{},[asdict(self.reqs[0])]*21):
            with self.assertRaises(ValueError):
                self.draft(self.lee,{**self.payload(self.lee),'input_refs':values})
        published=self.publish(private,None)
        newer=self.store.put(published['ref'].id,'contribution',SCOPE,published['body'],published['ref'].revision)
        with self.assertRaises(ValueError):
            self.draft(self.lee,{**self.payload(self.lee),'input_refs':[asdict(published['ref']),asdict(newer)]})
        with self.assertRaises(StaleBasis):
            self.draft(self.lee,{**self.payload(self.lee),'input_refs':[asdict(published['ref'])]})

    def test_input_changes_stale_advice_and_preflight_keep_history_and_require_explicit_refresh(self):
        published=self.publish(self.draft(),None)
        data={**self.payload(self.lee),'input_refs':[asdict(published['ref'])]}
        design=self.draft(self.lee,data)
        report=self.review(design,self.lee)
        prepared=self.prepare(design,self.lee)
        newer=self.store.put(published['ref'].id,'contribution',SCOPE,
            {**published['body'],'observation':'Revised Research finding'},published['ref'].revision)
        with self.assertRaises(StaleBasis):self.lee.domains.checked_report(asdict(report['ref']))
        with self.assertRaises(StaleBasis):
            self.lee.command('domain-publish',dict(expected=asdict(design['ref']),preflight=asdict(prepared['ref']),confirm=True))
        current=self.lee.domains.state()
        self.assertEqual(current['input_versions'][0]['ref'],published['ref'])
        self.assertEqual(current['input_versions'][0]['body']['observation'],published['body']['observation'])
        self.assertFalse(current['handoffs'][0]['current'])
        with self.assertRaises(StaleBasis):
            self.draft(self.lee,{**self.payload(self.lee),'expected':asdict(design['ref'])})
        refreshed=self.draft(self.lee,{**data,'expected':asdict(design['ref']),'input_refs':[asdict(newer)]})
        self.assertEqual(self.lee.domains.context(asdict(refreshed['ref']))['upstream_contributions'][0]['ref'],asdict(newer))
        self.assertEqual(self.store.read(design['ref'],self.lee.scopes)['body']['input_refs'],[asdict(published['ref'])])

    def test_old_edit_call_preserves_selected_inputs_and_unrelated_work_does_not_stale_review(self):
        published=self.publish(self.draft(),None)
        design=self.draft(self.lee,{**self.payload(self.lee),'input_refs':[asdict(published['ref'])]})
        changed=self.draft(self.lee,{**self.payload(self.lee),'expected':asdict(design['ref']),'interpretation':'Author revision'})
        self.assertEqual(changed['body']['input_refs'],[asdict(published['ref'])])
        report=self.review(changed,self.lee)
        self.publish(self.draft(p={**self.payload(),'title':'Unrelated new finding'}),None)
        self.assertEqual(self.review(changed,self.lee)['ref'],report['ref'])

    def test_changed_input_during_design_coaching_is_rejected(self):
        published=self.publish(self.draft(),None)
        design=self.draft(self.lee,{**self.payload(self.lee),'input_refs':[asdict(published['ref'])]})
        def change():
            self.store.put(published['ref'].id,'contribution',SCOPE,published['body'],published['ref'].revision)
        self.model.during=change
        with self.assertRaises(StaleBasis):self.review(design,self.lee)
        self.assertEqual(self.lee.domains.reports(),[])
        self.assertEqual(self.lee.domains.state()['runs'][0]['body']['status'],'stale')

    def test_shared_runtime_supports_research_and_design_with_different_configuration(self):
        for w in (self.sam,self.lee):
            d=self.draft(w);r=self.review(d,w);self.respond(r,w)
            call=self.model.calls[-1];self.assertEqual(call['context']['domain_profile']['key'],w.domains.key)
            self.assertIn('observation',call['schema']['properties']['suggestions']['items']['properties']['basis']['enum']);self.assertEqual(call['instructions'],GUARDRAILS);self.assertEqual(self.store.latest(d['ref'].id,w.scopes),d)
        self.assertNotEqual(self.model.calls[0]['context']['domain_profile']['config']['criteria'],self.model.calls[1]['context']['domain_profile']['config']['criteria'])
    def test_configuration_changes_affect_next_request_and_stale_old_report(self):
        d=self.draft();r=self.respond(self.review(d));p=self.sam.domains.profile();cfg={k:deepcopy(p['config'][k]) for k in EDITABLE};cfg['coach_guidance']='Focus on interruptions and recovery evidence.'
        self.sam.command('domain-configure',dict(domain='research',expected=p['ref'],config=cfg,reason='SME refinement'))
        with self.assertRaises(StaleBasis):self.publish(d,r)
        self.review(d);self.assertEqual(self.model.calls[-1]['context']['domain_profile']['config']['coach_guidance'],cfg['coach_guidance'])
        self.assertEqual(self.store.read(r['ref'],self.sam.scopes)['body']['configuration'],r['body']['configuration'])
    def test_config_optimistic_concurrency_authority_and_fixed_permissions(self):
        p=self.sam.domains.profile();data=dict(domain='research',expected=p['ref'],config={k:p['config'][k] for k in EDITABLE},reason='Explicit update')
        with self.assertRaises(PermissionError):self.lee.command('domain-configure',data)
        bad=deepcopy(data);bad['config']['authors']=['lee']
        with self.assertRaises(ValueError):self.sam.command('domain-configure',bad)
        self.sam.command('domain-configure',data)
        with self.assertRaises(StaleBasis):self.sam.command('domain-configure',data)
        self.assertEqual(self.sam.domains.profile()['config']['authors'],['sam'])
    def test_deferral_or_rejection_permits_publication_without_requirement_changes(self):
        for action in ('rejected','deferred','accepted'):
            before=[self.store.latest(r.id,{SCOPE}) for r in self.reqs];d=self.draft();report=self.respond(self.review(d),action=action);published=self.publish(d,report)
            self.assertEqual(published['body']['status'],'published-for-review');self.assertEqual([self.store.latest(r.id,{SCOPE}) for r in self.reqs],before)
            self.assertEqual(published['body']['links'],d['body']['links'])
            with self.assertRaises(DecisionBlocked):self.publish(d,report)
    def test_preflight_required_but_coaching_and_full_disposition_are_optional(self):
        d=self.draft();r=self.review(d)
        with self.assertRaises((ValueError,PermissionError)):self.sam.command('domain-publish',dict(expected=asdict(d['ref']),report=asdict(r['ref']),confirm=True))
        with self.assertRaises(ValueError):self.sam.command('domain-disposition',dict(expected=asdict(r['ref']),dispositions=[]))
        pub=self.publish(d,r);self.assertEqual(pub['body']['preflight']['mode'],'system-checks')
        other=self.draft();self.model.fail=True;before=len(self.model.calls);self.publish(other,None);self.assertEqual(len(self.model.calls),before)
    def test_old_save_endpoint_cannot_strip_chassis_and_bypass_review(self):
        d=self.draft();p=self.payload();p['expected']=asdict(d['ref'])
        with self.assertRaises(DecisionBlocked):self.sam.save_contribution(p)
    def test_unattached_finding_is_preserved_and_can_publish(self):
        p=self.payload();p['links']=[];d=self.draft(p=p);report=self.respond(self.review(d));pub=self.publish(d,report)
        self.assertEqual(pub['body']['requirement_refs'],[]);self.assertEqual(pub['body']['observation'],p['observation'])
    def test_source_import_is_private_deduplicated_and_publication_requires_release(self):
        data=dict(title='Synthetic transcript',text='Participant stopped the task and could not find their previous place.')
        source=self.sam.command('domain-source',data)['ref'];self.assertEqual(self.sam.command('domain-source',data)['ref'],source)
        with self.assertRaises(PermissionError):self.store.read(Ref(**source),self.lee.scopes)
        p=self.payload();p['source_refs']=[source];d=self.draft(p=p);r=self.respond(self.review(d))
        self.assertEqual(self.model.calls[-1]['context']['sources'][0]['body']['text'],data['text'])
        with self.assertRaises(PermissionError):self.publish(d,r)
        self.assertFalse(self.sam.latest_records('contribution'))
        pub=self.publish(d,r,release_sources=True);released=self.store.read(Ref(**pub['body']['source_refs'][0]),{SCOPE});self.assertEqual(released['body']['text'],data['text']);self.assertEqual(released['body']['source_version'],source)
        packet=self.store.resolve_packet('PKT-'+pub['ref'].id,1,{SCOPE});self.assertIn(released['ref'],[x['ref'] for x in packet['records']])
    def test_cross_domain_authoring_and_review_data_are_private(self):
        d=self.draft();r=self.review(d)
        with self.assertRaises(PermissionError):self.lee.command('domain-save',{**self.payload(self.lee),'expected':asdict(d['ref'])})
        with self.assertRaises(PermissionError):self.lee.command('domain-disposition',dict(expected=asdict(r['ref']),confirm=True,dispositions=[]))
        for actor in ('priya','alex','lee','maya'):
            state=Workspace(self.store,actor,self.model).state();ids={x['ref'].id for x in state['records']};self.assertNotIn(r['ref'].id,ids);self.assertNotIn(d['ref'].id,ids)
        run=self.sam.domains.state()['runs'][0];self.assertEqual(run['body']['mode'],'simulated');self.assertNotIn('context',run['body'])
        self.assertEqual(Workspace(self.store,'priya',self.model).state()['agent_monitoring']['runs'],[])
        metrics=Workspace(self.store,'administrator',self.model,admin=True).state()['agent_monitoring'];entry=next(x for x in metrics['runs'] if x['persona_id']=='P06');self.assertNotIn('context',entry);self.assertNotIn('output',entry);self.assertNotIn('instructions',entry)
    def test_changed_draft_and_requirements_invalidate_old_review(self):
        d=self.draft();r=self.respond(self.review(d));p=self.payload();p.update(expected=asdict(d['ref']),observation='A revised observation');new=self.draft(p=p)
        with self.assertRaises(StaleBasis):self.publish(d,r)
        new_r=self.respond(self.review(new));req=self.store.read(self.reqs[0],{SCOPE});self.store.put(req['ref'].id,'requirement',SCOPE,req['body'],req['ref'].revision)
        with self.assertRaises(StaleBasis):self.publish(new,new_r)
    def test_unrelated_changes_reuse_review_but_explicit_rerun_is_possible(self):
        d=self.draft();r=self.review(d);self.store.put('UNRELATED','note',SCOPE,dict(text='Unrelated'))
        cached=self.review(d);self.assertEqual(cached['ref'],r['ref']);self.assertEqual(len(self.model.calls),1)
        self.sam.command('domain-review',dict(expected=asdict(d['ref']),consent=True,rerun=True));self.assertEqual(len(self.model.calls),2)
    def test_change_during_generation_is_rejected_and_receipted(self):
        d=self.draft()
        def change():
            req=self.store.read(self.reqs[0],{SCOPE});self.store.put(req['ref'].id,'requirement',SCOPE,req['body'],req['ref'].revision)
        self.model.during=change
        with self.assertRaises(StaleBasis):self.review(d)
        self.assertEqual(self.sam.domains.reports(),[]);self.assertEqual(self.sam.domains.state()['runs'][0]['body']['status'],'stale')
    def test_model_failure_or_false_quote_never_falls_back_or_edits(self):
        d=self.draft();self.model.fail=True
        with self.assertRaises(ModelUnavailable):self.review(d)
        self.model.fail=False;self.model.bad=lambda out:out['suggestions'][0].update(quote='Invented quotation')
        with self.assertRaises(ModelUnavailable):self.review(d)
        self.assertEqual(self.sam.domains.reports(),[]);self.assertEqual(self.store.latest(d['ref'].id,self.sam.scopes),d)
        self.assertTrue(all(r['body']['status']=='failed' for r in self.sam.domains.state()['runs']))
    def test_source_and_goal_changes_invalidate_exact_context(self):
        g=self.store.put('G-test','goal',SCOPE,dict(title='Reduce repeated effort',measure_refs=[]))
        req=self.store.read(self.reqs[0],{SCOPE});req['body']['goal_refs']=[asdict(g)];self.reqs[0]=self.store.put(req['ref'].id,'requirement',SCOPE,req['body'],req['ref'].revision)
        d=self.draft();r=self.respond(self.review(d));self.assertEqual(self.model.calls[-1]['context']['goals_and_measures'][0]['ref'],asdict(g))
        self.store.put(g.id,'goal',SCOPE,dict(title='Refined goal'),g.revision)
        with self.assertRaises(StaleBasis):self.publish(d,r)
    def test_design_and_research_review_can_reach_human_requirement_decision(self):
        pubs=[]
        for w in (self.sam,self.lee):
            d=self.draft(w);r=self.respond(self.review(d,w),w);pubs.append(self.publish(d,r,w))
        out=self.owner.submit_proposal(dict(target=asdict(self.reqs[0]),selected=[asdict(p['ref']) for p in pubs],text='Users can resume their task with context',acceptance_criteria='Observe successful resumption',conditions='Scoped evaluation',rationale='Research and Design evidence',changes_intent=False));id=out['id']
        self.assertEqual(set(self.owner.loop.case(id)['body']['required_reviews']),{'sam','lee'})
        with self.assertRaises(PermissionError):Workspace(self.store,'maya').review(dict(expected=asdict(self.owner.loop.case(id)['ref']),disposition='cleared-with-conditions',rationale='Wrong reviewer'))
        for actor,disposition in [('sam','supported-with-limits'),('lee','cleared-with-conditions')]:Workspace(self.store,actor).review(dict(expected=asdict(self.owner.loop.case(id)['ref']),disposition=disposition,rationale='Within the evidence limits'))
        state=self.owner.state();self.assertTrue(next(c for c in state['cases'] if c['ref'].id==id)['ready'])
        self.owner.decide(dict(expected=asdict(self.owner.loop.case(id)['ref']),disposition='approve',rationale='Agreed within scope',confirm=True))
        self.assertEqual(self.store.latest(self.reqs[0].id,{SCOPE})['body']['status'],'approved');self.assertEqual(self.store.latest(self.reqs[1].id,{SCOPE})['ref'],self.reqs[1])
    def test_history_survives_reopen(self):
        d=self.draft();r=self.respond(self.review(d));self.publish(d,r);self.store.close();self.store=Store(self.path);w=Workspace(self.store,'sam',self.model)
        self.assertTrue(w.domains.state()['reports'][0]['current']);self.assertEqual(self.store.read(d['ref'],w.scopes)['body'],d['body'])

    def test_followup_carries_only_explicit_previous_exchange_and_current_draft(self):
        d=self.draft();r=self.review(d);p=self.payload();p.update(expected=asdict(d['ref']),observation='Two participants resumed after finding their last action.');new=self.draft(p=p)
        result=self.sam.command('domain-coach',dict(expected=asdict(new['ref']),previous=asdict(r['ref']),question='Does this change the interpretation?',consent=True))
        ctx=self.model.calls[-1]['context'];self.assertEqual(ctx['question'],'Does this change the interpretation?');self.assertEqual(ctx['previous_exchange']['draft'],asdict(d['ref']));self.assertEqual(ctx['deliverable']['observation'],p['observation'])
        self.assertNotEqual(result['domainReport'],r['ref'].id);self.assertEqual(self.store.read(d['ref'],self.sam.scopes),d)
        unrelated=self.draft()
        with self.assertRaises(ValueError):self.sam.command('domain-coach',dict(expected=asdict(unrelated['ref']),previous=asdict(r['ref']),consent=True))
    def test_suggested_edit_is_explicit_editable_versioned_and_invalidates_preflight(self):
        d=self.draft();r=self.review(d);h=self.prepare(d)
        data=dict(expected=asdict(d['ref']),report=asdict(r['ref']),index=0,text='Clarify which task cues users need when they return.')
        with self.assertRaises(ValueError):self.sam.command('domain-apply-advice',data)
        result=self.sam.command('domain-apply-advice',{**data,'confirm':True});new=self.store.latest(result['id'],self.sam.scopes)
        self.assertEqual(new['ref'].revision,2);self.assertEqual(new['body']['downstream_needs'],data['text']);self.assertEqual(new['body']['observation'],d['body']['observation']);self.assertEqual(self.store.read(d['ref'],self.sam.scopes),d)
        with self.assertRaises(StaleBasis):self.sam.command('domain-apply-advice',{**data,'confirm':True})
        with self.assertRaises(StaleBasis):self.sam.command('domain-publish',dict(expected=asdict(new['ref']),preflight=asdict(h['ref']),confirm=True))
        self.assertEqual(len(self.sam.latest_records('domain-coach-edit')),1)
    def test_preflight_packages_human_notes_without_inference_and_private_coaching(self):
        d=self.draft();r=self.review(d);count=len(self.model.calls)
        h=self.prepare(d,intent_implications='Reconsider resumption as part of the intended outcome.',downstream_needs='Design should investigate recovery cues.',open_questions='Which cues are sufficient?')
        self.assertEqual(len(self.model.calls),count);self.assertFalse(self.sam.latest_records('contribution'))
        pub=self.sam.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True));b=self.store.latest(pub['id'],{SCOPE})['body']
        self.assertEqual(b['handoff'],h['body']['handoff']);self.assertNotIn('output',b);self.assertNotIn('dispositions',b);self.assertNotIn('open_questions',b)
        self.assertEqual(self.store.read(d['ref'],self.sam.scopes),d)
        for actor in ('priya','alex','lee'):
            with self.assertRaises(PermissionError):self.store.read(h['ref'],Workspace(self.store,actor).scopes)
    def test_preflight_is_invalidated_by_config_and_published_intent_changes(self):
        d=self.draft();h=self.prepare(d);intent=self.sam.latest_records('intent')[0]
        self.store.put(intent['ref'].id,intent['kind'],intent['scope'],{**intent['body'],'text':'A revised outcome'},intent['ref'].revision)
        with self.assertRaises(StaleBasis):self.sam.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True))
        h=self.prepare(d);p=self.sam.domains.profile();config={k:p['config'][k] for k in EDITABLE};config['coach_guidance']='Refined method'
        self.sam.command('domain-configure',dict(domain='research',expected=p['ref'],config=config,reason='Refine method'))
        with self.assertRaises(StaleBasis):self.sam.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True))
    def test_changed_handoff_can_be_republished_but_identical_commit_is_rejected(self):
        d=self.draft();h=self.prepare(d,open_questions='Original question')
        def publish(h):return self.sam.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True))
        first=publish(h)
        with self.assertRaises(DecisionBlocked):publish(h)
        h2=self.prepare(d,open_questions='Revised question');second=publish(h2)
        self.assertEqual(first['id'],second['id']);self.assertEqual(self.store.latest(first['id'],{SCOPE})['ref'].revision,2)
        self.assertEqual(self.store.read(Ref(first['id'],1),{SCOPE})['body']['handoff']['open_questions'],'Original question')
    def test_partial_notes_and_historical_dispositions_remain_separate_from_work(self):
        d=self.draft();r=self.review(d)
        result=self.sam.command('domain-disposition',dict(expected=asdict(r['ref']),dispositions=[dict(action='',rationale='Need to discuss with the researcher')]))
        r=self.store.latest(result['domainReport'],self.sam.scopes);self.assertFalse(r['body']['reviewed']);self.assertEqual(self.store.latest(d['ref'].id,self.sam.scopes),d)
        self.assertEqual(r['body']['dispositions']['0']['rationale'],'Need to discuss with the researcher')
        new=self.draft(p={**self.payload(),'expected':asdict(d['ref']),'interpretation':'Revised interpretation'})
        self.respond(r,action='rejected');self.assertEqual(self.store.latest(new['ref'].id,self.sam.scopes),new)
    def test_invalid_edit_or_direction_never_changes_work(self):
        d=self.draft()
        for bad in (lambda o:o['suggestions'][0].update(direction='approved'),lambda o:o['suggestions'][0].update(edit=dict(field='permission',text='Widen access'))):
            self.model.bad=bad
            with self.assertRaises(ModelUnavailable):self.review(d)
        self.assertEqual(self.store.latest(d['ref'].id,self.sam.scopes),d)
    def test_legacy_review_history_is_preserved_and_cannot_substitute_for_preflight(self):
        d=self.draft();r=self.review(d);old=self.store.put('PREFLIGHT-historical','domain-preflight',self.sam.domains.scope,{**r['body'],'at':'2026-01-01T00:00:00+00:00'})
        self.assertIn(old,[x['ref'] for x in self.sam.domains.state()['reports']])
        with self.assertRaises(PermissionError):self.sam.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(old),confirm=True))
