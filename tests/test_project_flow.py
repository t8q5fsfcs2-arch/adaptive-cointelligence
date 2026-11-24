from brief_fixture import complete_design_brief
import tempfile
import unittest
from pathlib import Path
from dataclasses import asdict
from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.project_flow import figma_link

class ProjectFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'flow.db';self.store=Store(self.path)
        self.owner=Workspace(self.store,'alex');self.owner.setup(dict(title='Fictional feedback',intent='Capture feedback with evidence limits.',boundary='Non-safety only'))
        out=self.owner.create_requirement(dict(title='Staged evidence',text='Allow initial capture.',rationale='Avoid reporting loss.',conditions='Non-safety',drawer='Experience',acceptance_criteria='Show evidence pending.'))
        self.req=self.store.latest(out['id'],{SCOPE});self.packet=dict(id='PKT-'+out['id'],revision=1)
        self.priya=Workspace(self.store,'priya');self.sam=Workspace(self.store,'sam');self.lee=Workspace(self.store,'lee')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def create(self,**kw):
        values=dict(title='Understand reporting friction',recipient='sam',objective='Establish where work is lost.',expected_output='Bounded finding and downstream implications.',boundaries='No safety process changes.',local_context='Research should examine the reporting task and preserve observation limits.',requirement_guidance=[dict(ref=asdict(self.req['ref']),local_application='Investigate whether staged evidence reduces reporting interruption.',expected_evidence='A finding linked to task observations and study limits.')],packet_refs=[self.packet],requirement_refs=[asdict(self.req['ref'])]);values.update(kw)
        return self.priya.project_flow.seed_legacy_request(values)
    def test_assignment_shared_durable_separate_and_idempotent(self):
        self.create();task=self.sam.project_flow.requests()[0];self.assertEqual(task['kind'],'project-work-request');self.assertFalse(self.sam.bridge.issues())
        out=self.sam.command('work-request-start',dict(expected=asdict(task['ref'])));latest=self.sam.project_flow.requests()[0];self.assertEqual(latest['body']['status'],'accepted')
        again=self.sam.command('work-request-start',dict(expected=asdict(latest['ref'])));self.assertEqual(out['id'],again['id'])
        draft=self.store.latest(out['id'],{'domain:research'});self.assertEqual(draft['body']['requirement_refs'],[asdict(self.req['ref'])]);self.assertNotIn(out['id'],str(latest))
        self.store.close();self.store=Store(self.path);self.sam=Workspace(self.store,'sam');self.assertEqual(len(self.sam.domain_chat.threads()),1)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['status'],'proposed')
    def test_new_assignment_command_is_retired_for_every_role_without_mutating_existing_briefs(self):
        self.create()
        before=list(self.store.db.execute('SELECT * FROM records ORDER BY id,revision'))
        for workspace in [self.priya,self.sam,self.lee,self.owner]:
            with self.assertRaisesRegex(ValueError,'work assignment has been removed'):
                workspace.command('work-request-create',{})
            state=workspace.project_flow.state()
            self.assertFalse(state['can_request'])
            self.assertEqual(state['recipients'],[])
            self.assertEqual(len(state['requests']),1)
        self.assertEqual(before,list(self.store.db.execute('SELECT * FROM records ORDER BY id,revision')))
    def test_assignment_survives_private_edit_preflight_and_released_response(self):
        self.sam.command('domain-chat-start',{})  # Unassigned conversations do not break assignment opening.
        self.create();task=self.sam.project_flow.requests()[0];out=self.sam.command('work-request-start',dict(expected=asdict(task['ref'])))
        draft=self.store.latest(out['id'],{'domain:research'});self.assertEqual(draft['body']['work_request']['id'],task['ref'].id)
        edited=self.sam.command('domain-save',{**draft['body'],'expected':asdict(draft['ref']),'observation':'A fictional research observation.'});draft=self.store.latest(edited['id'],{'domain:research'})
        self.sam.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='design',intent_implications='No change proposed.',downstream_needs='Explore the pending state.',open_questions='Evidence ownership remains unanswered.'));handoff=self.sam.domains.handoffs()[0]
        out=self.sam.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(handoff['ref']),confirm=True,release_sources=False))
        published=self.store.latest(out['id'],{SCOPE});self.assertEqual(published['body']['work_request']['id'],task['ref'].id)
        self.assertEqual(self.priya.project_flow.state()['requests'][0]['published_outputs'][0]['ref'],asdict(published['ref']))
        self.assertEqual(self.priya.project_flow.requests()[0]['body']['status'],'accepted')  # Release is not assignment/requirement approval.

    def test_private_packet_and_wrong_recipient_rejected(self):
        private=self.store.put('SECRET','source','domain:research',dict(text='Private'));self.store.packet('PRIVATE',1,'Private',[private],{'domain:research'},{'domain:research'})
        with self.assertRaises(PermissionError):self.create(packet_refs=[dict(id='PRIVATE',revision=1)])
        self.create();task=self.sam.project_flow.requests()[0]
        with self.assertRaises(PermissionError):self.lee.command('work-request-start',dict(expected=asdict(task['ref'])))
        with self.assertRaises(PermissionError):self.lee.command('work-request-respond',dict(expected=asdict(task['ref']),action='accept'))
    def test_changed_assignment_and_stale_responses_rejected(self):
        self.create();task=self.sam.project_flow.requests()[0];self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Changed wording'},self.req['ref'].revision)
        self.assertTrue(self.sam.project_flow.state()['requests'][0]['changed'])
        with self.assertRaises(StaleBasis):self.sam.command('work-request-start',dict(expected=asdict(task['ref'])))
        self.priya.command('work-request-respond',dict(expected=asdict(task['ref']),action='cancel',note='Reissue with current context.'))
        with self.assertRaises(StaleBasis):self.sam.command('work-request-respond',dict(expected=asdict(task['ref']),action='accept'))
    def test_direct_start_cannot_spoof_assignment_scope(self):
        self.create();task=self.sam.project_flow.requests()[0];self.sam.command('work-request-respond',dict(expected=asdict(task['ref']),action='accept'));task=self.sam.project_flow.requests()[0]
        with self.assertRaises(ValueError):self.sam.command('domain-chat-start',dict(work_request=asdict(task['ref']),requirement_ids=[],input_refs=[]))
    def test_tool_links_versioned_and_never_claim_mcp(self):
        out=self.sam.command('work-tools-save',dict(expected=None,links=dict(research_figjam='https://www.figma.com/board/FictionalResearch/name?node-id=1-2&t=ignored')))
        tools=self.lee.project_flow.tools();self.assertEqual(tools['links']['research_figjam'],'https://www.figma.com/board/FictionalResearch?node-id=1-2');self.assertFalse(tools['mcp']['execution_available'])
        with self.assertRaises(PermissionError):self.sam.command('work-tools-save',dict(expected=out['ref'],links=dict(design_figma='')))
        with self.assertRaises(StaleBasis):self.lee.command('work-tools-save',dict(expected=None,links=dict(design_figma='')))
        self.lee.command('work-tools-save',dict(expected=out['ref'],links=dict(design_figma='https://figma.com/design/FictionalDesign')))
        self.store.close();self.store=Store(self.path);self.assertIn('FictionalDesign',Workspace(self.store,'lee').project_flow.tools()['links']['design_figma'])
    def test_link_validation(self):
        for value in ['javascript:alert(1)','https://evil.example/board/X','https://user:secret@figma.com/board/X','http://figma.com/board/X','https://www.figma.com/design/X','https://figma.com:999/board/X']:
            with self.subTest(value=value),self.assertRaises(ValueError):figma_link(value,'board')
    def test_pending_question_in_context_and_packet_not_a_requirement_change(self):
        issue=self.sam.command('bridge-raise',dict(boards=['business-research','research-design'],owner='priya',kind='question',route='coordination',title='Who follows up?',question='Who owns incomplete evidence?',consequence='Design needs a known next owner.',packet_refs=[self.packet],requirement_refs=[asdict(self.req['ref'])]))
        out=self.lee.command('domain-chat-start',{});t=self.lee.domain_chat.owned(out['conversation']);draft=self.lee.domain_chat.draft(t);ctx=self.lee.domains.context(asdict(draft['ref']))
        self.assertEqual(ctx['pending_bridge_questions'][0]['question'],'Who owns incomplete evidence?');self.assertIn(dict(id=issue['id'],revision=1),ctx['basis']);self.assertEqual(self.lee.project_flow.pending([]),[])
        complete_design_brief(self.lee,draft)
        self.lee.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='research',intent_implications='',downstream_needs='',open_questions='Sponsor response pending.'));h=self.lee.domains.handoffs()[0];p=h['body']['packet'];resolved=self.store.resolve_packet(p['id'],p['revision'],self.lee.scopes)
        self.assertIn(issue['id'],[r['ref'].id for r in resolved['records']]);r=self.priya.bridge.issues()[0];self.priya.command('bridge-respond',dict(expected=asdict(r['ref']),action='comment',note='We are considering an owner.'))
        with self.assertRaises(StaleBasis):self.lee.domains.checked_handoff(asdict(h['ref']))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.')
    def test_project_tools_not_global(self):
        self.sam.command('work-tools-save',dict(expected=None,links=dict(research_figjam='https://figma.com/board/ONE')))
        s=Store(Path(self.tmp.name)/'other.db')
        try:self.assertEqual(Workspace(s,'sam').project_flow.tools()['links']['research_figjam'],'')
        finally:s.close()


class ObjectiveModel:
    fail=False;during=None
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='objective-fixture')
    def generate(self,**kw):
        self.context=kw['context'];c=self.context;r=c['requirements'][0]
        if self.during:self.during()
        return dict(output=dict(summary='Investigate the reporting interruption before prescribing the solution.',objectives=[dict(title='Locate the evidence interruption',question='When does evidence collection interrupt initial capture?',why='It tests the barrier identified by the business intent.',output='A task-based finding with limits.',evidence='Observed triggers, actions and incomplete states.',requirement_ids=[r['ref']['id']],basis_links=[dict(evidence_id='invented-unknown-id' if self.fail else next(e['evidence_id'] for e in c['evidence_excerpts'] if e['id']==r['ref']['id']))])],open_questions=['Who owns evidence follow-up?']),model='objective-fixture')

class ObjectiveTests(unittest.TestCase):
    setUp=ProjectFlowTests.setUp
    tearDown=ProjectFlowTests.tearDown
    def test_objectives_are_source_linked_private_editable_and_feed_current_chat(self):
        m=ObjectiveModel();w=Workspace(self.store,'sam',m);out=w.command('domain-objectives-suggest',dict(consent=True));plan=w.domain_brief.state()[0]
        self.assertEqual(plan['body']['status'],'suggested');self.assertNotIn(out['id'],str(self.lee.state()['domain_objectives']))
        objectives=plan['body']['output']['objectives'];objectives[0]['question']='At which step is non-safety feedback lost?'
        w.command('domain-objectives-save',dict(expected=asdict(plan['ref']),objectives=objectives));t=w.domain_chat.owned(w.command('domain-chat-start',{})['conversation']);ctx,_=w.domain_chat.basis(t,w.domain_chat.plan(t)[0])
        self.assertEqual(ctx['working_objectives']['objectives'][0]['question'],'At which step is non-safety feedback lost?');self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.')
        self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Changed current basis'},self.req['ref'].revision)
        self.assertFalse(w.domain_brief.state()[0]['current'])
        before=w.domain_brief.state()[0]['ref'];w.command('domain-objectives-save',dict(expected=asdict(before),objectives=objectives));self.assertEqual(w.domain_brief.state()[0]['ref'].revision,before.revision+1);self.assertFalse(w.domain_brief.state()[0]['current'])
    def test_bad_or_changed_objective_basis_does_not_save_fake_proposal(self):
        from workbench.model_provider import ModelUnavailable
        m=ObjectiveModel();m.fail=True;w=Workspace(self.store,'sam',m)
        with self.assertRaises(ModelUnavailable):w.command('domain-objectives-suggest',dict(consent=True))
        self.assertFalse(w.domain_brief.state());m.fail=False
        m.during=lambda:self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Changed during inference'},self.req['ref'].revision)
        with self.assertRaises(StaleBasis):w.command('domain-objectives-suggest',dict(consent=True))
        self.assertFalse(w.domain_brief.state())



class UpdateTests(unittest.TestCase):
    setUp=ProjectFlowTests.setUp
    tearDown=ProjectFlowTests.tearDown
    def test_updates_are_real_and_read_state_is_account_specific(self):
        created=self.sam.command('bridge-raise',dict(boards=['business-research'],owner='priya',kind='question',route='coordination',title='Who follows up?',question='Who owns incomplete evidence?',consequence='Design needs a next owner.',packet_refs=[self.packet],requirement_refs=[asdict(self.req['ref'])]))
        first=Workspace(self.store,'sam',principal_id='account-one');second=Workspace(self.store,'sam',principal_id='account-two')
        update=first.domain_updates.state()[0];self.assertTrue(update['new']);first.command('project-update-open',dict(update=update['ref']))
        self.assertFalse(first.domain_updates.state()[0]['new']);self.assertTrue(second.domain_updates.state()[0]['new'])
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['body']['text'],'Allow initial capture.')
        with self.assertRaises(ValueError):first.command('project-update-open',dict(update=dict(id='SECRET',revision=1)))
    def test_issue_own_progress_cannot_make_its_packet_basis_permanently_stale(self):
        out=self.sam.command('bridge-raise',dict(boards=['research-design'],owner='sam',kind='question',route='coordination',title='Pending state',question='What is the next step?',consequence='A declared dependency.',packet_refs=[self.packet],requirement_refs=[asdict(self.req['ref'])]));issue=self.sam.bridge.issues()[0]
        self.store.packet('WITH-ISSUE',1,'Historical pending state',[issue['ref'],self.req['ref']],{SCOPE},{SCOPE})
        self.sam.command('bridge-refresh',dict(expected=asdict(issue['ref']),packet_refs=[dict(id='WITH-ISSUE',revision=1)],requirement_refs=[asdict(self.req['ref'])],note='Review the packet and current issue together.'))
        self.assertFalse(self.sam.bridge.state()['issues'][0]['changed'])
        self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Changed requirement'},self.req['ref'].revision)
        self.assertTrue(self.sam.bridge.state()['issues'][0]['changed'])

if __name__=='__main__':unittest.main()
