from copy import deepcopy
from dataclasses import asdict
import json
import unittest

import test_domain_chat as fixture
from workbench.core import Store, StaleBasis
from workbench.workspace import Workspace
from workbench.decisions import SCOPE

class WorkingReportTests(unittest.TestCase):
    setUp=fixture.ChatTests.setUp
    tearDown=fixture.ChatTests.tearDown
    start=fixture.ChatTests.start
    current=fixture.ChatTests.current
    draft=fixture.ChatTests.draft
    attach=fixture.ChatTests.attach
    send=fixture.ChatTests.send
    def review(self,visual=False):
        w=self.lee if visual else self.sam;t=self.attach(w,self.start(w),pdf=visual);out=self.send(w,t)
        return w,t,self.store.latest(out['chatReport'],w.scopes)
    def add(self,w,t,r,**extra):
        return w.command('domain-report-add',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref']),report=asdict(r['ref']),index=0,confirm=True,**extra))
    def save(self,w,t,entries,expected=None):
        return w.command('domain-report-save',dict(conversation=asdict(self.current(w,t)['ref']),expected=expected or asdict(self.draft(w,t)['ref']),entries=entries))
    def editable(self,w,t):return [{k:e[k] for k in ('id','heading','text')} for e in self.draft(w,t)['body']['working_report']['entries']]
    def test_selecting_advice_versions_draft_but_never_calls_a_second_model_or_changes_review(self):
        w,t,r=self.review();before=self.draft(w,t);original=deepcopy(r);calls=len(self.model.calls)
        self.add(w,t,r);after=self.draft(w,t);entry=after['body']['working_report']['entries'][0]
        self.assertEqual(len(self.model.calls),calls);self.assertEqual(after['ref'].revision,before['ref'].revision+1)
        self.assertEqual(self.store.read(r['ref'],w.scopes),original);self.assertEqual(entry['origin']['review'],asdict(r['ref']))
        self.assertEqual(entry['citations'][0]['ref'],r['body']['source']);self.assertIn('prevalence is unknown',entry['text'])
        self.assertTrue(w.working_report.selection_current(r,self.current(w,t)));self.assertFalse(w.domain_chat.state()['reports'][0]['current'])
    def test_duplicate_selection_does_not_duplicate_content_or_revision(self):
        w,t,r=self.review();self.add(w,t,r);before=self.draft(w,t)['ref'];result=self.add(w,t,r)
        self.assertTrue(result['duplicate']);self.assertEqual(self.draft(w,t)['ref'],before)
    def test_edit_reorder_remove_and_own_sections_preserve_old_versions_and_original_citations(self):
        w,t,r=self.review();self.add(w,t,r);old=self.draft(w,t);entries=self.editable(w,t)
        entries[0]['text']='Author-refined conclusion; evidence is limited.'
        entries.insert(0,dict(id='new-authored',heading='My conclusion',text='A bounded recommendation, not a confirmed outcome.'))
        self.save(w,t,entries);new=self.draft(w,t)
        self.assertEqual(new['body']['working_report']['entries'][0]['heading'],'My conclusion')
        self.assertEqual(new['body']['working_report']['entries'][1]['citations'],old['body']['working_report']['entries'][0]['citations'])
        self.assertNotEqual(self.store.read(old['ref'],w.scopes)['body']['working_report'],new['body']['working_report'])
        self.save(w,t,[self.editable(w,t)[1]]);self.assertEqual(len(self.draft(w,t)['body']['working_report']['entries']),1)
        self.assertGreaterEqual(len(w.domain_chat.state()['working_history']),3)
        self.assertNotIn('report',w.domain_chat.state()['working_history'][0])
        viewed=w.command('domain-report-read',dict(conversation=asdict(self.current(w,t)['ref']),version=asdict(old['ref'])))
        self.assertEqual(viewed['report'],old['body']['working_report'])
        self.assertEqual(self.draft(w,t)['body']['working_report']['entries'][0]['text'],'Author-refined conclusion; evidence is limited.')
    def test_stale_writes_and_forged_origin_are_rejected_atomically(self):
        w,t,r=self.review();self.add(w,t,r);old=self.draft(w,t);entries=self.editable(w,t);entries[0]['text']='Saved author revision.';self.save(w,t,entries)
        count=self.store.db.execute('select count(*) from records').fetchone()[0]
        with self.assertRaises(StaleBasis):self.save(w,t,entries,asdict(old['ref']))
        entries[0]['origin']={'review':asdict(r['ref'])}
        with self.assertRaises(ValueError):self.save(w,t,entries)
        self.assertEqual(self.store.db.execute('select count(*) from records').fetchone()[0],count)
    def test_other_role_and_other_conversation_cannot_select_private_advice(self):
        w,t,r=self.review();other=self.start(self.lee)
        with self.assertRaises(PermissionError):self.add(self.lee,other,r)
        unrelated=self.start(w)
        with self.assertRaises(PermissionError):self.add(w,unrelated,r)
        self.assertFalse(self.lee.domain_chat.state()['working_history'])
        with self.assertRaises(PermissionError):self.lee.command('domain-report-read',dict(conversation=asdict(self.current(self.lee,other)['ref']),version=asdict(self.draft(w,t)['ref'])))
    def test_changed_inputs_require_historical_acknowledgement(self):
        w,t,r=self.review();d=self.draft(w,t)
        w.command('domain-save',{**d['body'],'expected':asdict(d['ref']),'observation':'Revised observation contradicts the earlier interpretation.'})
        with self.assertRaises(StaleBasis):self.add(w,t,r)
        self.add(w,t,r,confirm_historical=True)
        self.assertTrue(self.draft(w,t)['body']['working_report']['entries'][0]['origin']['historical_confirmed'])
    def test_report_survives_normal_deliverable_edits_and_restart(self):
        w,t,r=self.review();self.add(w,t,r);d=self.draft(w,t);report=deepcopy(d['body']['working_report'])
        w.command('domain-save',{**d['body'],'expected':asdict(d['ref']),'title':'Renamed authored work'})
        self.assertEqual(self.draft(w,t)['body']['working_report'],report)
        self.assertTrue(self.store.db.execute('SELECT 1 FROM dependencies WHERE dependent_id=? AND dependent_revision=? AND basis_id=?',(self.draft(w,t)['ref'].id,self.draft(w,t)['ref'].revision,r['ref'].id)).fetchone())
        reopened=Store(self.path)
        try:
            restored=Workspace(reopened,'sam');self.assertTrue(restored.domain_chat.state()['working_history'])
            self.assertEqual(restored.latest_records('contribution-draft')[0]['body']['working_report'],report)
        finally:reopened.close()
    def test_visual_findings_have_page_specific_citations(self):
        w,t,r=self.review(True);self.add(w,t,r);entry=self.draft(w,t)['body']['working_report']['entries'][0]
        self.assertEqual(entry['citations'][0]['page'],r['body']['output']['findings'][0]['page']);self.assertIn('Recommendation',entry['text']);self.assertEqual(entry['requirement_refs'],[asdict(self.req['ref'])])
    def test_preflight_includes_exact_report_and_publication_releases_only_selected_content(self):
        w,t,r=self.review();self.add(w,t,r);d=self.draft(w,t)
        prepared=w.command('domain-prepare',dict(expected=asdict(d['ref']),recipient='design'))
        h=self.store.latest(prepared['domainHandoff'],w.scopes);p=self.store.resolve_packet(h['body']['packet']['id'],1,w.scopes)
        draft_record=next(x for x in p['records'] if x['kind']=='contribution-draft')
        self.assertEqual(draft_record['body']['working_report'],d['body']['working_report'])
        self.assertFalse(any(x['kind']=='domain-chat-review' for x in p['records']))
        out=w.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True,release_sources=True))
        shared=self.store.latest(out['id'],{SCOPE});citation=shared['body']['working_report']['entries'][0]['citations'][0]
        self.assertTrue(citation['ref']['id'].startswith('RELEASE-'));self.store.read(fixture.Ref(**citation['ref']),{SCOPE})
        packet=self.store.resolve_packet(out['packet']['id'],out['packet']['revision'],{SCOPE})
        self.assertFalse(any(x['kind'] in ('domain-chat-review','domain-chat-turn','domain-conversation') for x in packet['records']))
        design=self.lee.command('domain-chat-start',{});design_draft=self.store.latest(design['id'],self.lee.scopes)
        downstream=self.lee.domains.context(asdict(design_draft['ref']))
        self.assertTrue(any(x['body'].get('working_report')==shared['body']['working_report'] for x in downstream['upstream_contributions']))
        entries=self.editable(w,t);entries[0]['text']='Further author refinement.';self.save(w,t,entries)
        with self.assertRaises(StaleBasis):w.command('domain-publish',dict(expected=asdict(self.draft(w,t)['ref']),preflight=asdict(h['ref']),confirm=True,release_sources=True))
        self.assertEqual(self.store.latest(out['id'],{SCOPE})['body'],shared['body'])
    def test_edit_after_sharing_republishes_a_new_report_without_replacing_the_bridge_history(self):
        w,t,r=self.review();self.add(w,t,r);d=self.draft(w,t);calls=len(self.model.calls)
        prepared=w.command('domain-prepare',dict(expected=asdict(d['ref']),recipient='bridge'))
        handoff=self.store.latest(prepared['domainHandoff'],w.scopes)
        first=w.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(handoff['ref']),confirm=True,release_sources=True))
        published=self.store.latest(first['id'],{SCOPE});old=deepcopy(published['body']);old_packet=self.store.resolve_packet(first['packet']['id'],first['packet']['revision'],{SCOPE})
        entries=self.editable(w,t);entries[0]['text']='Author revised the recommendation after the first handoff.';self.save(w,t,entries)
        self.assertEqual(self.store.latest(first['id'],{SCOPE})['body'],old)
        current=self.draft(w,t);next_preflight=w.command('domain-prepare',dict(expected=asdict(current['ref']),recipient='bridge'))
        next_handoff=self.store.latest(next_preflight['domainHandoff'],w.scopes)
        second=w.command('domain-publish',dict(expected=asdict(current['ref']),preflight=asdict(next_handoff['ref']),confirm=True,release_sources=True))
        newer=self.store.latest(second['id'],{SCOPE});self.assertEqual(newer['ref'].id,published['ref'].id);self.assertEqual(newer['ref'].revision,published['ref'].revision+1)
        self.assertEqual(newer['body']['working_report']['entries'][0]['text'],entries[0]['text'])
        self.assertEqual(self.store.read(published['ref'],{SCOPE})['body'],old)
        self.assertEqual(self.store.resolve_packet(first['packet']['id'],first['packet']['revision'],{SCOPE})['records'],old_packet['records'])
        self.assertEqual(len(self.model.calls),calls)
    def test_source_removal_blocks_preflight_without_silently_releasing_an_unselected_source(self):
        w,t,r=self.review();self.add(w,t,r);d=self.draft(w,t)
        w.command('domain-save',{**d['body'],'expected':asdict(d['ref']),'source_refs':[]})
        with self.assertRaises(ValueError):w.command('domain-prepare',dict(expected=asdict(self.draft(w,t)['ref']),recipient='design'))


class WorkingReportWebTests(unittest.TestCase):
    setUp=fixture.ChatWebTests.setUp
    tearDown=fixture.ChatWebTests.tearDown
    def fetch_state(self):
        self.conn.request('GET','/api/state',headers={'Cookie':self.cookie})
        return json.loads(self.conn.getresponse().read())
    def test_real_http_curate_edit_reopen_and_privacy_without_additional_model_calls(self):
        self.conn.request('GET','/working-report.js');asset=self.conn.getresponse();self.assertEqual(asset.status,200);asset.read()
        status,started=self.post('domain-chat-start',{});self.assertEqual(status,200)
        thread=self.fetch_state()['domain_chat']['threads'][0]
        status,review=self.post('domain-chat-send',dict(conversation=thread['ref'],expected=thread['draft'],message='Review this fictional working observation.',request_id='http-report-review-001',consent=True));self.assertEqual(status,200,review)
        state=self.fetch_state();thread=state['domain_chat']['threads'][0];report=state['domain_chat']['reports'][0]
        status,added=self.post('domain-report-add',dict(conversation=thread['ref'],expected=thread['draft'],report=report['ref'],index=0,confirm=True));self.assertEqual(status,200,added)
        state=self.fetch_state();thread=state['domain_chat']['threads'][0];draft=next(r for r in state['records'] if r['ref']['id']==added['id'])
        entry=draft['body']['working_report']['entries'][0]
        status,saved=self.post('domain-report-save',dict(conversation=thread['ref'],expected=draft['ref'],entries=[dict(id=entry['id'],heading='Author conclusion',text='Retain uncertainty and investigate the reporting barrier.')]));self.assertEqual(status,200,saved)
        reopened=self.fetch_state();self.assertEqual(len(self.server.model.calls),1);self.assertEqual(len(reopened['domain_chat']['working_history']),2)
        self.post('profile',dict(actor='lee'))
        self.assertFalse(self.fetch_state()['domain_chat']['working_history'])
        status,denied=self.post('domain-report-save',dict(conversation=thread['ref'],expected=saved['ref'],entries=[]));self.assertEqual(status,403,denied)
