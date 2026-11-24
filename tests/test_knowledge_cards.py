"""Knowledge cards use actual persistence, private scopes and packet release."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.knowledge_cards import TYPES
import test_project_flow as flow
from brief_fixture import complete_design_brief


class KnowledgeCardTests(unittest.TestCase):
    setUp=flow.ProjectFlowTests.setUp
    tearDown=flow.ProjectFlowTests.tearDown
    def start(self,w=None):
        w=w or self.sam
        out=w.command('domain-chat-start',{})
        return w.domain_chat.owned(out['conversation'])
    def current(self,w,t):return w.domain_chat.owned(asdict(self.store.latest(t['ref'].id,{w.domains.scope})['ref']))
    def save(self,w,t,**kw):
        data=dict(conversation=asdict(self.current(w,t)['ref']),expected=None,type='finding',title='Responsibility across shifts',statement='The original acceptance does not establish who acts next.',rationale='Fictional task evidence; applicability remains bounded.',fields={'scope':'Fictional nonurgent shift handoff.'},relations=[],evidence=[],status='held')
        if kw.get('expected'):
            for k in ('type','title','statement','rationale','fields','relations','evidence','status'):
                if k not in kw:data.pop(k,None)
        data.update(kw);out=w.command('knowledge-card-save',data)
        return w.cards.owned(out['ref'])
    def relation(self,ref,**kw):
        return dict(relation='applies-to',ref=asdict(ref),rationale='The finding concerns this situation.',conditions='For the stated shift handoff.',**kw)
    def submission(self,w,t,cards,text='Selected professional finding.'):
        t=self.current(w,t);d=w.domain_chat.draft(t);old=w.submissions.latest(t)
        out=w.command('domain-submission-save',dict(conversation=asdict(t['ref']),expected=asdict(d['ref']),submission=asdict(old['ref']) if old else None,text=text,source_refs=[],implication_refs=[asdict(r['ref']) for r in cards],primary_source=None,review_mode='text'))
        return w.submissions.latest(t)
    def prepare(self,w,t,**extra):
        t=self.current(w,t);d=w.domain_chat.draft(t);sub=w.submissions.latest(t)
        out=w.command('domain-submission-prepare',dict(conversation=asdict(t['ref']),expected=asdict(d['ref']),submission=asdict(sub['ref']),include_evaluation=False,**extra))
        h=self.store.latest(out['domainHandoff'],w.scopes)
        return h,self.store.read(Ref(**h['body']['draft']),w.scopes)
    def publish(self,w,h,d):return w.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True))
    def test_families_new_types_and_the_applies_footer_keep_existing_blocks_valid(self):
        """D013: every type has a family and the shared footer; nothing was removed; teams get their own lead set."""
        from workbench.knowledge_cards import FAMILIES, DOMAIN_TYPES, preferred_types
        for old in ('finding','user-situation','user-flow','user-story','artifact','implication','hypothesis','challenge','dependency','performance-goal','question','note'):
            self.assertIn(old, TYPES)
        for new in ('observation','design-decision','evaluation-result','lesson'):
            self.assertIn(new, TYPES)
        for key, spec in TYPES.items():
            self.assertIn(spec['family'], FAMILIES, key)
            self.assertIn('applies_time', spec['fields'], key); self.assertIn('applies_confidence', spec['fields'], key)
            self.assertTrue(spec.get('hint'), key)
        self.assertEqual(TYPES['finding']['fields']['scope'], 'Scope and situation')          # earlier fields unchanged
        self.assertNotIn('applies_people', TYPES['user-situation']['fields'])                 # no duplicate of an existing field
        self.assertEqual(preferred_types('research')[0], 'observation'); self.assertEqual(preferred_types('design')[0], 'design-decision')
        self.assertEqual(preferred_types('unknown'), [])
        self.assertEqual(preferred_types('research', dict(config=dict(block_types=['lesson','not-a-type']))), ['lesson'])
        t=self.start(); card=self.save(self.sam,t,type='lesson',title='Phone-only rescheduling loses people',statement='Synthetic lesson.',fields=dict(population='Synthetic clinic patients',applies_time='2026',applies_confidence='Low: one synthetic study'))
        self.assertEqual(card['body']['card']['type'],'lesson')
        state=self.sam.cards.state([])
        self.assertEqual(state['preferred'],DOMAIN_TYPES['research']); self.assertEqual(state['families'],FAMILIES)
        self.assertIsNone(state['catalogue'][0]['shared'])                                    # still private

    def test_chat_capture_edits_history_and_idempotency_preserve_original_discussion(self):
        t=self.start();turn=self.sam.domain_chat.turn(t,'assistant','A true initial acceptance may no longer identify the current responder.')
        r=self.save(self.sam,t,selection=dict(turn=asdict(turn),text='initial acceptance may no longer identify the current responder'),request_id='capture-id-0001')
        again=self.save(self.sam,t,selection=dict(turn=asdict(turn),text='initial acceptance may no longer identify the current responder'),request_id='capture-id-0001')
        self.assertEqual(r,again);before=deepcopy(r)
        revised=self.save(self.sam,t,expected=asdict(r['ref']),statement='A continuing queue can retain responsibility.',fields={'scope':'Named queue after shift change.'})
        self.assertEqual(revised['ref'].id,r['ref'].id);self.assertEqual(revised['ref'].revision,2)
        self.assertEqual(self.store.read(r['ref'],self.sam.scopes),before)
        self.assertEqual(self.store.read(turn,self.sam.scopes)['body']['message'],'A true initial acceptance may no longer identify the current responder.')
        read=self.sam.command('knowledge-card-read',dict(ref=asdict(r['ref'])))
        self.assertEqual([v['ref']['revision'] for v in read['history']],[2,1])
        with self.assertRaises(StaleBasis):self.save(self.sam,t,expected=asdict(r['ref']))
    def test_user_and_assistant_passages_are_allowed_but_other_chats_and_forged_text_are_not(self):
        t=self.start();other=self.start();turn=self.sam.domain_chat.turn(t,'user','Keep this bounded working hypothesis.')
        r=self.save(self.sam,t,selection=dict(turn=asdict(turn),text='bounded working hypothesis'))
        self.assertEqual(r['body']['origin_selection']['role'],'user')
        for thread,text in [(other,'bounded working hypothesis'),(t,'invented passage')]:
            with self.subTest(text=text,thread=thread['ref'].id),self.assertRaises((ValueError,PermissionError)):
                self.save(self.sam,thread,selection=dict(turn=asdict(turn),text=text))
    def test_catalogue_and_exact_links_span_own_chats_without_cross_domain_or_owner_leaks(self):
        t=self.start();other=self.start();situation=self.save(self.sam,other,type='user-situation',title='Originator checks the next shift',fields={'people':'Originator','job':'Find the responsible responder','triggers':'Shift changes','pains':'Status is unclear','gains':'Know who acts next'})
        finding=self.save(self.sam,t,relations=[self.relation(situation['ref'])])
        state=self.sam.cards.state(self.sam.domain_chat.threads());entry=next(v for v in state['catalogue'] if v['ref']==asdict(finding['ref']))
        self.assertEqual(entry['relations'][0]['title'],situation['body']['payload']['title'])
        self.assertEqual(next(v for v in state['catalogue'] if v['ref']==asdict(situation['ref']))['backlinks'][0]['ref'],asdict(finding['ref']))
        self.assertFalse(self.lee.cards.state([])['catalogue'])
        for w in [self.lee,self.priya,self.owner]:
            with self.subTest(actor=w.actor),self.assertRaises(PermissionError):w.command('knowledge-card-read',dict(ref=asdict(finding['ref'])))
        self.assertNotIn(situation['ref'].id,str(self.lee.state()))
        # Same-domain membership does not grant ownership of another person's private card.
        from workbench.domain import DOMAINS
        original=DOMAINS['research']['authors'][:]
        try:
            DOMAINS['research']['authors'].append('maya');colleague=Workspace(self.store,'maya',domain_key='research')
            with self.assertRaises(PermissionError):colleague.command('knowledge-card-read',dict(ref=asdict(finding['ref'])))
            self.assertFalse(colleague.cards.state([])['catalogue'])
        finally:DOMAINS['research']['authors'][:]=original
    def test_invalid_types_fields_self_duplicate_and_private_links_fail_atomically(self):
        t=self.start();r=self.save(self.sam,t);private=self.store.put('PRIVATE-DESIGN','source','domain:design',dict(owner='lee',text='Private design text.'))
        count=self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        bad=[dict(type='approval'),dict(fields={'invented':'Field'}),dict(expected=asdict(r['ref']),relations=[self.relation(r['ref'])]),dict(relations=[self.relation(self.req['ref']),self.relation(self.req['ref'])]),dict(relations=[self.relation(private)])]
        for patch in bad:
            with self.subTest(patch=patch),self.assertRaises((ValueError,PermissionError)):self.save(self.sam,t,**patch)
        self.assertEqual(count,self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])
    def test_exact_source_evidence_is_checked_and_model_text_is_not_independent_evidence(self):
        t=self.start();source=self.store.put('OWN-SOURCE','source','domain:research',dict(owner='sam',title='Fictional source',text='The queue remained responsible after the shift changed.'))
        evidence=[dict(source=source.id+':v1',quote='The queue remained responsible',page=None)]
        r=self.save(self.sam,t,evidence=evidence)
        self.assertEqual(r['body']['payload']['evidence'],evidence)
        with self.assertRaises(ValueError):self.save(self.sam,t,evidence=[dict(source=source.id+':v1',quote='An invented quotation',page=None)])
        with self.assertRaises(ValueError):self.save(self.sam,t,evidence=[dict(source=r['ref'].id+':v1',quote=r['body']['payload']['statement'],page=None)])
    def test_related_card_changes_are_advisory_and_do_not_invalidate_its_neighbor(self):
        t=self.start();a=self.save(self.sam,t);b=self.save(self.sam,t,relations=[self.relation(a['ref'])])
        updated=self.save(self.sam,t,expected=asdict(a['ref']),statement='The author revised this one card.')
        b2=self.save(self.sam,t,expected=asdict(b['ref']),statement='A separate local refinement still works.')
        self.assertTrue(self.sam.implications.current(b2,t))
        meta=next(v for v in self.sam.cards.state([])['catalogue'] if v['ref']==asdict(b2['ref']))
        self.assertTrue(meta['relations'][0]['changed']);self.assertEqual(meta['relations'][0]['ref'],asdict(a['ref']));self.assertEqual(meta['relations'][0]['current'],asdict(updated['ref']))
    def test_private_packet_pins_selected_cards_and_publication_releases_only_selected_content(self):
        t=self.start();a=self.save(self.sam,t,title='Selected user situation',type='user-situation',fields={'people':'Originator','job':'Find the next responder'})
        b=self.save(self.sam,t,title='Selected finding',relations=[self.relation(a['ref'])])
        secret=self.save(self.sam,t,title='UNSELECTED SECRET',statement='Private exploratory detail that must not cross the boundary.')
        self.submission(self.sam,t,[a,b]);h,d=self.prepare(self.sam,t)
        prepared=self.store.resolve_packet(**h['body']['packet'],allowed_scopes=self.sam.scopes)
        self.assertIn(a['ref'],[r['ref'] for r in prepared['records']]);self.assertIn(b['ref'],[r['ref'] for r in prepared['records']]);self.assertNotIn(secret['ref'],[r['ref'] for r in prepared['records']])
        with self.assertRaises(PermissionError):self.store.resolve_packet(**h['body']['packet'],allowed_scopes={SCOPE})
        out=self.publish(self.sam,h,d);packet=self.store.resolve_packet(**out['packet'],allowed_scopes={SCOPE});published=[r for r in packet['records'] if r['kind']=='knowledge-card']
        self.assertEqual(len(published),2);self.assertNotIn('UNSELECTED SECRET',str(packet));self.assertNotIn('origin_selection',str(published));self.assertNotIn('domain-chat-turn',[r['kind'] for r in packet['records']])
        public_b=next(r for r in published if r['body']['title']=='Selected finding');public_a=next(r for r in published if r['body']['title']=='Selected user situation')
        self.assertEqual(public_b['body']['relations'][0]['ref'],asdict(public_a['ref']))
        self.assertEqual(public_b['body']['status'],'shared-for-review');self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
        receipt=next(r for r in packet['records'] if r['kind']=='packet-release');self.assertIn(dict(prepared=asdict(a['ref']),released=asdict(public_a['ref'])),receipt['body']['reference_map'])
        self.assertEqual(self.lee.store.read(public_a['ref'],self.lee.scopes)['body']['title'],'Selected user situation')
    def test_linked_unselected_private_cards_and_sources_cannot_leak_through_publication(self):
        t=self.start();secret=self.save(self.sam,t,title='Unselected linked card');r=self.save(self.sam,t,relations=[self.relation(secret['ref'])])
        self.submission(self.sam,t,[r]);count=self.store.db.execute('SELECT COUNT(*) FROM packets').fetchone()[0]
        with self.assertRaisesRegex(ValueError,'Select the linked private'):self.prepare(self.sam,t)
        self.assertEqual(count,self.store.db.execute('SELECT COUNT(*) FROM packets').fetchone()[0])
        source=self.store.put('PRIVATE-EVIDENCE','source','domain:research',dict(owner='sam',title='Private evidence',text='A bounded observation for the selected card.'))
        r=self.save(self.sam,t,evidence=[dict(source=source.id+':v1',quote='A bounded observation',page=None)])
        self.submission(self.sam,t,[r])
        with self.assertRaisesRegex(ValueError,'Select the cited.*source'):self.prepare(self.sam,t)
    def test_card_edits_require_new_preflight_but_prior_packets_and_public_cards_remain_exact(self):
        t=self.start();r=self.save(self.sam,t);self.submission(self.sam,t,[r]);h,d=self.prepare(self.sam,t);out=self.publish(self.sam,h,d)
        old=self.store.resolve_packet(**out['packet'],allowed_scopes={SCOPE});updated=self.save(self.sam,t,expected=asdict(r['ref']),statement='A later privately revised interpretation.')
        self.assertEqual(old,self.store.resolve_packet(**out['packet'],allowed_scopes={SCOPE}))
        self.assertNotIn('A later privately revised interpretation.',str(self.lee.state()))
        self.submission(self.sam,t,[updated]);h2,d2=self.prepare(self.sam,t);out2=self.publish(self.sam,h2,d2)
        later=self.store.resolve_packet(**out2['packet'],allowed_scopes={SCOPE});new=next(v for v in later['records'] if v['kind']=='knowledge-card')
        self.assertEqual(new['ref'].revision,2);self.assertEqual(new['body']['previous'],dict(id=new['ref'].id,revision=1))
        self.assertEqual(old['records'],self.store.resolve_packet(**out['packet'],allowed_scopes={SCOPE})['records'])
    def test_stale_or_duplicate_selections_and_changed_preflight_are_rejected(self):
        t=self.start();r=self.save(self.sam,t)
        with self.assertRaises(ValueError):self.submission(self.sam,t,[r,r])
        self.submission(self.sam,t,[r]);h,d=self.prepare(self.sam,t);self.save(self.sam,t,expected=asdict(r['ref']),statement='Later local evidence interpretation.')
        with self.assertRaises(StaleBasis):self.publish(self.sam,h,d)
        with self.assertRaises(StaleBasis):self.submission(self.sam,t,[r])
    def test_cross_chat_selected_card_enters_evaluation_and_release_with_explicit_sources(self):
        t=self.start();other=self.start()
        source=self.store.put('CROSS-CHAT-SOURCE','source','domain:research',dict(owner='sam',title='Fictional task observation',text='The responder changed at shift handoff.'))
        card=self.save(self.sam,other,evidence=[dict(source=source.id+':v1',quote='The responder changed',page=None)])
        self.submission(self.sam,t,[card]);sub=self.sam.submissions.latest(t);d=self.sam.domain_chat.draft(self.current(self.sam,t))
        out=self.sam.command('domain-submission-save',dict(conversation=asdict(self.current(self.sam,t)['ref']),expected=asdict(d['ref']),submission=asdict(sub['ref']),text='Selected authored submission.',source_refs=[asdict(source)],implication_refs=[asdict(card['ref'])],primary_source=None,review_mode='text'))
        sub=self.sam.submissions.latest(t);ctx,_=self.sam.submissions.context(self.current(self.sam,t),sub,self.sam.submissions.plan(sub)[0])
        self.assertEqual(ctx['selected_knowledge_cards'][0]['ref'],asdict(card['ref']))
        self.assertNotIn('origin_selection',str(ctx['selected_knowledge_cards']))
        self.assertIn(asdict(card['ref']),ctx['basis'])
        h,prepared=self.prepare(self.sam,t)
        with self.assertRaises(PermissionError):self.publish(self.sam,h,prepared)
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='knowledge-card'").fetchone())
        out=self.sam.command('domain-publish',dict(expected=asdict(prepared['ref']),preflight=asdict(h['ref']),confirm=True,release_sources=True))
        packet=self.store.resolve_packet(**out['packet'],allowed_scopes={SCOPE})
        shared=next(r for r in packet['records'] if r['kind']=='knowledge-card')
        self.assertNotEqual(shared['body']['evidence'][0]['ref']['id'],source.id)
        self.assertIn(Ref(**shared['body']['evidence'][0]['ref']),[r['ref'] for r in packet['records']])
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_user_flow_story_and_prototype_artifact_are_working_knowledge_not_commitments(self):
        t=self.start();before=self.store.latest(self.req['ref'].id,{SCOPE})
        for kind,fields in [('user-flow',dict(trigger='Shift ends',steps='Check status; find responder')),('user-story',dict(role='Originator',need='Know who acts next',benefit='Avoid duplicate chasing')),('artifact',dict(artifact_type='Prototype',version_label='Variant B · v2',location='https://www.figma.com/design/EXAMPLE',review_status='Untested static screens'))]:
            with self.subTest(kind=kind):
                card=self.save(self.sam,t,type=kind,fields=fields)
                self.assertEqual(card['body']['card']['fields'],fields)
                self.assertEqual(self.sam.cards.type(card),kind)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='knowledge-card'").fetchone())
    def test_drafting_submission_does_not_silently_select_all_saved_cards(self):
        t=self.start();card=self.save(self.sam,t)
        d=self.sam.domain_chat.draft(t)
        self.sam.command('domain-save',{**d['body'],'expected':asdict(d['ref']),'observation':'Authored private work.'})
        d=self.sam.domain_chat.draft(t)
        self.sam.command('domain-submission-from-draft',dict(conversation=asdict(self.current(self.sam,t)['ref']),expected=asdict(d['ref']),submission=None))
        self.assertEqual(self.sam.submissions.latest(t)['body']['implication_refs'],[])
    def test_related_record_reader_retains_exact_versions_and_enforces_private_ownership(self):
        t=self.start();card=self.save(self.sam,t);self.save(self.sam,t,expected=asdict(card['ref']),statement='A later private statement.')
        old=self.sam.command('knowledge-card-link-read',dict(ref=asdict(card['ref'])))
        self.assertEqual(old['record'],card)
        old_req=self.req;self.store.put(old_req['ref'].id,'requirement',SCOPE,{**old_req['body'],'text':'Later requirement wording'},old_req['ref'].revision)
        read=self.sam.command('knowledge-card-link-read',dict(ref=asdict(old_req['ref'])))
        self.assertEqual(read['record'],old_req)
        with self.assertRaises(PermissionError):self.lee.command('knowledge-card-link-read',dict(ref=asdict(card['ref'])))
    def test_same_card_and_packet_contract_runs_in_design_without_changing_its_brief(self):
        t=self.start(self.lee);d=self.lee.domain_chat.draft(t);plan=complete_design_brief(self.lee,d)
        r=self.save(self.lee,t,type='hypothesis',fields={'test':'Compare two fictional prototype treatments.'})
        self.submission(self.lee,t,[r]);h,prepared=self.prepare(self.lee,t);out=self.publish(self.lee,h,prepared)
        self.assertEqual(self.store.latest(plan['ref'].id,self.lee.scopes),self.store.read(plan['ref'],self.lee.scopes))
        packet=self.store.resolve_packet(**out['packet'],allowed_scopes={SCOPE})
        self.assertEqual(next(v for v in packet['records'] if v['kind']=='knowledge-card')['body']['type'],'hypothesis')
        self.assertEqual(set(self.lee.cards.state([])['types']),set(TYPES))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)

    def capture(self,w,t,selection,**extra):
        data=dict(conversation=asdict(self.current(w,t)['ref']),expected=None,type='finding',title='A bounded captured finding',section='statement',text=selection['text'],selection=selection,request_id='capture-flow-0001',confirm=True)
        data.update(extra)
        return w.command('knowledge-card-capture',data)
    def test_capture_requires_review_and_creates_one_private_version_with_exact_origin(self):
        t=self.start();turn=self.sam.domain_chat.turn(t,'assistant','Keep responsibility visible after a shift change.')
        selection=dict(turn=asdict(turn),text='responsibility visible after a shift change')
        count=self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        with self.assertRaises(ValueError):self.capture(self.sam,t,selection,confirm=False)
        self.assertEqual(count,self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])
        out=self.capture(self.sam,t,selection);r=self.sam.cards.owned(out['ref'])
        self.assertEqual(r['body']['payload']['statement'],selection['text']);self.assertEqual(r['body']['payload']['evidence'],[])
        self.assertEqual(r['body']['captures'][0]['origin']['turn'],asdict(turn));self.assertEqual(r['body']['captures'][0]['section'],'statement')
        self.assertEqual(self.store.latest(turn.id,self.sam.scopes)['body']['message'],'Keep responsibility visible after a shift change.')
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='knowledge-card'").fetchone())
    def test_capture_appends_to_existing_section_across_own_chats_and_preserves_every_other_attribute(self):
        a=self.start();b=self.start();card=self.save(self.sam,a,fields={'scope':'A bounded situation.','implications':'Existing implication.','limits':'One interview.'},relations=[self.relation(self.req['ref'])])
        before=deepcopy(card);turn=self.sam.domain_chat.turn(b,'user','Test accountability across the next shift.')
        selection=dict(turn=asdict(turn),text='Test accountability across the next shift.')
        out=self.capture(self.sam,b,selection,expected=asdict(card['ref']),section='fields.implications',text='Existing implication.\n\n'+selection['text'])
        changed=self.sam.cards.owned(out['ref']);self.assertEqual(changed['ref'].revision,2)
        self.assertEqual(changed['body']['conversation'],a['ref'].id)
        self.assertEqual(changed['body']['card']['fields']['scope'],'A bounded situation.')
        self.assertEqual(changed['body']['card']['fields']['limits'],'One interview.')
        self.assertEqual(changed['body']['card']['relations'],before['body']['card']['relations'])
        self.assertEqual(changed['body']['payload'],before['body']['payload'])
        self.assertEqual(changed['body']['captures'][0]['origin']['conversation']['id'],b['ref'].id)
        self.assertEqual(self.store.read(before['ref'],self.sam.scopes),before)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_review_capture_records_exact_leaf_and_keeps_evidence_notes_distinct_from_citations(self):
        t=self.start();review=self.store.put('REVIEW-CAPTURE','domain-chat-review','domain:research',dict(owner='sam',conversation=t['ref'].id,output={'summary':'A private assessment.','findings':[{'recommendation':'Test the unaccepted handoff.','uncertainty':'Static screen only.'}]}))
        selection=dict(review=asdict(review),path=['findings',0,'recommendation'],text='unaccepted handoff')
        out=self.capture(self.sam,t,selection,section='fields.evidence_notes',text='An untested consideration from the review.',statement='Ownership needs validation.')
        r=self.sam.cards.owned(out['ref']);self.assertEqual(r['body']['card']['fields']['evidence_notes'],'An untested consideration from the review.')
        self.assertEqual(r['body']['payload']['statement'],'Ownership needs validation.')
        self.assertEqual(r['body']['payload']['evidence'],[])
        self.assertEqual(r['body']['captures'][0]['origin']['path'],selection['path'])
        for bad in [dict(selection,text='invented wording'),dict(selection,path=['context','secret']),dict(selection,path=['findings',-1,'recommendation']),dict(selection,path=['findings',True,'recommendation'])]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.capture(self.sam,t,bad,request_id='bad-review-capture')
    def test_capture_retries_do_not_duplicate_and_concurrent_edits_do_not_overwrite(self):
        t=self.start();turn=self.sam.domain_chat.turn(t,'assistant','A selected passage.');selection=dict(turn=asdict(turn),text='selected passage')
        card=self.save(self.sam,t);kw=dict(expected=asdict(card['ref']),section='rationale',text='A revised rationale.')
        out=self.capture(self.sam,t,selection,**kw);again=self.capture(self.sam,t,selection,**kw)
        self.assertEqual(out['ref'],again['ref']);self.assertEqual(self.sam.cards.owned(out['ref'])['ref'].revision,2)
        with self.assertRaises(ValueError):self.capture(self.sam,t,selection,**dict(kw,text='Different request using same identifier.'))
        with self.assertRaises(StaleBasis):self.capture(self.sam,t,selection,**dict(kw,request_id='new-capture-stale-0001'))
        self.assertEqual(self.sam.cards.owned(out['ref'])['body']['payload']['rationale'],'A revised rationale.')
    def test_capture_rejects_other_owner_domain_forged_passages_and_unknown_sections_without_writes(self):
        t=self.start();other=self.start(self.lee);turn=self.sam.domain_chat.turn(t,'assistant','A saved Research passage.')
        alien=self.lee.domain_chat.turn(other,'assistant','A saved Design passage.')
        card=self.save(self.lee,other);selection=dict(turn=asdict(turn),text='Research passage')
        count=self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        cases=[dict(expected=asdict(card['ref'])),dict(selection=dict(turn=asdict(alien),text='Design passage')),dict(selection=dict(turn=asdict(turn),text='forged text')),dict(section='fields.invented'),dict(section='evidence'),dict(section='fields.implications',statement='')]
        for patch in cases:
            with self.subTest(patch=patch),self.assertRaises((ValueError,PermissionError)):self.capture(self.sam,t,patch.get('selection',selection),**{k:v for k,v in patch.items() if k!='selection'})
        self.assertEqual(count,self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])
    def test_capture_origin_stays_private_when_the_selected_card_is_released(self):
        t=self.start();turn=self.sam.domain_chat.turn(t,'assistant','Private scaffolding for the public-safe concept.')
        out=self.capture(self.sam,t,dict(turn=asdict(turn),text='Private scaffolding'),text='A public-safe authored finding.')
        card=self.sam.cards.owned(out['ref']);self.submission(self.sam,t,[card]);h,d=self.prepare(self.sam,t);release=self.publish(self.sam,h,d)
        packet=self.store.resolve_packet(**release['packet'],allowed_scopes={SCOPE})
        shared=next(r for r in packet['records'] if r['kind']=='knowledge-card')
        self.assertNotIn('captures',shared['body']);self.assertNotIn('Private scaffolding',str(packet));self.assertNotIn(turn.id,str(packet))

if __name__=='__main__':unittest.main()
