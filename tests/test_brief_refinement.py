from copy import deepcopy
from dataclasses import asdict
import unittest
import test_design_brief as brief
from workbench.workspace import Workspace
from workbench.core import StaleBasis
from workbench.model_provider import ModelUnavailable
from workbench.decisions import SCOPE

class RefinementModel(brief.DesignBriefModel):
    def generate(self,**kw):
        if kw['context'].get('skill')!='domain-brief-refinement':return super().generate(**kw)
        self.calls+=1;self.context=kw['context'];targets=self.context['editable_targets'];target=next(t for t in targets if t.endswith(':question'))
        return dict(output=dict(summary='Make the objective testable without overstating the evidence.',changes=[dict(target='section:1:text' if self.bad else target,value='Can the technician distinguish saved work from confirmed submission after an interruption?',why='Makes the task and observable outcome explicit.')]))

class RefinementTests(unittest.TestCase):
    setUp=brief.DesignBriefTests.setUp;tearDown=brief.DesignBriefTests.tearDown;seed=brief.DesignBriefTests.seed
    def prepare(self,actor='lee'):

        if not hasattr(self,'research'):self.seed()
        m=RefinementModel();w=Workspace(self.store,actor,m)
        if actor=='lee':
            preview=w.command('domain-brief-preview',{});w.command('domain-objectives-suggest',dict(consent=True,include_brief=True,expected_signature=preview['signature']))
        else:w.command('domain-objectives-suggest',dict(consent=True))
        plan=w.domain_brief.state()[0];thread=w.domain_chat.owned(w.command('domain-chat-start',{})['conversation']);turn=w.domain_chat.turn(thread,'assistant','Use an observable interruption task to distinguish retained work from a confirmed submission.')
        data=dict(expected=asdict(plan['ref']),conversation=asdict(thread['ref']),selection=dict(turn=asdict(turn),text='Use an observable interruption task'),consent=True)
        return w,m,plan,thread,data
    def test_explicit_update_saves_one_revision_then_posts_exact_from_to_receipt_for_both_domains(self):
        for actor in ['lee','sam']:
            with self.subTest(actor=actor):
                w,m,plan,thread,data=self.prepare(actor);requirement=deepcopy(self.store.latest(self.req['ref'].id,{SCOPE}));proposal=w.command('domain-brief-refine-prepare',data)
                self.assertEqual(w.domain_brief.state()[0]['ref'],plan['ref']);calls=m.calls
                result=w.command('domain-brief-refine-apply',dict(expected=proposal['ref'],confirm=True));saved=w.domain_brief.state()[0]
                self.assertEqual(saved['ref'].revision,plan['ref'].revision+1);self.assertEqual(m.calls,calls)
                self.assertEqual(saved['body']['status'],'working');self.assertTrue(saved['refinement'])
                receipt=w.domain_chat.turns(thread)[-1];self.assertIn('From:',receipt['body']['message']);self.assertIn('To:',receipt['body']['message']);self.assertEqual(receipt['body']['brief_update']['plan'],asdict(saved['ref']))
                self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),requirement);self.assertFalse(w.bridge.issues())
                with self.assertRaises(StaleBasis):w.command('domain-brief-refine-apply',dict(expected=proposal['ref'],confirm=True))
    def test_stale_plan_and_forged_incoming_target_do_not_apply_or_claim_success(self):
        w,m,plan,thread,data=self.prepare();proposal=w.command('domain-brief-refine-prepare',data)
        values=deepcopy(plan['body']['output']['objectives']);values[0]['question']='An author edited this first.'
        w.command('domain-objectives-save',dict(expected=asdict(plan['ref']),objectives=values));before=w.domain_brief.state()[0]
        with self.assertRaises(StaleBasis):w.command('domain-brief-refine-apply',dict(expected=proposal['ref'],confirm=True))
        self.assertEqual(w.domain_brief.state()[0],before);self.assertFalse(any(t['body'].get('brief_update') for t in w.domain_chat.turns(thread)))
        data['expected']=asdict(before['ref']);m.bad=True
        with self.assertRaises(ModelUnavailable):w.command('domain-brief-refine-prepare',data)
        self.assertEqual(w.domain_brief.state()[0],before)
    def test_selection_must_be_exact_owned_and_in_the_current_discussion(self):
        w,m,plan,thread,data=self.prepare();bad=deepcopy(data);bad['selection']['text']='Invented text'
        with self.assertRaises(ValueError):w.command('domain-brief-refine-prepare',bad)
        other=w.domain_chat.owned(w.command('domain-chat-start',{})['conversation']);bad=deepcopy(data);bad['conversation']=asdict(other['ref'])
        with self.assertRaises(PermissionError):w.command('domain-brief-refine-prepare',bad)
        self.assertEqual(w.domain_brief.state()[0]['ref'],plan['ref']);self.assertEqual(m.calls,1)

    def test_typed_chat_instruction_is_saved_with_success_receipt_only_after_explicit_apply(self):
        w,m,plan,thread,data=self.prepare();data.pop('selection');data['request']='Make the objective observable and keep evidence limitations.'
        proposal=w.command('domain-brief-refine-prepare',data);self.assertNotIn(data['request'],str(w.domain_chat.turns(thread)))
        w.command('domain-brief-refine-apply',dict(expected=proposal['ref'],confirm=True));turns=w.domain_chat.turns(thread)
        self.assertEqual(turns[-2]['body']['role'],'user');self.assertEqual(turns[-2]['body']['message'],data['request']);self.assertIn('I updated the brief.',turns[-1]['body']['message'])
