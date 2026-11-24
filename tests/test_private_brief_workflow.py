from copy import deepcopy
from dataclasses import asdict
import unittest
import test_design_brief as fixture
import test_domain_chat as chats
import test_domain_development as development
from workbench.workspace import Workspace
from workbench.core import StaleBasis
from workbench.decisions import SCOPE
from workbench import brief_development

class PlanModel:
    def __init__(self):self.calls=[];self.bad=False
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='synthetic')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));ctx=kw['context']
        if ctx.get('include_design_brief') and ctx.get('skill') in {'domain-design-brief','domain-working-brief'}:
            result=fixture.DesignBriefModel().generate(**kw)
            if ctx['domain_profile']['config'].get('brief_sections'):
                base=deepcopy(result['output']['brief_sections'][0])
                result['output']['brief_sections'].extend({**deepcopy(base),'kind':kind,'title':title,'text':text} for kind,title,text in [
                    ('hypotheses','Business hypotheses to examine','Proposed hypothesis: easier feedback capture improves usable reporting. Examine whether ownership and follow-through matter more; this is not a finding.'),
                    ('approach','Research approach','Propose contextual interviews with technicians about recent interruptions and handoffs; participant coverage remains to be agreed.'),
                    ('discussion-guide','Draft interview guide','Walk me through the last issue you reported. What triggered it? What happened next? What got in the way? Who took ownership? How did you know what happened?') ] if kind in ctx['domain_profile']['config']['brief_sections'])
            return result
        if ctx.get('workbench_task')=='submission-evaluation':
            out=development.DevelopmentModel().generate(**kw)
            out['output']['plan_review']=[dict(section_id=s['id'],assessment='partial',rationale='The work describes a proposed approach; observed performance is not established.',evidence=[],next_step='Collect the missing task evidence.') for s in ctx.get('brief_evaluation',{}).get('sections',[])]
            return out
        out=chats.ChatModel().generate(**kw)
        if ctx.get('brief_development'):
            target=next(t for t in ctx['brief_development']['editable_targets'] if t.endswith(':question'))
            out['output']['summary']='Brief recommendation: test whether the technician can distinguish saved work from a confirmed submission.'
            out['output']['brief_changes']=[dict(target='requirement:text' if self.bad else target,value='Can the technician distinguish retained draft work from confirmed submission?',why='Makes the objective observable without inventing a result.')]
        return out

class PrivateBriefTests(unittest.TestCase):
    setUp=fixture.DesignBriefTests.setUp;tearDown=fixture.DesignBriefTests.tearDown;seed=fixture.DesignBriefTests.seed
    def plan(self,actor='lee',adopt=False):
        if not hasattr(self,'research'):self.seed()
        model=PlanModel();w=Workspace(self.store,actor,model);preview=w.command('domain-brief-preview',{})
        w.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
        r=w.domain_brief.state()[0]
        if adopt:
            sections=[{**s,'id':'section-'+str(i),'disposition':'use'} for i,s in enumerate(r['body']['output']['brief_sections']) if s['kind']!='requirement-implication']
            w.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=deepcopy(r['body']['output']['objectives']),brief_sections=sections));r=w.domain_brief.state()[0]
        t=w.domain_chat.owned(w.command('domain-chat-start',{})['conversation']);return w,model,r,t
    def send(self,w,t,**patch):
        t=w.domain_chat.owned(asdict(t['ref']));draft=w.domain_chat.draft(t)
        return w.command('domain-chat-send',dict(conversation=asdict(t['ref']),expected=asdict(draft['ref']),message='Help make the objective observable.',consent=True,request_id='private-plan-discussion-0001',brief_development=True,**patch))
    def test_full_working_brief_is_configured_for_both_domains_and_keeps_inputs_read_only(self):
        for actor in ('sam','lee'):
            w,m,r,t=self.plan(actor);self.assertTrue(r['body']['include_domain_brief']);self.assertTrue(r['editable']);self.assertEqual(r['body']['domain_key'],w.domains.key)
            self.assertTrue({'purpose','scope','users-and-tasks','deliverable','validation','evidence-and-dependencies','requirement-implication'}<={s['kind'] for s in r['body']['output']['brief_sections']})
            self.assertNotIn('Never send this private Research transcript',str(m.calls));self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_changed_inputs_allow_private_editing_and_coaching_but_do_not_authorize_readiness(self):
        w,m,r,t=self.plan()
        req=self.store.latest(self.req['ref'].id,{SCOPE});self.store.put(req['ref'].id,req['kind'],req['scope'],{**req['body'],'text':'A revised governing requirement.'},req['ref'].revision)
        values=deepcopy(r['body']['output']['objectives']);values[0]['question']='A private exploration of an alternative.'
        saved=w.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=values));latest=w.domain_brief.state()[0]
        self.assertFalse(latest['current']);self.assertEqual(latest['body']['objectives'][0]['question'],values[0]['question'])
        with self.assertRaises(StaleBasis):w.command('domain-objectives-save',dict(expected=saved_ref(saved,w),objectives=values,complete=True))
        draft=w.domain_chat.draft(t);w.command('domain-chat-context',dict(conversation=asdict(t['ref']),expected=asdict(draft['ref']),requirement_ids=[self.req['ref'].id],input_refs=[]))
        t=w.store.latest(t['ref'].id,w.scopes)
        self.send(w,t);self.assertIn('earlier_inputs',m.calls[-1]['context']['brief_for_coaching']);self.assertEqual(w.bridge.issues(),[])
    def test_one_main_chat_call_proposes_changes_then_review_and_edited_apply_are_deterministic(self):
        for actor in ('sam','lee'):
            w,m,plan,t=self.plan(actor);before=deepcopy(plan);count=len(m.calls);out=self.send(w,t)
            report=self.store.latest(out['chatReport'],w.scopes);self.assertEqual(len(m.calls),count+1);self.assertTrue(report['body']['output']['brief_changes']);self.assertEqual(w.domain_brief.state()[0]['ref'],before['ref'])
            t=w.store.latest(t['ref'].id,w.scopes);proposal=w.command('domain-brief-refine-review',dict(conversation=asdict(t['ref']),review=asdict(report['ref'])));self.assertEqual(len(m.calls),count+1)
            target=proposal['changes'][0]['target'];text='What evidence distinguishes retained work from a confirmed submission?'
            result=w.command('domain-brief-refine-apply',dict(expected=proposal['ref'],confirm=True,edits={target:text}));saved=w.domain_brief.state()[0]
            self.assertEqual(saved['body']['objectives'][0]['question'],text);self.assertEqual(saved['ref'].revision,plan['ref'].revision+1);self.assertEqual(len(m.calls),count+1)
            self.assertIn(text,w.domain_chat.turns(t)[-1]['body']['message']);self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req);self.assertEqual(w.bridge.issues(),[])
            with self.assertRaises(StaleBasis):w.command('domain-brief-refine-apply',dict(expected=proposal['ref'],confirm=True))
    def test_invalid_optional_plan_advice_is_discarded_without_losing_the_chat(self):
        w,m,r,t=self.plan();m.bad=True;out=self.send(w,t);report=self.store.latest(out['chatReport'],w.scopes)
        self.assertEqual(report['body']['output']['brief_changes'],[]);self.assertIn('Brief recommendation',report['body']['output']['summary']);self.assertEqual(w.domain_brief.state()[0]['ref'],r['ref'])
    def test_review_rejects_other_domain_or_concurrent_plan_changes(self):
        w,m,r,t=self.plan();out=self.send(w,t);report=self.store.latest(out['chatReport'],w.scopes)
        with self.assertRaises(PermissionError):self.sam.command('domain-brief-refine-review',dict(conversation=asdict(t['ref']),review=asdict(report['ref'])))
        values=deepcopy(r['body']['output']['objectives']);values[0]['question']='Concurrent author wording.';w.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=values))
        with self.assertRaises(StaleBasis):w.command('domain-brief-refine-review',dict(conversation=asdict(t['ref']),review=asdict(report['ref'])))
    def test_submission_evaluates_selected_plan_without_editing_it_and_retains_prior_cycles(self):
        w,m,r,t=self.plan('sam',adopt=True);d=w.domain_chat.draft(t)
        data=dict(conversation=asdict(t['ref']),expected=asdict(d['ref']),submission=None)
        sub=w.command('domain-submission-save',dict(**data,text='A proposed research synthesis with explicit limits.',source_refs=[],implication_refs=[],primary_source=None,review_mode='text'));data['submission']=sub['ref'];before=deepcopy(w.domain_brief.state()[0])
        result=w.command('domain-submission-evaluate',dict(**data,consent=True,request_id='plan-eval-request-0001',cycle='plan-eval-cycle-0001',batch=0));review=self.store.latest(result['evaluation']['id'],w.scopes)
        self.assertEqual(len(review['body']['output']['plan_review']),9);self.assertEqual(w.domain_brief.state()[0],before);self.assertTrue(w.submissions.is_current(review,t))
        state=w.submissions.state([t])[0]['evaluations'][0];self.assertEqual(state['body']['evaluated_plan']['ref'],asdict(r['ref']))
        first=deepcopy(review);data['conversation']=asdict(w.store.latest(t['ref'].id,w.scopes)['ref']);data['submission']=w.command('domain-submission-save',dict(**data,text='Revised synthesis with another evidence limitation.',source_refs=[],implication_refs=[],primary_source=None,review_mode='text'))['ref']
        self.assertFalse(w.submissions.is_current(review,t));self.assertEqual(self.store.latest(review['ref'].id,w.scopes),first)
    def test_plan_performance_cannot_be_marked_addressed_without_cited_evidence(self):
        ctx={'brief_evaluation':{'sections':[{'id':'criterion','title':'Demonstrate recovery'}]}}
        with self.assertRaises(ValueError):brief_development.validate_plan([dict(section_id='criterion',assessment='addressed',rationale='The plan is filled in.',evidence=[],next_step='')],ctx)

    def test_brief_sections_and_guidance_configure_the_same_routine_in_design(self):
        from workbench.domain import EDITABLE
        w,m,r,t=self.plan();profile=w.domains.profile()
        patch={k:deepcopy(profile['config'][k]) for k in EDITABLE}
        patch.update(brief_guidance='Propose hypotheses and a neutral interview guide for this evaluation assignment.',brief_sections=['hypotheses','approach','discussion-guide'])
        w.command('domain-configure',dict(domain='design',expected=profile['ref'],config=patch,reason='Test the shared configurable brief routine.'))
        preview=w.command('domain-brief-preview',{});w.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
        new=w.domain_brief.state()[0]
        self.assertTrue(set(patch['brief_sections'])<={s['kind'] for s in new['body']['output']['brief_sections']})
        self.assertIn(patch['brief_guidance'],m.calls[-1]['instructions'])
        self.assertEqual(self.store.read(r['ref'],w.scopes)['ref'],r['ref']);self.assertFalse(w.bridge.issues())
        current=w.domains.profile();invalid={**patch,'brief_sections':['approve-requirements']}
        with self.assertRaises(ValueError):w.command('domain-configure',dict(domain='design',expected=current['ref'],config=invalid,reason='Invalid authority injection.'))
        self.assertEqual(w.domains.profile()['ref'],current['ref'])
    def test_long_guide_can_be_saved_and_refined_without_extending_other_fields(self):
        from workbench.brief_refinement import targets
        w,m,r,t=self.plan('sam');sections=[{**s,'id':'section-'+str(i),'disposition':'use'} for i,s in enumerate(r['body']['output']['brief_sections']) if s['kind']!='requirement-implication']
        guide=next(s for s in sections if s['kind']=='discussion-guide');guide['text']='Ask for a recent concrete example. '*50
        w.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=deepcopy(r['body']['output']['objectives']),brief_sections=sections));saved=w.domain_brief.state()[0]
        self.assertEqual(next(s for s in saved['body']['brief_sections'] if s['kind']=='discussion-guide')['text'],guide['text'].strip())
        target=next(v for v in targets(saved).values() if 'Draft interview guide' in v['label'] and v['label'].endswith('text'));self.assertEqual(target['limit'],2400)
        guide['text']='x'*2401
        with self.assertRaises(ValueError):w.command('domain-objectives-save',dict(expected=asdict(saved['ref']),objectives=deepcopy(saved['body']['objectives']),brief_sections=sections))
        self.assertEqual(w.domain_brief.state()[0]['ref'],saved['ref'])
    def test_refresh_retains_authored_plan_in_context_without_self_invalidating_new_proposal(self):
        w,m,r,t=self.plan(adopt=True);preview=w.command('domain-brief-preview',{})
        w.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
        new=w.domain_brief.state()[0];self.assertTrue(new['current']);self.assertEqual(m.calls[-1]['context']['existing_private_plan']['ref'],asdict(r['ref']))
        self.assertEqual(self.store.read(r['ref'],w.scopes)['ref'],r['ref']);self.assertNotIn('existing_private_plan',w.domain_brief.context())

    def test_brief_activity_uses_the_actual_domain_instead_of_a_design_only_name(self):
        from workbench.project_activity import function_for
        for key,persona in [('research','P06'),('design','P12')]:
            result=function_for(dict(persona=persona,skill='domain-design-brief',scope='domain:'+key,agent='domain-coach'))
            self.assertEqual(result[0],key.title()+' Brief Drafter');self.assertEqual(result[1],key.title()+' workbench')

    def test_requirement_citations_resolve_full_supplied_records_not_compact_display_projections(self):
        self.seed();m=PlanModel();w=Workspace(self.store,'sam',m);original=w.domain_brief.context
        def projected(*args,**kwargs):
            ctx=original(*args,**kwargs)
            for record in ctx['evidence_records']:
                if record['kind']=='requirement':record['body']={'title':record['body']['title']}
            return ctx
        w.domain_brief.context=projected
        preview=w.command('domain-brief-preview',{});w.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
        plan=w.domain_brief.state()[0];self.assertTrue(plan['current']);link=plan['body']['output']['objectives'][0]['basis_links'][0]
        self.assertEqual(link['id'],self.req['ref'].id);self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)

def saved_ref(result,w):return asdict(w.store.latest(result['id'],w.scopes)['ref'])
