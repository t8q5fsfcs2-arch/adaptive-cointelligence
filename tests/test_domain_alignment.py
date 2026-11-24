from copy import deepcopy
from dataclasses import asdict
import unittest
import test_domain_chat as fixture
from workbench.core import StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench import domain_alignment
from workbench.business_assessments import standard as reasoning_standard, DIMENSIONS as REASONING_DIMENSIONS
from unittest.mock import patch

def scoped_confidence(ctx,target,level='low'):
    standard=reasoning_standard();ids=list(domain_alignment.passage_catalog(ctx))[:1]
    return dict(framework='evidence-reasoning-v1',standard=dict(id=standard['id'],revision=standard['revision']),level=level,
        claim=target['body'].get('text') or target['body'].get('title'),scope='Only the supplied fictional observation and selected target.',
        rationale='The source supports a bounded interpretation; it does not establish wider behavior.',limits='Other contexts, runtime behavior and delivered benefits remain untested.',
        patterns=dict(status='single-line',families=[dict(key='observation-family',passage_ids=ids,relationship='unknown',rationale='This is one selected fictional source family.')],recurrence='Only one fictional observation is supplied.',exceptions='Alternative explanations remain open.',population_limits='No wider population inference is established.'),dimensions={key:dict(judgment='limited',rationale='This fictional observation supplies limited support for this aspect.',passage_ids=ids if key=='evidence-quality' else [],limits='This aspect needs additional scoped evidence.') for key in REASONING_DIMENSIONS})

class AlignmentModel(fixture.ChatModel):
    def __init__(self):super().__init__();self.invalid=None
    def generate(self,**kw):
        result=super().generate(**kw);ctx=kw['context']
        if 'alignment' not in kw['schema']['properties']:return result
        source=ctx['sources'][0];targets=ctx['requirements'][:1]+ctx['goals_and_measures'][:1]
        result['output']['alignment']=[dict(target=domain_alignment.key(t['ref']),criterion=t['body'].get('acceptance_criteria','') if t['kind']=='requirement' else '',assessment='gap',rationale='The single invented observation does not establish coverage.',evidence=[dict(source=domain_alignment.key(source['ref']),quote=source['body']['text'],page=None)],confidence=scoped_confidence(ctx,t),gaps=['Interview additional relevant users; draft probes around interrupted work.']) for t in targets]
        if self.invalid:self.invalid(result['output']['alignment'][0])
        return result

    def generate_visual(self,**kw):
        result=super().generate_visual(**kw);ctx=kw['context']
        if 'alignment' in kw['schema']['properties']:
            result['output']['alignment']=[dict(target=domain_alignment.key(ctx['requirements'][0]['ref']),criterion='',assessment='appears-met',rationale='The selected static screen depicts the criterion; behavior needs testing.',evidence=[dict(source=domain_alignment.key(ctx['visual_source']['ref']),quote='',page=ctx['pages'][0]['page'])],confidence=scoped_confidence(ctx,ctx['requirements'][0]),gaps=['Test the interaction with representative users.'])]
        return result

class AlignmentTests(unittest.TestCase):
    tearDown=fixture.ChatTests.tearDown
    start=fixture.ChatTests.start
    current=fixture.ChatTests.current
    draft=fixture.ChatTests.draft
    attach=fixture.ChatTests.attach
    send=fixture.ChatTests.send
    def setUp(self):
        fixture.ChatTests.setUp(self);self.model=AlignmentModel();self.sam=Workspace(self.store,'sam',self.model)
        goal=self.store.put('GOAL-TEST','goal',SCOPE,dict(title='Capture useful feedback',outcome='Reduce abandoned reporting.'))
        raw=self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'goal_refs':[asdict(goal)]},self.req['ref'].revision)
        self.req=self.store.read(raw,{SCOPE});self.t=self.attach(self.sam,self.start(),text='One fictional participant paused reporting to collect a photo. All data is invented.')
    def rows(self):return self.sam.domain_chat.state()['alignment']
    def assess(self,row,**extra):
        return self.sam.command('domain-alignment-save',{**dict(conversation=asdict(self.current(self.sam,self.t)['ref']),review=row['review'],index=row['index'],expected=row['edit_ref'],assessment='gap',note='The researcher confirms the bounded gap; more interviews are needed.',confirmed=True,confidence=row['confidence_values']),**extra})
    def test_review_logs_requirements_criteria_goals_and_provisional_confidence_in_same_call(self):
        before=self.draft(self.sam,self.t);out=self.send(self.sam,self.t,purpose='review');self.assertIn('chatReport',out)
        rows=self.rows();self.assertEqual(len(rows),2);self.assertEqual({r['target_kind'] for r in rows},{'requirement','goal'})
        self.assertTrue(any(r['criterion'] for r in rows));self.assertTrue(all(r['confidence']['level']=='low' for r in rows));self.assertTrue(all(r['confidence']['framework']=='evidence-reasoning-v1' and 'score' not in r['confidence'] for r in rows));self.assertEqual(set(rows[0]['confidence']['dimensions']),set(REASONING_DIMENSIONS));self.assertEqual(self.model.calls[-1]['context']['evidence_reasoning_standard']['ref'],rows[0]['confidence']['standard']);self.assertFalse(any(r['confirmed'] for r in rows))
        self.assertEqual(self.draft(self.sam,self.t),before);self.assertEqual(len(self.model.calls),1);self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_author_can_edit_confirm_and_reopen_versioned_assessment_without_project_approval(self):
        self.send(self.sam,self.t,purpose='review');row=self.rows()[0];saved=self.assess(row);current=self.rows()[0]
        self.assertTrue(current['confirmed']);self.assertEqual(current['edit_ref'],saved['ref']);self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
        with self.assertRaises(StaleBasis):self.assess(row)
        out=self.assess(current,confirmed=False);self.assertFalse(self.rows()[0]['confirmed']);self.assertGreater(out['ref']['revision'],saved['ref']['revision'])
    def test_changed_requirement_preserves_history_but_invalidates_confirmation(self):
        self.send(self.sam,self.t,purpose='review');row=self.rows()[0];self.assess(row)
        self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'A newly ratified requirement.'},self.req['ref'].revision)
        current=self.rows()[0];self.assertFalse(current['current']);self.assertFalse(current['confirmed']);self.assertTrue(current['human']['confirmed'])
        with self.assertRaises(StaleBasis):self.assess(current)
    def test_other_domain_cannot_inspect_or_edit_private_assessment(self):
        self.send(self.sam,self.t,purpose='review');row=self.rows()[0]
        self.assertEqual(self.lee.domain_chat.state()['alignment'],[])
        with self.assertRaises(PermissionError):self.lee.command('domain-alignment-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),review=row['review'],index=row['index']))
    def test_hallucinated_targets_criteria_quotes_and_uncited_passes_are_rejected(self):
        mutations=[lambda r:r.update(target='SECRET:v1'),lambda r:r.update(criterion='Invented criterion'),lambda r:r['evidence'][0].update(quote='Invented quotation'),lambda r:r.update(assessment='appears-met',evidence=[])]
        for i,mutate in enumerate(mutations):
            self.model.invalid=mutate;out=self.send(self.sam,self.t,purpose='review',request_id='invalid-alignment-'+str(i));self.assertIn('chat_error',out)
        self.assertEqual(self.rows(),[])
    def test_legacy_history_keeps_its_original_score_without_translation_to_common_confidence(self):
        values=dict(grounding=3,corroboration=3,coverage=3,applicability=3,participant_count=None)
        self.assertEqual(domain_alignment.confidence(values,[])['score'],0)
        self.assertEqual(domain_alignment.confidence({**values,'participant_count':1},[{}])['score'],49)
        self.assertEqual(domain_alignment.confidence({**values,'participant_count':5},[{}])['score'],100)
        # Raising sample size alone cannot fix weak grounding, coverage or applicability.
        self.assertEqual(domain_alignment.confidence({**values,'grounding':0,'coverage':0,'applicability':0,'participant_count':1000},[{}])['score'],25)
    def test_conversation_may_also_signal_alignment_without_becoming_a_draft_editor(self):
        out=self.send(self.sam,self.t,purpose='explore');self.assertFalse(out['findings_updated']);self.assertEqual(len(self.rows()),2)
        self.assertIn('discussion guide',self.model.calls[-1]['instructions'])

    def test_human_refinement_informs_followup_as_attributed_judgment_not_new_evidence(self):
        self.send(self.sam,self.t,purpose='review');row=self.rows()[0];self.assess(row)
        out=self.send(self.sam,self.t,purpose='explore',request_id='followup-human-assessment')
        self.assertIn('chatReport',out);author=self.model.calls[-1]['context']['author_assessments'][0]
        self.assertIn('more interviews',author['note']);self.assertTrue(author['confirmed'])
        self.assertIn('Not project approval',author['status']);self.assertTrue(self.rows()[0]['current'])

    def test_research_uses_shared_pdf_review_and_page_citations_with_owner_scopes(self):
        t=self.attach(self.sam,self.start(),pdf=True);changed=self.sam.command('domain-chat-focus',dict(conversation=asdict(self.current(self.sam,t)['ref']),source=self.draft(self.sam,t)['body']['source_refs'][0],mode='visual'));t=self.sam.domain_chat.owned(changed['conversation']);out=self.send(self.sam,t,purpose='review',request_id='research-pdf-review')
        self.assertIn('chatReport',out);row=next(r for r in self.rows() if r['conversation']==t['ref'].id)
        self.assertEqual(row['evidence'][0]['page'],1);self.assertEqual(row['assessment'],'appears-met')
        self.assertFalse(row['confirmed']);self.assertNotIn('configured Design coach',self.model.calls[-1]['instructions'])
        from workbench import visual_pdf
        with self.assertRaises(PermissionError):visual_pdf.source(self.lee,self.draft(self.sam,t)['body']['source_refs'][0])

    def test_source_deduplication_never_returns_another_authors_private_file(self):
        source=self.sam.domain_chat.source(self.t)
        self.store.put(source['ref'].id,'source',source['scope'],{**source['body'],'owner':'lee'},source['ref'].revision)
        fresh=self.sam.command('domain-source',dict(title='My independently supplied text',text=source['body']['text']))
        self.assertNotEqual(fresh['ref']['id'],source['ref'].id)
        self.assertEqual(self.store.read(__import__('workbench.validation',fromlist=['reference']).reference(fresh['ref']),self.sam.scopes)['body']['owner'],'sam')

    def test_new_reviews_never_invoke_the_legacy_percentage_calculator(self):
        with patch('workbench.domain_alignment.confidence',side_effect=AssertionError('No new percentage scoring')):
            result=self.send(self.sam,self.t,purpose='review')
            self.assertIn('chatReport',result)
            row=self.rows()[0]
            self.assertEqual(row['confidence']['level'],'low')
            self.assertNotIn('score',row['confidence'])
            self.assertEqual(row['assessor_type'],'model')
            self.assess(row)
            self.assertEqual(self.rows()[0]['assessor_type'],'human')

    def test_unsupported_confidence_invented_dimension_passages_and_legacy_new_outputs_are_rejected(self):
        mutations=[lambda r:r['confidence'].update(level='high'),lambda r:r['confidence']['dimensions']['evidence-quality'].update(passage_ids=['MADE-UP']),lambda r:r.update(confidence=dict(grounding=3,corroboration=3,coverage=3,applicability=3,participant_count=1))]
        for i,mutate in enumerate(mutations):
            self.model.invalid=mutate
            out=self.send(self.sam,self.t,purpose='review',request_id='invalid-common-confidence-'+str(i))
            self.assertIn('chat_error',out)
        self.assertEqual(self.rows(),[])

    def test_shared_standard_change_invalidates_confirmation_without_rewriting_recorded_judgment(self):
        self.send(self.sam,self.t,purpose='review');row=self.rows()[0];self.assess(row)
        saved=deepcopy(self.rows()[0]['confidence_values'])
        changed=domain_alignment.standard_context();changed['ref']['revision']+=1;changed['body']['revision']+=1
        with patch('workbench.domain_alignment.standard_context',return_value=changed):
            current=self.rows()[0]
            self.assertFalse(current['current']);self.assertFalse(current['confirmed'])
            self.assertEqual(current['confidence_values'],saved)
            self.assertEqual(current['confidence']['level'],'low')
            with self.assertRaises(StaleBasis):self.assess(current)

    def test_legacy_saved_record_and_author_note_remain_private_historical_and_cannot_be_regraded(self):
        out=self.send(self.sam,self.t,purpose='review');report=self.store.latest(out['chatReport'],{self.sam.domains.scope});body=deepcopy(report['body'])
        legacy=dict(grounding=2,corroboration=0,coverage=1,applicability=1,participant_count=1)
        for item in body['output']['alignment']:item['confidence']=deepcopy(legacy)
        self.store.put(report['ref'].id,report['kind'],report['scope'],body,report['ref'].revision)
        row=self.rows()[0]
        self.assertEqual(row['confidence']['score'],33);self.assertTrue(row['confidence']['historical'])
        self.assertEqual(row['confidence']['framework'],'evidence-v1');self.assertNotIn('level',row['confidence'])
        self.assess(row)
        self.assertEqual(self.rows()[0]['confidence_values'],legacy)
        self.assertEqual(self.lee.domain_chat.state()['alignment'],[])
        with self.assertRaises(ValueError):self.assess(self.rows()[0],confidence={**legacy,'grounding':3})
