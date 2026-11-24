"""Research user flows reach FigJam only through an explicit, receipted send."""
from dataclasses import asdict
import os
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from workbench.core import StaleBasis, Store
from workbench.flow_export import MCPDiagramWriter, validate_diagram
from workbench.tool_imports import PROVIDERS
from workbench.workspace import Workspace

FLOW = 'flowchart LR\n  A[Reminder] --> B{Can attend?}\n  B -- No --> C[Call the clinic]'
SCHEMA = dict(properties=dict(name=dict(type='string'), mermaidSyntax=dict(type='string'), fileKey=dict(type='string')),
              required=['name', 'mermaidSyntax'])


def fake_writer(calls, result=None, error=None, schema=SCHEMA):
    class Writer(MCPDiagramWriter):
        def __init__(self, *args):
            self.schema = {}
        def prepare(self):
            self.schema = schema
        def write(self, arguments):
            calls.append(arguments)
            if error:
                raise error
            return result if result is not None else dict(content=[dict(type='text', text='Created https://www.figma.com/board/AbC123/Flow?node-id=0-1')])
    return Writer


class FlowExportTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'w.sqlite3')
        self.sam = Workspace(self.store, 'sam')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def configure(self, export=True):
        self.sam.command('domain-tool-settings', dict(provider='figjam', expected=None, enabled=True, export_enabled=export,
            tool='get_figjam', protocol='2025-11-25', arguments=PROVIDERS['figjam']['arguments']))

    def flow(self):
        return self.sam.command('domain-flow-save', dict(title='Current rescheduling journey', diagram=FLOW))['flow']

    def send(self, export, calls, **kw):
        self.sam.flows.writer = fake_writer(calls, **kw)
        with patch.dict(os.environ, {self.sam.tool_imports.credential('figjam'): 'test-secret'}):
            return self.sam.command('domain-flow-send', dict(export=export, confirm=True))

    def test_validation_accepts_supported_mermaid_only(self):
        self.assertEqual(validate_diagram(' Flow ', FLOW + '\n'), ('Flow', FLOW))
        for bad in ['', 'pie title X', 'flowchart LR\x00', 'x' * 20001]:
            with self.assertRaises(ValueError):
                validate_diagram('Flow', bad)

    def test_staged_flow_is_sent_once_with_receipt_and_no_secret(self):
        ref = self.flow()
        staged = self.sam.command('domain-flow-stage', dict(flow=ref, url='https://www.figma.com/board/Xyz789/Existing'))
        self.assertEqual(staged['destination'], 'https://www.figma.com/board/Xyz789')
        self.configure()
        calls = []
        result = self.send(staged['export'], calls)
        self.assertEqual(calls, [dict(name='Current rescheduling journey', mermaidSyntax=FLOW, fileKey='Xyz789')])
        self.assertTrue(result['board_url'].startswith('https://www.figma.com/board/AbC123'))
        record = self.store.latest(staged['export']['id'], self.sam.scopes)
        self.assertEqual(record['body']['status'], 'sent')
        self.assertNotIn('test-secret', str(record))
        with self.assertRaises((ValueError, StaleBasis)):
            self.send(asdict(record['ref']), calls)
        self.assertEqual(len(calls), 1)

    def test_nothing_is_sent_without_confirmation_permission_or_credential(self):
        staged = self.sam.command('domain-flow-stage', dict(flow=self.flow()))
        self.assertEqual(staged['destination'], 'a new FigJam board in your drafts')
        with self.assertRaises(ValueError):
            self.sam.command('domain-flow-send', dict(export=staged['export']))
        calls = []
        self.configure(export=False)
        with self.assertRaises(ValueError):
            self.send(staged['export'], calls)
        current = asdict(self.sam.tool_imports.connection('figjam')['ref'])
        self.sam.command('domain-tool-settings', dict(provider='figjam', expected=current, enabled=True, export_enabled=True,
            tool='get_figjam', protocol='2025-11-25', arguments=PROVIDERS['figjam']['arguments']))
        self.sam.flows.writer = fake_writer(calls)
        with self.assertRaises(ValueError):
            self.sam.command('domain-flow-send', dict(export=staged['export'], confirm=True))
        self.assertEqual(calls, [])
        self.assertEqual(self.store.latest(staged['export']['id'], self.sam.scopes)['body']['status'], 'staged')

    def test_unfillable_tool_inputs_stop_before_any_write(self):
        staged = self.sam.command('domain-flow-stage', dict(flow=self.flow()))
        self.configure()
        calls = []
        with self.assertRaises(ValueError):
            self.send(staged['export'], calls, schema=dict(properties=dict(prompt=dict(type='string')), required=['prompt']))
        self.assertEqual(calls, [])
        self.assertEqual(self.store.latest(staged['export']['id'], self.sam.scopes)['body']['status'], 'staged')

    def test_uncertain_outcome_is_retained_without_automatic_retry(self):
        staged = self.sam.command('domain-flow-stage', dict(flow=self.flow()))
        self.configure()
        calls = []
        with self.assertRaises(ValueError):
            self.send(staged['export'], calls, error=TimeoutError('unknown'))
        self.assertEqual(self.store.latest(staged['export']['id'], self.sam.scopes)['body']['status'], 'outcome-unknown')
        with self.assertRaises((ValueError, StaleBasis)):
            self.send(staged['export'], calls)
        self.assertEqual(len(calls), 1)

    def test_edited_flow_keeps_history_and_stale_stage_cannot_send(self):
        first = self.flow()
        staged = self.sam.command('domain-flow-stage', dict(flow=first))
        second = self.sam.command('domain-flow-save', dict(flow=first, title='Revised journey', diagram=FLOW + '\n  C --> D[Hold]'))['flow']
        self.assertEqual((first['id'], second['revision']), (second['id'], 2))
        self.configure()
        calls = []
        with self.assertRaises(StaleBasis):
            self.send(staged['export'], calls)
        self.assertEqual(calls, [])

    def test_flows_are_private_to_their_research_author_and_not_offered_to_design(self):
        self.flow()
        self.assertEqual(len(self.sam.flows.state()['flows']), 1)
        lee = Workspace(self.store, 'lee')
        self.assertEqual(lee.flows.state(), dict(enabled=False, flows=[]))
        with self.assertRaises(PermissionError):
            lee.command('domain-flow-save', dict(title='X', diagram=FLOW))
        with self.assertRaises(PermissionError):
            self.store.latest(self.sam.flows.state()['flows'][0]['ref'].id, lee.scopes)
