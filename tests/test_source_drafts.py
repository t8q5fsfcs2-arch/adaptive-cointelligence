"""Document-to-editable-draft contracts; fixtures contain no client material."""
from dataclasses import asdict
from pathlib import Path
import base64, io, tempfile, unittest, zipfile
from unittest.mock import patch

from workbench.core import Store, StaleBasis
from workbench.workspace import Workspace
from workbench.model_provider import ModelUnavailable
from workbench.source_passages import source_with_passages
from test_coaching import RecordingModel


class SourceDraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'db.sqlite3')
        self.model=RecordingModel();self.ws=Workspace(self.store,'priya',self.model)
        self.ws.command('intake-start',{'title':'Fictional source drafting'})
        doc=io.BytesIO()
        with zipfile.ZipFile(doc,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Small study: customers lose their place after asking for help.</w:t></w:r></w:p><w:p><w:r><w:t>“Resume” means keeping in-progress work; scale\u00a0unknown.</w:t></w:r></w:p></w:document>')
        self.source=self.ws.command('intake-source',{'filename':'fictional.docx','content':base64.b64encode(doc.getvalue()).decode(),'role':'evidence'})['ref']
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.ws.intake.draft()['ref'])
    def run_coach(self):
        return self.ws.command('intake-coach',{'expected':self.ref(),'skill':'seed-value','message':'Draft supported answers from these documents.','field':'business_challenge','sources':[self.source],'consent':True})['ref']
    def fill(self,run,**overrides):
        return self.ws.command('intake-coach-fill-empty',{'expected':self.ref(),'run_id':run['id'],'confirm':True,**overrides})
    def test_docx_passage_references_resolve_to_exact_stored_text(self):
        run=self.run_coach();ctx=self.model.context;src=ctx['sources'][0]
        self.assertNotIn('text',src)
        self.assertEqual(src['ref'],self.source)
        prop=self.model.schema['properties']['suggestions']['properties']['need']['anyOf'][0]['properties']
        self.assertNotIn('field',prop)
        self.assertEqual(list(prop['citations']['items']['properties']),['passage_id'])
        self.assertEqual(prop['citations']['items']['properties']['passage_id']['enum'],[p['id'] for p in src['passages']])
        saved=self.ws.coaching.records('intake-coach-run')[-1]['body']
        text=self.ws.coaching.records('intake-source')[0]['body']['text']
        c=saved['output']['suggestions'][0]['citations'][0]
        self.assertEqual(c['quote'],text[c['start']:c['end']])
        self.assertIn('“Resume”',c['quote']);self.assertIn('\u00a0',c['quote']);self.assertIn('\n',c['quote'])
        self.assertEqual(c['source_ref'],self.source)
        self.assertFalse(self.ws.intake.draft()['body']['values']['business_challenge'])
    def test_explicit_fill_is_atomic_keeps_existing_answers_and_leaves_gaps(self):
        self.ws.intake.save({'expected':self.ref(),'step':'value','business_challenge':'Keep my business wording.'})
        run=self.run_coach();before=self.ref();result=self.fill(run)
        draft=self.ws.intake.draft()['body']
        self.assertEqual(result['filled'],['need'])
        self.assertEqual(self.ref()['revision'],before['revision']+1)
        self.assertEqual(draft['values']['business_challenge'],'Keep my business wording.')
        self.assertIn('Some customers',draft['values']['need'])
        self.assertFalse(draft['values']['why_now'])
        self.assertEqual(draft['field_provenance']['need']['status'],'ai-proposed-draft')
        self.assertEqual(draft['field_provenance']['need']['origin'],'drafted-from-sources')
        self.assertFalse(self.ws.state()['intake']['value_checkpoint']['current'])
        self.assertIsNone(self.ws.intake.latest('INT-001'));self.assertFalse(self.ws.state()['decisions'])
        after=self.ref();self.assertEqual(self.fill(run)['filled'],[]);self.assertEqual(self.ref(),after)
    def test_two_empty_answers_fill_in_one_revision(self):
        run=self.run_coach();before=self.ref();result=self.fill(run)
        self.assertEqual(result['filled'],['business_challenge','need'])
        self.assertEqual(self.ref()['revision'],before['revision']+1)
    def test_edit_then_coach_uses_latest_human_text_and_keeps_source_basis(self):
        run=self.run_coach();self.fill(run)
        edited='The study suggests some customers lose their place; frequency is unknown.'
        self.ws.intake.save({'expected':self.ref(),'step':'value','need':edited})
        self.ws.command('intake-coach',{'expected':self.ref(),'skill':'coach-field','field':'need','sources':[self.source],'consent':True})
        self.assertEqual(self.model.context['working_answer']['text'],edited)
        provenance=self.ws.intake.draft()['body']['field_provenance']['need']
        self.assertEqual(provenance['status'],'sponsor-edited-after-coaching')
        self.assertEqual(provenance['citations'][0]['source_ref'],self.source)
    def test_existing_answer_proposal_can_be_edited_before_explicit_use(self):
        self.ws.intake.save({'expected':self.ref(),'step':'value','need':'Earlier answer.'})
        run=self.run_coach();self.fill(run)
        self.ws.command('intake-coach-apply',{'expected':self.ref(),'run_id':run['id'],'field':'need','edited_text':'My refined source interpretation.','confirm':True})
        draft=self.ws.intake.draft()['body']
        self.assertEqual(draft['values']['need'],'My refined source interpretation.')
        self.assertEqual(draft['field_provenance']['need']['origin'],'drafted-from-sources')
        self.assertEqual(draft['field_provenance']['need']['status'],'sponsor-edited-after-coaching')
    def test_unselected_source_and_unknown_passage_are_rejected(self):
        other=self.ws.command('intake-source',{'title':'Do not send','text':'Private unrelated material.'})['ref']
        self.run_coach();self.assertNotIn('Private unrelated material',str(self.model.context))
        for c in ({'passage_id':other['id']+'@1:p1'},{'passage_id':'made-up'}, {'source_id':self.source['id'],'quote':'invented'}):
            self.model.custom={'reply':'Draft','questions':[],'suggestions':[{'field':'need','text':'Candidate','rationale':'Reason','basis':'source-supported','citations':[c]}]}
            with self.assertRaises(ModelUnavailable):self.run_coach()
        self.assertFalse(self.ws.intake.draft()['body']['values']['need'])
    def test_stale_or_unconfirmed_fill_never_overwrites_edits(self):
        run=self.run_coach()
        with self.assertRaises(ValueError):self.fill(run,confirm=False)
        with self.assertRaises(PermissionError):Workspace(self.store,'sam',self.model).command('intake-coach-fill-empty',{})
        self.ws.intake.save({'expected':self.ref(),'step':'value','need':'New human answer.'})
        with self.assertRaises(StaleBasis):self.fill(run)
        self.assertEqual(self.ws.intake.draft()['body']['values']['need'],'New human answer.')
    def test_changed_configuration_blocks_fill(self):
        run=self.run_coach();current=self.ws.coaching.settings.coaching()
        with patch.object(self.ws.coaching.settings,'coaching',return_value={**current,'fingerprint':'changed'}):
            with self.assertRaises(StaleBasis):self.fill(run)
        self.assertFalse(self.ws.intake.draft()['body']['values']['need'])


class PassageTests(unittest.TestCase):
    def test_long_source_preserves_all_non_whitespace_with_exact_offsets(self):
        text=(' Paragraph with smart “quotes”,\u00a0spacing, and line breaks.\n'*100)+'x'*1900
        s=source_with_passages({'id':'SRC','ref':{'id':'SRC','revision':7},'title':'Synthetic','text':text})
        passages=s['passages']
        self.assertGreater(len(passages),4)
        for p in passages:
            self.assertEqual(p['text'],text[p['start']:p['end']]);self.assertLessEqual(len(p['text']),900)
            self.assertIn('@7:',p['id'])
        self.assertEqual(''.join(''.join(p['text'].split()) for p in passages),''.join(text.split()))
        self.assertEqual(len({p['id'] for p in passages}),len(passages))

class DocumentContractTests(unittest.TestCase):
    def test_field_slots_are_unique_nullable_and_keep_internal_proposals_compatible(self):
        from workbench.intake_coach import IntakeCoachAgent, FIELDS, response_schema
        context={'skill':'seed-value','values':{},'sources':[]}
        schema=response_schema(context)['properties']['suggestions']
        self.assertEqual(schema['type'],'object')
        self.assertEqual(set(schema['properties']),set(FIELDS))
        self.assertEqual(set(schema['required']),set(FIELDS))
        self.assertFalse(schema['additionalProperties'])
        for slot in schema['properties'].values():
            self.assertEqual(slot['anyOf'][1],{'type':'null'})
            self.assertNotIn('field',slot['anyOf'][0]['properties'])
        slots={f:None for f in FIELDS}
        slots['need']={'text':'A supported need','rationale':'Source','basis':'source-supported','citations':[]}
        out=IntakeCoachAgent.document_output({'reply':'Draft','suggestions':slots,'questions':[]})
        self.assertEqual(out['suggestions'],[{'field':'need',**slots['need']}])
        self.assertIsNone(slots['value'])
        for bad in ([],{**slots,'work_kind':None},{k:v for k,v in slots.items() if k!='need'},
                    {**slots,'need':{'field':'value','text':'Cannot redirect'}}):
            with self.assertRaises(ModelUnavailable):
                IntakeCoachAgent.document_output({'reply':'Draft','suggestions':bad,'questions':[]})
