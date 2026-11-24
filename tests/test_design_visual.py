from brief_fixture import complete_design_brief
"""Visual review invariants with synthetic screens; no live/client evaluation."""
import base64
from copy import deepcopy
from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pdf_fixture import prototype_pdf
from workbench.core import Store,StaleBasis,Ref
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench import visual_pdf
from workbench.model_provider import ModelUnavailable,OpenAIModel


class VisualTestModel:
    def __init__(self):self.calls=[];self.bad=None;self.during=None
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='synthetic')
    def generate_visual(self,**kw):
        self.calls.append(deepcopy(kw));ctx=kw['context'];basis=ctx['requirements'][0]
        if self.during:self.during()
        out=dict(summary='The photo gate conflicts with the reporting requirement.',reviewed_pages=[p['page'] for p in ctx['pages']],limitations='Static screens do not demonstrate working submission.',findings=[dict(page=ctx['pages'][-1]['page'],area='Photo gate',assessment='tension',observation='The screen asks for a photo before submission.',rationale='This would block the reporting task.',recommendation='Allow initial reporting and retain an evidence follow-up.',context_links=[dict(ref=deepcopy(basis['ref']),quote=basis['body']['text'])],uncertainty='Confirm behavior in an interactive test.')])
        if self.bad:self.bad(out)
        return dict(output=out,model='synthetic',usage=dict(input_tokens=80,output_tokens=60))


class VisualTests(unittest.TestCase):
    def test_review_citation_index_does_not_duplicate_the_canonical_context_bodies(self):
        self.review();ctx=self.model.calls[0]['context']
        self.assertTrue(all('body' not in r for r in ctx['review_basis']))
        self.assertIn(self.req['body']['text'],str(ctx['requirements']))
        self.assertEqual(self.reports()[0]['body']['output']['findings'][0]['context_links'][0]['ref'],asdict(self.req['ref']))
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'visual.sqlite3';self.store=Store(self.path);self.model=VisualTestModel()
        owner=Workspace(self.store,'alex');owner.setup(dict(title='Synthetic Clinic',intent='Capture usable reports without interrupting maintenance.',boundary='Non-safety feedback only.'))
        result=owner.create_requirement(dict(title='Report before evidence',text='A technician can submit feedback without a photo and add evidence later.',rationale='Reduce abandoned reporting.',conditions='Non-safety only.',drawer='Experience',acceptance_criteria='Submit without a photo; preserve an evidence-pending state.'))
        self.req=self.store.latest(result['id'],{SCOPE})
        self.research=self.store.put('PUB-SYNTHETIC','contribution',SCOPE,dict(domain_key='research',domain='Research',title='Fictional reporting study',observation='Six invented technicians paused to collect a photo and abandoned reporting.',limitation='Synthetic illustration; not empirical evidence.'))
        self.lee=Workspace(self.store,'lee',self.model);self.pdf=prototype_pdf()
        self.src=self.lee.command('domain-source',dict(filename='fictional.pdf',content=base64.b64encode(self.pdf).decode()))['ref']
        result=self.lee.command('domain-save',dict(title='Fictional prototype',deliverable_type=self.lee.domains.profile()['config']['deliverable_types'][0],observation='Two alternative static screens.',source='Fictional PDF',interpretation='Compare capture with evidence follow-up.',recommendation='Review the photo gate.',limitation='No interactions tested.',source_refs=[self.src],input_refs=[asdict(self.research)],links=[dict(ref=asdict(self.req['ref']),relation='refines',rationale='Test the reporting requirement')]))
        self.draft=self.store.latest(result['id'],self.lee.scopes)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def request(self,**extra):return {**dict(expected=asdict(self.draft['ref']),source=self.src,pages=[1,2],question='Can a technician report before adding evidence?',consent=True),**extra}
    def review(self,**extra):return self.lee.command('design-visual-review',self.request(**extra))
    def reports(self):return self.lee.design_visual.state()['reports']

    def test_actual_images_exact_context_no_text_from_unselected_screens(self):
        before=self.store.read(self.draft['ref'],self.lee.scopes);result=self.review(pages=[2]);call=self.model.calls[0];ctx=call['context']
        self.assertTrue(base64.b64decode(call['images'][0]['data']).startswith(b'\x89PNG'))
        self.assertEqual([p['page'] for p in ctx['pages']],[2]);self.assertEqual(len(call['images']),1)
        self.assertEqual(ctx['requirements'][0]['ref'],asdict(self.req['ref']));self.assertEqual(ctx['upstream_contributions'][0]['ref'],asdict(self.research))
        self.assertTrue(ctx['business_intent']);self.assertFalse(ctx['sources'])
        self.assertNotIn('Photo (optional - add it later)',json.dumps(ctx))
        self.assertEqual(self.store.read(self.draft['ref'],self.lee.scopes),before)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
        report=self.reports()[0];self.assertTrue(report['current']);self.assertEqual(report['body']['mode'],'simulated')
        self.assertEqual(report['ref'].id,result['visualReport']);self.assertEqual(report['basis_records'][0]['ref'],self.req['ref'])
        run=self.lee.latest_records('agent-execution')[0]
        self.assertEqual(run['body']['status'],'succeeded');self.assertNotIn('data:image',json.dumps(run['body']))
        self.assertNotIn('iVBOR',json.dumps(run['body']));self.assertEqual(run['body']['usage']['input_tokens'],80)

    def test_original_and_cache_survive_reopen_without_rerender(self):
        meta,image=visual_pdf.page(self.lee,self.src,2);self.assertLessEqual(max(meta['width'],meta['height']),1600)
        original=self.store.db.execute('SELECT content FROM visual_pdf_files').fetchone()['content'];self.assertEqual(original,self.pdf)
        self.store.close();self.store=Store(self.path);self.lee=Workspace(self.store,'lee',self.model)
        with patch('workbench.visual_pdf.run',side_effect=AssertionError('cached page must not rerender')):
            self.assertEqual(visual_pdf.page(self.lee,self.src,2),(meta,image))
        self.assertNotIn(base64.b64encode(self.pdf).decode(),json.dumps(self.lee.state(),default=lambda x:asdict(x)))

    def test_reuse_and_stale_requirement(self):
        first=self.review()['visualReport'];self.assertEqual(self.review()['visualReport'],first);self.assertEqual(len(self.model.calls),1)
        self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Revised requirement'},self.req['ref'].revision)
        self.assertFalse(self.reports()[0]['current'])
        with self.assertRaises(StaleBasis):self.review()

    def test_changed_draft_during_review_saves_stale_receipt_without_review(self):
        self.model.during=lambda:self.store.put(self.draft['ref'].id,'contribution-draft','domain:design',{**self.draft['body'],'recommendation':'Author edited during review'},self.draft['ref'].revision)
        with self.assertRaises(StaleBasis):self.review()
        self.assertFalse(self.reports());self.assertEqual(self.lee.latest_records('agent-execution')[0]['body']['status'],'stale')

    def test_invalid_output_rejected_with_no_substitute(self):
        for bad in (lambda o:o['findings'][0].update(page=3),lambda o:o.update(reviewed_pages=[True,2]),lambda o:o['findings'][0]['context_links'][0].update(quote='invented evidence'),lambda o:o['findings'][0]['context_links'][0]['ref'].update(revision=100),lambda o:o['findings'][0]['context_links'][0]['ref'].update(id='UNSELECTED')):
            self.model.bad=bad
            with self.assertRaisesRegex(ModelUnavailable,'could not verify'):self.review()
            self.assertFalse(self.reports())
        self.assertTrue(all(r['body']['status']=='failed' for r in self.lee.latest_records('agent-execution')))

    def test_only_design_can_read_original_pages_or_visual_reports(self):
        self.review()
        for actor in ('sam','priya','alex','maya'):
            other=Workspace(self.store,actor,self.model)
            with self.assertRaises(PermissionError):visual_pdf.page(other,self.src,1)
            with self.assertRaises(PermissionError):other.command('design-visual-review',self.request())
            self.assertIsNone(other.state()['design_visual'])

    def test_selection_consent_and_complete_context_are_required(self):
        for changes in (dict(pages=[]),dict(pages=[1,1]),dict(pages=[3]),dict(pages=[True]),dict(consent=False)):
            with self.assertRaises(ValueError):self.review(**changes)
        modified={**self.draft['body'],'input_refs':[]}
        d=self.store.put(self.draft['ref'].id,'contribution-draft','domain:design',modified,self.draft['ref'].revision)
        with self.assertRaisesRegex(ValueError,'published Research'):self.review(expected=asdict(d))
        self.assertFalse(self.model.calls)

    def test_unselected_private_research_is_excluded_and_unrelated_change_is_not_stale(self):
        self.store.put('PRIVATE-SECRET','contribution-draft','domain:research',dict(observation='Sensitive unselected data'))
        self.review();self.assertNotIn('Sensitive unselected data',json.dumps(self.model.calls[0]['context']))
        self.store.put('UNRELATED','contribution',SCOPE,dict(domain='Research',observation='Unrelated new finding'))
        self.assertTrue(self.reports()[0]['current'])

    def test_image_only_and_malformed_encrypted_and_oversize_pdfs(self):
        writer=PdfWriter();writer.add_blank_page(400,300);out=io.BytesIO();writer.write(out)
        payload,raw=visual_pdf.extract_visual(dict(filename='scan.pdf',content=base64.b64encode(out.getvalue()).decode()))
        self.assertEqual(payload['visual_pdf']['page_count'],1);self.assertIn('No extractable text',payload['text'])
        writer.encrypt('secret');encrypted=io.BytesIO();writer.write(encrypted)
        for data in (b'not a pdf',encrypted.getvalue(),b'%PDF-'+b'0'*(5*1024*1024)):
            with self.assertRaises(ValueError):visual_pdf.extract_visual(dict(filename='x.pdf',content=base64.b64encode(data).decode()))
        with patch('workbench.visual_pdf.shutil.which',return_value=None):
            with self.assertRaisesRegex(ValueError,'Poppler'):visual_pdf.extract_visual(dict(filename='x.pdf',content=base64.b64encode(self.pdf).decode()))

    def test_original_and_image_integrity_checks(self):
        self.store.db.execute('UPDATE visual_pdf_files SET content=?',(b'corrupt',));self.store.db.commit()
        with self.assertRaisesRegex(ValueError,'integrity'):visual_pdf.page(self.lee,self.src,1)
        self.store.db.execute('UPDATE visual_pdf_files SET content=?',(self.pdf,));self.store.db.commit()
        visual_pdf.page(self.lee,self.src,1)
        self.store.db.execute('UPDATE visual_pdf_pages SET content=?',(b'corrupt',));self.store.db.commit()
        with self.assertRaisesRegex(ValueError,'integrity'):visual_pdf.page(self.lee,self.src,1)

    def test_visual_request_uses_real_image_content_parts_no_tools_and_no_storage(self):
        reply=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text='{"ok":true}')])])
        meta,image=visual_pdf.page(self.lee,self.src,1)
        with patch('workbench.model_provider.urlopen',return_value=io.BytesIO(json.dumps(reply).encode())) as call:
            OpenAIModel('fake','configured-model').generate_visual(instructions='Review images',context=dict(skill='design-pdf-review'),schema=dict(type='object'),images=[dict(label='Page 1',mime_type='image/png',data=base64.b64encode(image).decode())])
        request=call.call_args.args[0];payload=json.loads(request.data)
        self.assertEqual(payload['model'],'configured-model');self.assertFalse(payload['store']);self.assertNotIn('tools',payload)
        self.assertEqual(payload['input'][0]['content'][-1]['type'],'input_image')
        self.assertEqual(base64.b64decode(payload['input'][0]['content'][-1]['image_url'].split(',')[1]),image)
        self.assertEqual(call.call_args.kwargs['timeout'],180);self.assertEqual(call.call_count,1)


    def test_attach_pdf_is_atomic_and_preserves_other_draft_fields(self):
        result=self.lee.command('design-pdf-attach',dict(expected=asdict(self.draft['ref']),filename='new.pdf',content=base64.b64encode(self.pdf+b'\n% revision two').decode()))
        current=self.store.latest(result['id'],self.lee.scopes)
        self.assertEqual(current['body']['observation'],self.draft['body']['observation'])
        self.assertEqual(current['body']['input_refs'],self.draft['body']['input_refs'])
        self.assertEqual(len(current['body']['source_refs']),2)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM visual_pdf_files').fetchone()[0],2)
        self.store.put(self.req['ref'].id,'requirement',SCOPE,self.req['body'],self.req['ref'].revision)
        with self.assertRaises(StaleBasis):
            self.lee.command('design-pdf-attach',dict(expected=asdict(current['ref']),filename='failed.pdf',content=base64.b64encode(self.pdf+b'\n% revision three').decode()))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM visual_pdf_files').fetchone()[0],2)
        self.assertEqual(self.store.latest(current['ref'].id,self.lee.scopes),current)

    def test_profile_changes_stale_visual_review(self):
        self.review();profile=self.lee.domains.profile()
        from workbench.domain import EDITABLE
        config={key:deepcopy(profile['config'][key]) for key in EDITABLE};config['coach_guidance']='Prioritize technician interruption recovery.'
        self.lee.command('domain-configure',dict(domain='design',expected=profile['ref'],config=config,reason='Synthetic SME refinement'))
        self.assertFalse(self.reports()[0]['current'])

    def test_publication_releases_text_only_when_explicitly_authorized(self):
        complete_design_brief(self.lee,self.draft)
        preflight=self.lee.command('domain-prepare',dict(expected=asdict(self.draft['ref']),recipient='research'))
        handoff=self.store.latest(preflight['domainHandoff'],self.lee.scopes)
        out=self.lee.command('domain-publish',dict(expected=asdict(self.draft['ref']),preflight=asdict(handoff['ref']),confirm=True,release_sources=True))
        contribution=self.store.latest(out['id'],{SCOPE});released=self.store.read(Ref(**contribution['body']['source_refs'][0]),{SCOPE})
        self.assertNotIn('visual_pdf',released['body']);self.assertFalse(released['body']['original_retained'])
        self.assertIn('Photo required',released['body']['text'])
        with self.assertRaises(PermissionError):visual_pdf.page(Workspace(self.store,'sam'),self.src,1)



class VisualPageWebTests(unittest.TestCase):
    def setUp(self):
        from test_web import WebTests
        WebTests.setUp(self)
        self.post=WebTests.post.__get__(self)
        self.assertEqual(self.post('profile',dict(actor='lee'))[0],200)
        with self.server.projects.locked(self.state['project']['id']) as project:
            store=Store(project['path'])
            self.source=Workspace(store,'lee').command('domain-source',dict(filename='synthetic.pdf',content=base64.b64encode(prototype_pdf()).decode()))['ref']
            store.close()
        from urllib.parse import urlencode
        self.url='/api/design-page?'+urlencode(dict(project=self.state['project']['id'],generation=self.state['project']['version'],source=self.source['id'],revision=self.source['revision'],page=1))
    def tearDown(self):
        from test_web import WebTests
        WebTests.tearDown(self)
    def get(self,url,**headers):
        self.conn.request('GET',url,headers={'Cookie':self.cookie,**headers});response=self.conn.getresponse();return response,response.read()
    def test_page_route_returns_private_png_with_access_and_generation_guards(self):
        response,data=self.get(self.url);self.assertEqual(response.status,200);self.assertTrue(data.startswith(b'\x89PNG'));self.assertEqual(response.getheader('Cache-Control'),'no-store');self.assertEqual(response.getheader('Content-Type'),'image/png')
        self.assertEqual(self.get(self.url,Origin='https://unrelated.example')[0].status,403)
        self.assertEqual(self.get(self.url.replace('page=1','page=3'))[0].status,400)
        self.assertEqual(self.get(self.url.replace('generation=1','generation=999'))[0].status,400)
        self.assertEqual(self.post('profile',dict(actor='sam'))[0],200)
        self.assertEqual(self.get(self.url)[0].status,403)
    def test_visual_assets_are_served_under_existing_csp(self):
        for url in ('/design-visual.js','/design-visual.css'):
            response,data=self.get(url);self.assertEqual(response.status,200);self.assertIn("frame-ancestors 'none'",response.getheader('Content-Security-Policy'));self.assertGreater(len(data),100)
