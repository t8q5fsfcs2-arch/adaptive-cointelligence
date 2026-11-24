"""Request budgets and exact evidence catalog; no live calls in unit tests."""
import io,json,unittest
from unittest.mock import patch
from workbench.integrity_example import Fixture
from workbench.integrity import schema,citation_catalog
from workbench.model_provider import OpenAIModel,request_timeout
from workbench.integrity_options_example import synthetic_output
from workbench.core import Ref
from workbench.decisions import SCOPE

class IntegrityModelPolicyTests(unittest.TestCase):
    def test_only_integrity_task_on_supported_gpt5_receives_explicit_controls(self):
        for name in ('gpt-5-mini','gpt-5-mini-2025-08-07','gpt-5','gpt-5-nano'):
            m=OpenAIModel('test-key',name);calls=[]
            def transport(request,timeout):
                calls.append((json.loads(request.data),timeout))
                return io.BytesIO(json.dumps(dict(id='resp-test',status='completed',model='gpt-5-mini-2025-08-07',output=[dict(type='message',content=[dict(type='output_text',text='{"ok":true}')])],usage={})).encode())
            with patch('workbench.model_provider.urlopen',transport):out=m.generate(instructions='test',context=dict(skill='integrity-review'),schema=dict(type='object'))
            payload,deadline=calls[0]
            self.assertEqual(payload['reasoning'],dict(effort='low'));self.assertEqual(payload['text']['verbosity'],'low')
            self.assertEqual(payload['max_output_tokens'],6000);self.assertEqual(deadline,120)
            self.assertEqual(out['response_id'],'resp-test');self.assertEqual(out['request_settings']['reasoning_effort'],'low')
            self.assertNotIn('test-key',json.dumps(out))
        self.assertNotIn('reasoning_effort',OpenAIModel('test','gpt-4.1').request_settings(dict(skill='integrity-review')))
        self.assertNotIn('reasoning_effort',OpenAIModel('test','gpt-5-mini').request_settings(dict(skill='coach-field')))
        self.assertEqual(request_timeout(dict(skill='coach-field')),55)
        self.assertEqual(request_timeout(dict(skill='assess-change')),180)

    def test_catalog_is_schema_enum_and_expands_to_exact_source_snapshot(self):
        f=Fixture();self.addCleanup(f.store.close)
        ctx=f.w('sam').integrity.assemble(dict(packets=[f.a['packet']],evaluation_scope='within-domain',mode='formal'))
        catalog=citation_catalog(ctx);key=next(k for k,v in catalog.items() if v['id']==f.anchor.id and v['field']=='text')
        enum=schema(ctx)['properties']['findings']['items']['properties']['citations']['items']['enum']
        self.assertIn(key,enum)
        out=dict(summary='Execution timing needs clarification.',workability='unknown',unresolved=[],findings=[dict(title='Timing gap',classifications=['weakening'],effect='Assignment alone does not establish execution qualification.',citations=[key],support='supported',action='Establish execution enforcement.',material=True)])
        saved=f.store.read(f.anchor,{SCOPE});f.store.put(f.anchor.id,'requirement',SCOPE,{**saved['body'],'text':'A later version is different.'},1)
        findings=f.w('sam').integrity.validate_model(out,ctx)
        self.assertEqual(findings[0]['citations'],[catalog[key]])
        self.assertEqual(findings[0]['citations'][0]['revision'],1)
        self.assertIn('at work execution',findings[0]['citations'][0]['quote'])
        out['findings'][0]['citations']=['C-invented']
        with self.assertRaises(ValueError):f.w('sam').integrity.validate_model(out,ctx)

    def test_effective_request_settings_change_invalidates_semantic_cache_key(self):
        f=Fixture();self.addCleanup(f.store.close)
        class Model:
            cap=6000
            def status(self):return dict(configured=True,model='fixture',provider='test')
            def request_settings(self,ctx):return dict(max_output_tokens=self.cap,reasoning_effort='low')
            def generate(self,**kw):return dict(model='fixture-snapshot',response_id='resp-test',request_settings=self.request_settings(kw['context']),output=synthetic_output(kw['context']))
        model=Model();w=f.w('sam',model)
        data=dict(packets=[f.a['packet']],evaluation_scope='within-domain',mode='formal',confirm=True,semantic=True,consent=True)
        a=w.integrity.assess(data);cached=w.integrity.assess(data);model.cap=5000;b=w.integrity.assess(data)
        self.assertTrue(cached['cached']);self.assertNotEqual(a['ref'],b['ref'])
        body=f.store.read(Ref(**b['ref']),{SCOPE})['body']
        self.assertEqual(body['model']['resolved_model'],'fixture-snapshot');self.assertEqual(body['model']['settings']['max_output_tokens'],5000)

    def test_current_anchor_and_history_are_separate_in_model_projection(self):
        from workbench.integrity import model_context
        f=Fixture();self.addCleanup(f.store.close)
        f.change_anchor('Only qualified personnel may perform the assigned task.');f.declare([])
        e=f.expression('sam','research','Scheduling','Validate qualification when assigning the task.',['assignment'],previous=f.a['ref'],source=Ref('SOURCE-sam',1))
        ctx=f.w('sam').integrity.assemble(dict(packets=[e['packet']],evaluation_scope='within-domain',mode='formal'))
        projected=model_context(ctx)
        self.assertEqual(projected['current_governing_requirements'][0]['ref'],{'id':f.anchor.id,'revision':2})
        self.assertEqual(projected['current_governing_requirements'][0]['body']['text'],'Only qualified personnel may perform the assigned task.')
        self.assertTrue(projected['historical_context']['decisions'])
        self.assertEqual(projected['owner_declared_conditions'][0]['body']['conditions'],[])
        self.assertIn('cannot override',projected['historical_context']['boundary'])

    def test_execution_receipt_retains_the_actual_projected_request(self):
        from workbench.decisions import fingerprint
        f=Fixture();self.addCleanup(f.store.close)
        class Model:
            def status(self):return dict(configured=True,model='fixture',provider='test')
            def generate(self,**kw):
                self.sent=kw['context'];return dict(model='fixture-snapshot',output=synthetic_output(kw['context']))
        m=Model();w=f.w('sam',m)
        result=w.integrity.assess(dict(packets=[f.a['packet']],evaluation_scope='within-domain',mode='formal',confirm=True,semantic=True,consent=True))
        a=f.store.read(Ref(**result['ref']),{SCOPE})
        run=next(r for r in w.integrity.records('agent-execution') if r['body']['skill']=='integrity-review')
        self.assertEqual(run['body']['context'],m.sent)
        self.assertEqual(a['body']['model_context_fingerprint'],fingerprint(m.sent))
        self.assertEqual(run['body']['mode'],'simulated')
        self.assertIn('current_governing_requirements',m.sent)
