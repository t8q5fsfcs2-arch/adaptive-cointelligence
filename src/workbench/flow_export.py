"""User-flow schematics a domain author pushes to FigJam explicitly.

A versioned private flow (Mermaid text) is staged as an exact copy with an optional
destination board, then sent only after explicit confirmation through the author's
own FigJam connection, which must allow creation. The attempt is recorded before
the external effect and an uncertain outcome is never retried automatically. The
flow returns through the existing FigJam import. See docs/decisions/D002.
"""
from dataclasses import asdict
import json
import os
import re
from uuid import uuid4

from .core import StaleBasis
from .decisions import fingerprint, now
from .tool_imports import MCPReader, PROVIDERS, locator
from .validation import reference

DIAGRAM_TYPES = ('flowchart', 'graph', 'sequenceDiagram', 'stateDiagram-v2', 'stateDiagram')
BOARD_URL = re.compile(r'https://(?:www\.)?figma\.com/board/[A-Za-z0-9]+[^\s"\'<>)]*')


def validate_diagram(title, diagram):
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise ValueError('Name the user flow in 160 characters or fewer')
    if not isinstance(diagram, str) or not diagram.strip() or len(diagram) > 20000:
        raise ValueError('Describe the flow in Mermaid syntax, up to 20,000 characters')
    if any(ord(c) < 32 and c not in '\n\t' for c in diagram):
        raise ValueError('Remove control characters from the flow')
    first = diagram.strip().split(None, 1)[0]
    if first not in DIAGRAM_TYPES:
        raise ValueError('Start the flow with flowchart, sequenceDiagram or stateDiagram')
    return title.strip(), diagram.strip()


class MCPDiagramWriter(MCPReader):
    tool = 'generate_diagram'

    def prepare(self):
        self.start()
        tools = self.rpc('tools/list').get('tools', [])
        match = next((t for t in tools if t.get('name') == self.tool), None)
        if not match:
            raise ValueError('This authorized MCP server does not provide FigJam diagram creation. The flow is still staged; nothing was sent.')
        self.schema = match.get('inputSchema') or {}

    def arguments(self, title, diagram, file_key):
        props = self.schema.get('properties', {})
        args = {}
        for name in props:
            low = name.lower()
            if 'mermaid' in low or low in ('diagram', 'syntax', 'code'):
                args[name] = diagram
            elif low in ('name', 'title', 'diagramname', 'filename'):
                args[name] = title
            elif low == 'filekey' and file_key:
                args[name] = file_key
        missing = [k for k in self.schema.get('required', []) if k not in args]
        if missing or not any(v == diagram for v in args.values()):
            raise ValueError('The FigJam diagram tool needs inputs the Workbench cannot supply ('+', '.join(missing or ['diagram'])+'). Nothing was sent.')
        return args

    def write(self, arguments):
        result = self.rpc('tools/call', dict(name=self.tool, arguments=arguments))
        if result.get('isError'):
            raise RuntimeError('FigJam did not confirm creation. Inspect the destination before trying again.')
        return result


class FlowExport:
    writer = MCPDiagramWriter

    def __init__(self, w):
        self.w = w
        self.store = w.store

    def enabled(self):
        return bool(self.w.domains.key and self.w.domains.profile()['config'].get('flow_export'))

    def require(self):
        self.w.domains.author()
        if not self.enabled():
            raise PermissionError('User-flow export is not configured for this domain')

    def owned(self, raw, kind):
        r = self.store.latest(reference(raw).id, {self.w.domains.scope})
        if not r or r['kind'] != kind or r['body']['owner'] != self.w.actor:
            raise PermissionError('Choose a user flow from your own workbench')
        if asdict(r['ref']) != raw:
            raise StaleBasis('This user flow changed. Reopen its current version.')
        return r

    def save(self, data):
        self.require()
        title, diagram = validate_diagram(data.get('title'), data.get('diagram'))
        previous = self.owned(data['flow'], 'domain-user-flow') if data.get('flow') else None
        body = dict(owner=self.w.actor, principal=self.w.principal_id, title=title, diagram=diagram,
                    digest=fingerprint(diagram), at=now(), previous=asdict(previous['ref']) if previous else None)
        ref = self.store.put(previous['ref'].id if previous else 'FLOW-'+uuid4().hex[:12], 'domain-user-flow',
                             self.w.domains.scope, body, previous['ref'].revision if previous else 0)
        return dict(flow=asdict(ref), message='User flow saved privately. Earlier versions remain available.')

    def stage(self, data):
        self.require()
        flow = self.owned(data.get('flow'), 'domain-user-flow')
        url = (data.get('url') or '').strip()
        file_key = locator('figjam', url)['file_key'] if url else ''
        body = dict(owner=self.w.actor, principal=self.w.principal_id, flow=asdict(flow['ref']), title=flow['body']['title'],
                    diagram=flow['body']['diagram'], digest=flow['body']['digest'], file_key=file_key,
                    url='https://www.figma.com/board/'+file_key if file_key else '', status='staged',
                    marker='WB-'+uuid4().hex[:16], at=now())
        ref = self.store.put('FLOWEXPORT-'+uuid4().hex[:12], 'domain-flow-export', self.w.domains.scope, body)
        self.store.depend(ref, flow['ref'], self.w.scopes)
        destination = body['url'] or 'a new FigJam board in your drafts'
        return dict(export=asdict(ref), title=body['title'], destination=destination,
                    message='Exact user flow staged; nothing has been sent to FigJam.')

    def send(self, data):
        self.require()
        if data.get('confirm') is not True:
            raise ValueError('Confirm the exact flow and destination before creating it in FigJam')
        r = self.owned(data.get('export'), 'domain-flow-export')
        if r['body']['status'] != 'staged':
            raise ValueError('This flow was already attempted. Inspect its receipt before staging another.')
        flow = self.store.latest(r['body']['flow']['id'], {self.w.domains.scope})
        if asdict(flow['ref']) != r['body']['flow']:
            raise StaleBasis('The user flow changed after staging. Stage its current version.')
        conn = self.w.tool_imports.connection('figjam')
        token = os.environ.get(self.w.tool_imports.credential('figjam'))
        if not conn or not conn['body'].get('export_enabled') or not token:
            raise ValueError('Allow user-flow creation and authorize FigJam in Settings → Integrations. Nothing was sent.')
        writer = self.writer(PROVIDERS['figjam']['endpoint'], token, conn['body']['protocol'])
        writer.prepare()
        arguments = writer.arguments(r['body']['title'], r['body']['diagram'], r['body']['file_key'])
        if self.w.tool_imports.connection('figjam')['ref'] != conn['ref']:
            raise StaleBasis('The FigJam connection changed. Stage the flow again.')
        # Persist the attempt before the external effect; never retry an uncertain outcome.
        ref = self.store.put(r['ref'].id, r['kind'], r['scope'], {**r['body'], 'status': 'sending', 'attempted_at': now()}, r['ref'].revision)
        attempt = self.store.read(ref, self.w.scopes)
        try:
            raw = writer.write(arguments)
            text = json.dumps(raw)
            if token in text:
                raise RuntimeError('Credential material returned; no receipt retained')
            found = BOARD_URL.search(text)
            board = found.group(0) if found else r['body']['url']
            if not board:
                raise ValueError('FigJam did not return the board location')
            with self.store.transaction():
                self.store.put(r['ref'].id, r['kind'], r['scope'], {**attempt['body'], 'status': 'sent', 'board_url': board,
                               'confirmed_at': now(), 'receipt_digest': fingerprint(raw)}, attempt['ref'].revision)
        except Exception:
            latest = self.store.latest(r['ref'].id, {r['scope']})
            self.store.put(r['ref'].id, r['kind'], r['scope'], {**latest['body'], 'status': 'outcome-unknown',
                           'note': 'Creation was not confirmed. Inspect FigJam before making another attempt.'}, latest['ref'].revision)
            raise ValueError('FigJam creation was not confirmed. Inspect your drafts or the board; this attempt will not be retried automatically.') from None
        return dict(id=r['ref'].id, board_url=board,
                    message='FigJam confirmed the user flow. Refine it there, then import it back to use it as evidence.')

    def state(self):
        if not self.enabled():
            return dict(enabled=False, flows=[])
        scope = self.w.domains.scope
        exports = [e for e in self.w.latest_records('domain-flow-export') if e['scope'] == scope and e['body']['owner'] == self.w.actor]
        flows = []
        for f in self.w.latest_records('domain-user-flow'):
            if f['scope'] != scope or f['body']['owner'] != self.w.actor:
                continue
            flows.append({**f, 'exports': [e for e in exports if e['body']['flow']['id'] == f['ref'].id]})
        return dict(enabled=True, flows=flows)
