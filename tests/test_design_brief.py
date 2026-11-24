"""Synthetic contract checks; no claim of general design reasoning quality."""
from copy import deepcopy
from dataclasses import asdict
import unittest
import test_project_flow as flow
from workbench.workspace import Workspace
from workbench.core import StaleBasis
from workbench.decisions import SCOPE
from workbench.model_provider import ModelUnavailable
from workbench.domain_brief import schema

class DesignBriefModel(flow.ObjectiveModel):
    def __init__(self):self.calls=0;self.bad=None;self.during=None
    def generate(self,**kw):
        self.calls+=1
        result=super().generate(**kw);c=kw['context']
        if not c.get('include_design_brief'):return result
        req=c['requirements'][0]['ref']['id'];intent=next(e['evidence_id'] for e in c['evidence_excerpts'] if e['id']=='INT-001');rquote=next(e['evidence_id'] for e in c['evidence_excerpts'] if e['id']==req)
        research=next((e['evidence_id'] for e in c['evidence_excerpts'] if e['id']=='PUB-RESEARCH'),intent)
        def item(kind,title,quote,ids):return dict(kind=kind,title=title,text='Explore interrupted reporting with recoverable draft states.',rationale='The supplied context identifies reporting interruptions; effectiveness remains unvalidated.',requirement_ids=ids,basis_links=[dict(evidence_id=quote)])
        result['output']['brief_sections']=[item('purpose','Preserve interrupted work',intent,[]),item('requirement-implication','Explore save and recovery states',rquote,[req]),item('validation','Test interruption recovery',research,[req])]
        result['output']['brief_sections'].extend(item(kind,title,research,[]) for kind,title in [('scope','Scope and exclusions'),('users-and-tasks','Receptionist tasks and states'),('deliverable','Prototype deliverable'),('evidence-and-dependencies','Evidence and dependencies')])
        if self.bad=='quote':result['output']['brief_sections'][0]['basis_links']=[dict(evidence_id='PRIVATE-UNKNOWN')]
        if self.bad=='requirement':result['output']['brief_sections'][1]['basis_links']=[dict(evidence_id=research)]
        if self.bad=='empty':result['output']['brief_sections']=[]
        return result

class DesignBriefTests(unittest.TestCase):
    def test_older_full_context_signatures_remain_current_without_rewriting_the_plan(self):
        from workbench.decisions import fingerprint
        self.seed();legacy=self.design.domain_brief.context(include_brief=True,projection_version=0);plan=self.generate()
        old={**plan,'body':{**plan['body'],'signature':fingerprint(legacy)}};old['body'].pop('context_projection_version',None)
        before=self.store.db.execute('select count(*) from records').fetchone()[0]
        self.assertTrue(self.design.domain_brief.current(old))
        self.assertEqual(self.store.db.execute('select count(*) from records').fetchone()[0],before)
    setUp=flow.ProjectFlowTests.setUp
    tearDown=flow.ProjectFlowTests.tearDown
    def seed(self):
        self.research=self.store.put('PUB-RESEARCH','contribution',SCOPE,dict(domain_key='research',domain='Research',owner='sam',title='Fictional interruption study',observation='Participants paused fictional feedback while seeking supporting evidence.',recommendation='Explore a saved draft state when evidence is not ready.',limitation='Fictional small study; prevalence and business impact are unvalidated.',handoff=dict(downstream_needs='Show draft retained separately from submission confirmed.',open_questions='Who owns follow-up on missing evidence?'),requirement_refs=[asdict(self.req['ref'])]))
        self.store.put('PRIVATE-STUDY','domain-source','domain:research',dict(title='Private transcript',text='Never send this private Research transcript.'))
        self.model=DesignBriefModel();self.design=Workspace(self.store,'lee',self.model)
    def generate(self):
        self.preview=self.design.command('domain-brief-preview',{})
        self.design.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=self.preview['signature']))
        return self.design.domain_brief.state()[0]
    def payload(self,r):
        return dict(expected=asdict(r['ref']),objectives=deepcopy(r['body'].get('objectives',r['body']['output']['objectives'])),brief_sections=[{**s,'disposition':'proposed'} for s in r['body'].get('brief_sections',r['body']['output']['brief_sections'])])
    def test_incoming_user_context_uses_pinned_intake_not_newer_claims_or_private_work(self):
        self.seed()
        prior=self.store.latest('INT-001',{SCOPE})
        intake=dict(beneficiaries='Receptionists and local supervisors',jobs='Restore productive work while the original issue stays visible.',user_situation='An issue interrupts a task or crosses a shift.',user_actions='Identify, request help, hand off, confirm outcome.',need='Ownership disappears after handoff.',bottlenecks='People repeat context through separate tools.',gains='Know the current owner and next action.',constraints='Existing authority stays in its governed system.',dependencies='Agree which system provides each status event.')
        self.store.put('INT-001','intent',SCOPE,{**prior['body'],'intake':intake},prior['ref'].revision)
        plan=self.generate();calls=self.model.calls
        old=self.store.latest('INT-001',{SCOPE});self.store.put('INT-001','intent',SCOPE,{**old['body'],'intake':{**intake,'jobs':'A NEW UNREVIEWED CLAIM'}},old['ref'].revision)
        before=self.store.db.execute('SELECT count(*) FROM records').fetchone()[0]
        groups=self.design.domain_brief.incoming_context(plan)
        self.assertIn(intake['jobs'],str(groups));self.assertNotIn('A NEW UNREVIEWED CLAIM',str(groups));self.assertNotIn('PRIVATE-STUDY',str(groups))
        self.assertEqual(groups[0]['items'][0]['ref'],asdict(old['ref']));self.assertEqual(self.model.calls,calls)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM records').fetchone()[0],before)
    def test_missing_user_context_remains_empty_instead_of_becoming_model_expertise(self):
        self.seed();plan=self.generate();groups=self.design.domain_brief.incoming_context(plan)
        self.assertEqual([g['title'] for g in groups],['People and job','Situation and triggers','Pains and obstacles','Gains sought','Boundaries and dependencies'])
        self.assertTrue(any(not g['items'] for g in groups));self.assertNotIn('Professional approach',str(groups))

    def test_preview_is_deterministic_private_and_preserves_exact_upstream_and_criteria(self):
        self.seed();out=self.design.command('domain-brief-preview',{})
        self.assertEqual(self.model.calls,0);self.assertEqual(out['inputs']['research_count'],1)
        direction=next(x for x in out['inputs']['upstream'] if x['ref']['id']=='PUB-RESEARCH')
        self.assertIn('Show draft retained separately from submission confirmed.',str(direction));self.assertIn('prevalence',str(direction));self.assertEqual(out['inputs']['requirements'][0]['acceptance_criteria'],'Show evidence pending.')
        self.assertNotIn('PRIVATE-STUDY',str(out));self.assertNotIn('private Research transcript',str(out))
        self.assertIn('inputs',self.sam.command('domain-brief-preview',{}))
    def test_unpreviewed_or_changed_inputs_stop_before_model_call(self):
        self.seed()
        with self.assertRaises(StaleBasis):self.design.command('domain-objectives-suggest',dict(consent=True,include_brief=True))
        preview=self.design.command('domain-brief-preview',{})
        old=self.store.latest('PUB-RESEARCH',{SCOPE});self.store.put('PUB-RESEARCH','contribution',SCOPE,{**old['body'],'recommendation':'Revised recommendation for a later study.'},old['ref'].revision)
        with self.assertRaises(StaleBasis):self.design.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
        self.assertEqual(self.model.calls,0)
    def test_complete_proposal_keeps_canonical_sources_distinct_and_is_not_automatically_used(self):
        self.seed();before=self.store.latest(self.req['ref'].id,{SCOPE});r=self.generate()
        self.assertTrue(r['body']['include_design_brief']);self.assertEqual(r['body']['status'],'suggested');self.assertEqual(r['body']['mode'],'simulated')
        self.assertEqual(r['body']['output']['brief_sections'][1]['basis_links'][0]['id'],self.req['ref'].id)
        self.assertNotIn('PRIVATE-STUDY',str(self.model.context));self.assertNotIn(r['ref'].id,str(self.sam.domain_brief.state()))
        t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);ctx,_=self.design.domain_chat.basis(t,self.design.domain_chat.plan(t)[0]);self.assertNotIn('working_design_brief',ctx)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)
    def test_author_choices_and_edits_persist_feed_current_chat_and_cannot_forge_lineage(self):
        self.seed();r=self.generate();data=self.payload(r);data['brief_sections'][0].update(text='Designer refined the purpose to protect entered feedback.',disposition='use',basis_links=[dict(id='FORGED',revision=9,quote='Not a source')]);data['brief_sections'][3]['disposition']='question';data['brief_sections'][2]['disposition']='omit'
        original=deepcopy(r['body']['output']);self.design.command('domain-objectives-save',data);saved=self.design.domain_brief.state()[0]
        self.assertEqual(self.model.calls,1);self.assertEqual(saved['body']['output'],original);self.assertNotIn('FORGED',str(saved));self.assertEqual(saved['body']['brief_sections'][0]['text'],data['brief_sections'][0]['text'])
        t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);ctx,_=self.design.domain_chat.basis(t,self.design.domain_chat.plan(t)[0]);working=ctx['working_design_brief']
        self.assertEqual(len(working['adopted']),1);self.assertEqual(len(working['questions']),1);self.assertNotIn('Test interruption recovery',str(working));self.assertIn(asdict(saved['ref']),ctx['basis'])
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.');self.assertFalse(self.design.bridge.issues())
        with self.assertRaises(StaleBasis):self.design.command('domain-objectives-save',data)
        from workbench.core import Store
        self.store.close();self.store=Store(self.path);reopened=Workspace(self.store,'lee');self.assertEqual(reopened.domain_brief.state()[0]['body']['brief_sections'],saved['body']['brief_sections'])
    def test_plan_only_save_preserves_read_only_interpretation_and_separates_coach_context(self):
        self.seed();r=self.generate();original=deepcopy(r['body']['output']['brief_sections'][1]);data=self.payload(r)
        data['brief_sections']=[{**s,'id':'section-'+str(i)} for i,s in enumerate(data['brief_sections']) if s['kind']!='requirement-implication']
        data['brief_sections'][0].update(text='Use two recoverable prototype variants.',disposition='use')
        self.design.command('domain-objectives-save',data);saved=self.design.domain_brief.state()[0]
        interpretation=next(s for s in saved['body']['brief_sections'] if s['kind']=='requirement-implication')
        self.assertEqual({k:interpretation[k] for k in original},original)
        t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);ctx,_=self.design.domain_chat.basis(t,self.design.domain_chat.plan(t)[0])
        self.assertEqual(ctx['working_design_brief']['interpretations'],[interpretation]);self.assertEqual(len(ctx['working_design_brief']['adopted']),1)
        self.assertEqual(self.design.domain_brief.public_body({**saved,'body':{**saved['body'],'completed_by':'lee','completed_at':'fictional'}})['brief_sections'][-1],interpretation)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.')
    def test_interpretation_tampering_is_rejected_atomically_and_new_sections_must_be_plan(self):
        self.seed();r=self.generate()
        for key,value in [('text','Rewrite the incoming meaning'),('kind','validation'),('disposition','use'),('requirement_ids',[])]:
            data=self.payload(r);data['brief_sections'][1][key]=value
            with self.subTest(field=key),self.assertRaisesRegex(ValueError,'read only'):self.design.command('domain-objectives-save',data)
            self.assertEqual(self.design.domain_brief.state()[0]['ref'],r['ref'])
        data=self.payload(r);data['brief_sections'].append(dict(id='new-incoming',kind='requirement-implication',title='Forged meaning',text='A changed interpretation.',rationale='Not supplied.',requirement_ids=[],disposition='use'))
        with self.assertRaises(ValueError):self.design.command('domain-objectives-save',data)
    def test_configured_domain_knowledge_is_supplied_to_plan_generation(self):
        self.seed();r=self.generate()
        self.assertEqual(self.model.context['domain_profile'],r['body']['profile'])
        self.assertIn('knowledge_entries',self.model.context['domain_profile'])
        from workbench.domain import DOMAINS
        DESIGN_INSTRUCTIONS=DOMAINS['design']['brief_guidance']
        self.assertIn('observable evaluation criteria',DESIGN_INSTRUCTIONS);self.assertIn('Do not merely restate requirements',DESIGN_INSTRUCTIONS)

    def test_main_chat_can_coach_unadopted_brief_without_applying_or_publishing_it(self):
        self.seed();r=self.generate();t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation'])
        ctx,_=self.design.domain_chat.basis(t,self.design.domain_chat.plan(t)[0]);brief=ctx['brief_for_coaching']
        self.assertEqual(brief['ref'],asdict(r['ref']));self.assertEqual(brief['status'],'suggested')
        self.assertEqual(len(brief['interpretations']),1);self.assertEqual(len(brief['plan']),6)
        self.assertIn('unadopted',brief['boundary']);self.assertNotIn('working_design_brief',ctx)
        self.assertEqual(self.design.domain_brief.state()[0],r);self.assertFalse(self.design.bridge.issues())

    def test_unsupported_basis_missing_structure_and_model_inference_cannot_be_saved_as_requirement(self):
        self.seed()
        for bad in ['quote','requirement','empty']:
            with self.subTest(bad=bad):
                self.model.bad=bad
                with self.assertRaises(ModelUnavailable):self.generate()
                self.assertFalse(self.design.domain_brief.state());self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.')
    def test_changed_source_during_drafting_or_after_adoption_invalidates_only_guidance(self):
        self.seed();r=self.generate();data=self.payload(r);data['brief_sections'][0]['disposition']='use';self.design.command('domain-objectives-save',data)
        old=self.store.latest('PUB-RESEARCH',{SCOPE});self.store.put('PUB-RESEARCH','contribution',SCOPE,{**old['body'],'observation':'A revised fictional finding requires reconsideration.'},old['ref'].revision)
        self.assertFalse(self.design.domain_brief.state()[0]['current'])
        t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);ctx,_=self.design.domain_chat.basis(t,self.design.domain_chat.plan(t)[0]);self.assertIn('earlier_inputs',ctx['brief_for_coaching'])
        self.assertEqual(self.store.read(r['ref'],self.design.scopes)['body']['status'],'suggested')
        preview=self.design.command('domain-brief-preview',{});self.model.during=lambda:self.store.put('PUB-RESEARCH','contribution',SCOPE,{**old['body'],'observation':'Changed while model was preparing its proposal.'},old['ref'].revision+1)
        with self.assertRaises(StaleBasis):self.design.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
    def test_invalid_disposition_and_changed_section_count_are_rejected_atomically(self):
        self.seed();r=self.generate();data=self.payload(r);data['brief_sections'][0]['disposition']='approve-requirement'
        with self.assertRaises(ValueError):self.design.command('domain-objectives-save',data)
        data=self.payload(r);data['brief_sections']*=4
        with self.assertRaises(ValueError):self.design.command('domain-objectives-save',data)
        self.assertEqual(self.design.domain_brief.state()[0]['ref'],r['ref'])
    def test_research_objective_contract_remains_compatible_and_does_not_generate_design_sections(self):
        m=DesignBriefModel();w=Workspace(self.store,'sam',m);w.command('domain-objectives-suggest',dict(consent=True));r=w.domain_brief.state()[0]
        self.assertNotIn('brief_sections',r['body']['output']);self.assertNotIn('include_design_brief',r['body'])
        self.assertNotIn('brief_sections',schema(w.domain_brief.context())['properties'])

    def test_changed_or_cancelled_assignment_cannot_silently_rebase_a_design_brief(self):
        self.seed();task_result=flow.ProjectFlowTests.create(self,recipient='lee',recipient_domain='design');task=self.design.project_flow.requests()[0]
        preview=self.design.command('domain-brief-preview',dict(work_request=asdict(task['ref'])))
        self.design.command('domain-objectives-suggest',dict(work_request=asdict(task['ref']),include_brief=True,expected_signature=preview['signature'],consent=True))
        self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'A later requirement changes the assignment basis.'},self.req['ref'].revision)
        self.assertFalse(self.design.domain_brief.state()[0]['current'])
        with self.assertRaises(StaleBasis):self.design.command('domain-brief-preview',dict(work_request=asdict(task['ref'])))
        self.store.put(task['ref'].id,'project-work-request',SCOPE,{**task['body'],'status':'cancelled'},task['ref'].revision)
        self.assertFalse(self.design.domain_brief.state()[0]['current']);self.assertEqual(self.model.calls,1)
    def test_new_unadopted_proposal_retains_prior_authored_objectives_in_current_chat(self):
        self.seed();self.design.command('domain-objectives-suggest',dict(consent=True));old=self.design.domain_brief.state()[0]
        values=deepcopy(old['body']['output']['objectives']);values[0]['question']='Designer authored an earlier question about reporting loss.'
        self.design.command('domain-objectives-save',dict(expected=asdict(old['ref']),objectives=values));old=self.design.domain_brief.state()[0];r=self.generate()
        self.assertEqual(len(self.design.domain_brief.state()),2)
        t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);ctx,_=self.design.domain_chat.basis(t,self.design.domain_chat.plan(t)[0])
        self.assertEqual(ctx['working_objectives']['ref'],asdict(old['ref']));self.assertEqual(ctx['working_objectives']['objectives'][0]['question'],values[0]['question']);self.assertNotIn('working_design_brief',ctx)

    def test_blank_manual_brief_can_be_saved_but_cannot_complete_or_prepare(self):
        self.seed();out=self.design.command('domain-brief-create',{});r=self.design.domain_brief.state()[0]
        self.design.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=[],brief_sections=[]));r=self.design.domain_brief.state()[0]
        with self.assertRaises(ValueError):self.design.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=[],brief_sections=[],complete=True))
        t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);draft=self.design.domain_chat.draft(t)
        with self.assertRaisesRegex(ValueError,'Complete the Working brief'):self.design.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='bridge'))
        self.assertFalse(self.design.domain_brief.readiness(draft)['ready']);self.assertEqual(self.model.calls,0)
    def test_completion_publication_edit_alert_recompletion_and_shared_diff_are_connected(self):
        from brief_fixture import complete_design_brief
        self.seed();t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);draft=self.design.domain_chat.draft(t);plan=complete_design_brief(self.design,draft)
        self.assertEqual(plan['body']['status'],'completed');self.assertTrue(self.design.domain_brief.readiness(draft)['ready'])
        def prepare():
            out=self.design.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='bridge'))
            return self.store.latest(out['domainHandoff'],self.design.scopes)
        def publish(h):return self.design.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(h['ref']),confirm=True))
        h=prepare();self.assertEqual(h['body']['design_brief'],asdict(plan['ref']));first=publish(h);contribution=self.store.latest(first['id'],{SCOPE});public_ref=contribution['body']['design_brief'];first_public=self.design.command('domain-brief-read',dict(ref=public_ref))
        packet=self.store.resolve_packet(first['packet']['id'],first['packet']['revision'],{SCOPE});self.assertIn(public_ref,packet['refs']);self.assertNotIn('domain-work-plan',[v['kind'] for v in packet['records']]);self.assertNotIn('output',first_public['body'])
        sections=deepcopy(plan['body']['brief_sections']);sections[0]['text']='Private revised purpose pending publication.'
        self.design.command('domain-objectives-save',dict(expected=asdict(plan['ref']),objectives=deepcopy(plan['body']['objectives']),brief_sections=sections));edited=self.design.domain_brief.state()[0]
        self.assertEqual(edited['body']['status'],'working');self.assertFalse(self.design.domain_brief.readiness(draft)['ready'])
        notices=[u for u in self.priya.domain_updates.state() if u['source_kind']=='design-brief-change'];self.assertTrue(notices);self.assertIn('Purpose',notices[0]['detail']);self.assertNotIn('Private revised purpose',str(notices));self.assertEqual(self.priya.command('domain-brief-read',dict(ref=public_ref)),first_public)
        with self.assertRaises((StaleBasis,ValueError)):publish(h)
        self.design.command('domain-objectives-save',dict(expected=asdict(edited['ref']),objectives=deepcopy(edited['body']['objectives']),brief_sections=deepcopy(edited['body']['brief_sections']),complete=True));second=publish(prepare());shared=self.store.latest(second['id'],{SCOPE})['body']['design_brief'];new_public=self.sam.command('domain-brief-read',dict(ref=shared))
        self.assertEqual(new_public['previous']['ref'],public_ref);self.assertEqual(new_public['previous']['body'],first_public['body']);self.assertIn('Private revised purpose',str(new_public['body']));self.assertTrue(any(u['source_kind']=='project-design-brief' for u in self.sam.domain_updates.state()));self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.')
    def test_private_brief_edits_stay_local_until_a_deliverable_is_released(self):
        from brief_fixture import complete_design_brief
        self.seed()
        dt=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation'])
        dd=self.design.domain_chat.draft(dt);dp=complete_design_brief(self.design,dd)
        prepared=self.design.command('domain-prepare',dict(expected=asdict(dd['ref']),recipient='research'))
        dh=self.store.latest(prepared['domainHandoff'],self.design.scopes)
        released=self.design.command('domain-publish',dict(expected=asdict(dd['ref']),preflight=asdict(dh['ref']),confirm=True))
        shared_brief=self.store.latest(released['id'],{SCOPE})['body']['design_brief']
        public_before=[tuple(row) for row in self.store.db.execute('SELECT * FROM records WHERE scope=? ORDER BY id,revision',(SCOPE,))]
        packets_before=[tuple(row) for row in self.store.db.execute('SELECT * FROM packets ORDER BY id,revision')]
        research=Workspace(self.store,'sam',DesignBriefModel())
        research.command('domain-objectives-suggest',dict(consent=True))
        rp=research.domain_brief.state()[0]
        values=deepcopy(rp['body']['output']['objectives'])
        research.command('domain-objectives-save',dict(expected=asdict(rp['ref']),objectives=values))
        rp=research.domain_brief.state()[0]
        rt=research.domain_chat.owned(research.command('domain-chat-start',{})['conversation']);rd=research.domain_chat.draft(rt)
        def research_prepare():
            out=research.command('domain-prepare',dict(expected=asdict(rd['ref']),recipient='design'))
            return self.store.latest(out['domainHandoff'],research.scopes)
        rh=research_prepare()
        values[0]['question']='What additional observations would test this uncertainty?'
        research.command('domain-objectives-save',dict(expected=asdict(rp['ref']),objectives=values))
        self.assertTrue(self.design.domain_brief.current(dp))
        self.assertEqual(self.design.domains.checked_handoff(asdict(dh['ref'])),dh)
        self.assertEqual(self.store.latest('PUB-RESEARCH',{SCOPE}),self.store.read(self.research,{SCOPE}))
        self.assertEqual([tuple(row) for row in self.store.db.execute('SELECT * FROM records WHERE scope=? ORDER BY id,revision',(SCOPE,))],public_before)
        rh=research_prepare();rp=research.domain_brief.state()[0]
        research_before=[tuple(row) for row in self.store.db.execute('SELECT * FROM records WHERE scope=? ORDER BY id,revision',('domain:research',))]
        sections=deepcopy(dp['body']['brief_sections']);sections[0]['text']='Privately refine the Design approach after considering accepted Research input.'
        self.design.command('domain-objectives-save',dict(expected=asdict(dp['ref']),objectives=deepcopy(dp['body']['objectives']),brief_sections=sections))
        self.assertTrue(research.domain_brief.current(rp))
        self.assertEqual(research.domains.checked_handoff(asdict(rh['ref'])),rh)
        self.assertEqual([tuple(row) for row in self.store.db.execute('SELECT * FROM records WHERE scope=? ORDER BY id,revision',('domain:research',))],research_before)
        self.assertEqual(self.store.latest(shared_brief['id'],{SCOPE})['ref'],type(dp['ref'])(**shared_brief))
        self.assertEqual(self.store.latest('PUB-RESEARCH',{SCOPE}),self.store.read(self.research,{SCOPE}))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
        self.assertEqual([tuple(row) for row in self.store.db.execute("SELECT * FROM records WHERE scope=? AND kind!='design-brief-change' ORDER BY id,revision",(SCOPE,))],public_before)
        # Only the author's prepared outgoing handoff needs a fresh local preview.
        with self.assertRaises((StaleBasis,ValueError)):
            self.design.domains.checked_handoff(asdict(dh['ref']))
        self.assertFalse(self.design.bridge.issues())
        # Neither domain's private edits can revise an already shared packet.
        for row in packets_before:
            self.assertIn(row,[tuple(v) for v in self.store.db.execute('SELECT * FROM packets ORDER BY id,revision')])

    def test_every_essential_and_linked_requirement_must_be_adopted_before_completion(self):
        from brief_fixture import complete_design_brief
        self.seed();t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);draft=self.design.domain_chat.draft(t);r=complete_design_brief(self.design,draft)
        for i in range(len(r['body']['brief_sections'])):
            sections=deepcopy(r['body']['brief_sections']);sections[i]['disposition']='question'
            with self.subTest(section=i),self.assertRaises(ValueError):self.design.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=deepcopy(r['body']['objectives']),brief_sections=sections,complete=True))
        for key in ['title','question','why','output','evidence']:
            objectives=deepcopy(r['body']['objectives']);objectives[0][key]=''
            with self.subTest(field=key),self.assertRaises(ValueError):self.design.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=objectives,brief_sections=deepcopy(r['body']['brief_sections']),complete=True))
        self.assertEqual(self.design.domain_brief.state()[0]['ref'],r['ref'])
