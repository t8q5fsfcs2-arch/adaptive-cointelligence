"""Placement advice stays scoped, bounded and subordinate to reviewed card saves."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest

from workbench import card_placement,conversation_findings
from workbench.workspace import Workspace
from workbench.core import StaleBasis
import test_domain_chat as chat
import test_knowledge_cards as cards


class CardPlacementTests(unittest.TestCase):
    setUp=chat.ChatTests.setUp
    tearDown=chat.ChatTests.tearDown
    start=chat.ChatTests.start
    current=chat.ChatTests.current
    draft=chat.ChatTests.draft
    send=chat.ChatTests.send
    save=cards.KnowledgeCardTests.save
    relation=cards.KnowledgeCardTests.relation

    def proposal(self,card,**patch):
        p=dict(field='summary',index=0,quote='bounded interpretation',destination=card_placement.key(asdict(card['ref'])),type='finding',section='fields.implications',title='',card_statement='',reason='This qualifies the same finding.')
        return {**p,**patch}
    def review(self,t,output,**kw):
        ref=self.store.put('PLACEMENT-REVIEW-'+str(self.store.db.execute('select count(*) from records').fetchone()[0]),'domain-chat-review','domain:research',dict(owner='sam',conversation=t['ref'].id,output=output,format='text',context={'card_capture_options':card_placement.options(self.sam)},at='2026-11-14T21:00:00Z',**kw))
        return self.store.read(ref,self.sam.scopes)
    def test_options_are_private_bounded_and_do_not_write(self):
        t=self.start();d=self.start(self.lee)
        for i in range(15):self.save(self.sam,t,title='Finding '+str(i),fields={'scope':'x'*1800,'implications':'y'*1800})
        self.save(self.lee,d,title='PRIVATE DESIGN')
        before=self.store.db.execute('select count(*) from records').fetchone()[0];options=card_placement.options(self.sam)
        self.assertLessEqual(len(options),12);self.assertLessEqual(sum(len(json.dumps(x)) for x in options),14000)
        self.assertNotIn('PRIVATE DESIGN',str(options));self.assertNotIn('origin_selection',str(options))
        self.assertEqual(before,self.store.db.execute('select count(*) from records').fetchone()[0])
    def test_optional_model_advice_uses_exact_passages_types_and_current_owned_targets(self):
        t=self.start();card=self.save(self.sam,t);ctx={'card_capture_options':card_placement.options(self.sam)};p=self.proposal(card)
        out={'summary':'The evidence needs a bounded interpretation.','card_placements':[p]}
        self.assertEqual(card_placement.validated(out,ctx),[p])
        for patch in [dict(quote='invented quotation'),dict(destination='CARD-OTHER:v1'),dict(section='fields.fabricated'),dict(type='artifact'),dict(index=True),dict(field='private-source')]:
            with self.subTest(patch=patch):self.assertEqual(card_placement.validated({**out,'card_placements':[self.proposal(card,**patch)]},ctx),[])
        self.assertEqual(card_placement.validated({**out,'card_placements':[p,p,p,p]},ctx),[p])
    def test_schema_extends_existing_response_and_invalid_advice_does_not_discard_the_answer(self):
        t=self.start();self.save(self.sam,t);ctx={'card_capture_options':card_placement.options(self.sam)}
        base={'type':'object','properties':{'summary':{'type':'string'}},'required':['summary'],'additionalProperties':False}
        schema=conversation_findings.output_schema(base,ctx)
        self.assertEqual(schema['properties']['card_placements']['maxItems'],3);self.assertIn('card_placements',schema['required'])
        out={'summary':'A useful answer.','card_placements':[{'invented':'bad advice'}]};conversation_findings.validate(out,ctx)
        self.assertEqual(out['summary'],'A useful answer.');self.assertEqual(out['card_placements'],[])
    def test_projection_requires_exact_target_revision_and_never_auto_saves(self):
        t=self.start();card=self.save(self.sam,t);p=self.proposal(card);r=self.review(t,{'summary':'A bounded interpretation.','card_placements':[p]});before=self.store.db.execute('select count(*) from records').fetchone()[0]
        hints=card_placement.projection(self.sam,[r]);self.assertEqual(hints[0]['target'],asdict(card['ref']));self.assertEqual(hints[0]['origin']['path'],['summary'])
        self.assertEqual(before,self.store.db.execute('select count(*) from records').fetchone()[0])
        self.save(self.sam,t,expected=asdict(card['ref']),statement='A changed concept.')
        self.assertEqual(card_placement.projection(self.sam,[r]),[])
        self.assertEqual(card_placement.projection(self.lee,[r]),[])
    def test_legacy_review_hint_is_based_on_exact_links_not_similar_titles_and_ambiguous_matches_are_not_asserted(self):
        t=self.start();a=self.save(self.sam,t,title='Same words',relations=[self.relation(self.req['ref'])]);self.save(self.sam,t,title='Same words again')
        r=self.review(t,{'summary':'A review.','suggestions':[{'question':'What happens after the handoff?','issue':'Handoff','requirement_ids':[self.req['ref'].id]}]})
        hint=card_placement.projection(self.sam,[r])[0];self.assertEqual(hint['target'],asdict(a['ref']));self.assertEqual(hint['basis'],'linked-review');self.assertIn('Review the conceptual fit',hint['reason'])
        self.save(self.sam,t,title='A distinct concept',relations=[self.relation(self.req['ref'])]);hint=card_placement.projection(self.sam,[r])[0];self.assertIsNone(hint['target'])
    def test_assessment_uses_one_main_chat_request_exact_card_context_and_leaves_cards_unchanged(self):
        for w in (self.sam,self.lee):
            with self.subTest(domain=w.domains.key):
                t=self.start(w);card=self.save(w,t,fields={'scope':'A bounded claim.','implications':'A proposed consequence.'});before=deepcopy(card);count=len(self.model.calls)
                out=self.send(w,t,request_id='assess-'+w.actor+'-0001',card_assessment=asdict(card['ref']))
                self.assertIn('chatReport',out);self.assertEqual(len(self.model.calls),count+1)
                ctx=self.model.calls[-1]['context'];self.assertEqual(ctx['card_assessment']['ref'],asdict(card['ref']));self.assertEqual(ctx['card_assessment']['fields'],before['body']['card']['fields'])
                self.assertIn('CARD ASSESSMENT',self.model.calls[-1]['instructions']);self.assertEqual(self.store.latest(card['ref'].id,w.scopes),before)
                report=self.store.latest(out['chatReport'],w.scopes);self.save(w,t,expected=asdict(card['ref']),statement='A later private refinement.')
                self.assertTrue(w.domain_chat.report_current(report,self.current(w,t)))
                self.assertTrue(w.working_report.selection_current(report,self.current(w,t)))
                changed={**self.req['body'],'text':'A revised governing requirement.'}
                newer=self.store.put(self.req['ref'].id,self.req['kind'],self.req['scope'],changed,self.req['ref'].revision)
                self.assertFalse(w.working_report.selection_current(report,self.current(w,t)))
                self.req=self.store.read(newer,w.scopes)
    def test_assessment_rejects_other_domain_and_stale_cards_before_model_execution(self):
        t=self.start();other=self.start(self.lee);card=self.save(self.lee,other);count=len(self.model.calls)
        with self.assertRaises(PermissionError):self.send(self.sam,t,card_assessment=asdict(card['ref']))
        self.assertEqual(len(self.model.calls),count)
        own=self.save(self.sam,t);self.save(self.sam,t,expected=asdict(own['ref']),statement='Later version.')
        with self.assertRaises(StaleBasis):self.send(self.sam,t,request_id='assess-stale-0001',card_assessment=asdict(own['ref']))
        self.assertEqual(len(self.model.calls),count)

if __name__=='__main__':unittest.main()
