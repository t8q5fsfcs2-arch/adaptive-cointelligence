"""Read a prior live run; capture the next native request without a provider.

Writes only the explicitly supplied audit output. The historical database is
opened read-only and copied into memory. No semantic judgment is fabricated.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.dont_write_bytecode=True

def deny(*args,**kwargs):raise AssertionError('Offline replay prohibits all network access.')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
socket.getaddrinfo=deny

from workbench.core import Store
from workbench.workspace import Workspace
from workbench import integrity_options as options,integrity_grounding as grounding,integrity_pipeline as pipeline

class CapturedBoundary(Exception):pass
class CaptureOnly:
    def __init__(self):self.requests=[]
    def status(self):return dict(configured=True,provider='offline-capture',model='no-provider')
    def generate(self,**request):
        self.requests.append(request)
        raise CapturedBoundary('Stopped before any provider invocation.')

def replay(run,output):
    protocol=json.loads((run/'PROTOCOL.json').read_text());stage=protocol['stages'][0]
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    protected={str(p):digest(p) for p in run.rglob('*') if p.is_file()}
    store=Store(':memory:')
    try:
        with sqlite3.connect('file:'+str(run/'execution.sqlite3')+'?mode=ro',uri=True) as source:source.backup(store.db)
        model=CaptureOnly();workspace=Workspace(store,stage['actor_context'],model)
        ctx=workspace.integrity.assemble(stage['data']);frozen=ctx['condition_inventory']
        c=options.context(ctx);windows=grounding.review_batches(ctx);coverage=[]
        for window in windows:
            part=grounding.subset(ctx,window['groups'],window['part_refs']);projected=grounding.project(part,window['groups'])
            assert 0<len(window['part_refs'])<=12
            assert projected['evidence_level']==ctx['evidence_level']
            for group in window['groups']:
                for pid in window['part_refs']:
                    if c['material_parts'][pid]['clause_ref']!=group[0]:continue
                    for member in group:
                        translated=member+pid[len(group[0]):];coverage.append(translated)
                        assert c['material_parts'][translated]['meaning']==frozen['conditions'][translated]['meaning']
            assert projected['option_contract']['rule_bindings']==options.context(part)['rule_bindings']
        assert Counter(coverage)==Counter(c['material_parts'].keys())
        assert len(c['material_parts'])+len(c['context_parts'])==len(frozen['conditions'])
        counts_before=store.db.execute("SELECT COUNT(*) FROM records WHERE kind='integrity-assessment'").fetchone()[0]
        try:workspace.command(stage['command'],stage['data'])
        except CapturedBoundary:pass
        else:raise AssertionError('Expected a captured request boundary.')
        assert len(model.requests)==1
        first=model.requests[0]
        assert first['context']['assessment_phase']=='clause-mapping'
        assert first['context']['frozen_inventory']['ref']==frozen['ref']
        assert store.db.execute("SELECT COUNT(*) FROM records WHERE kind='integrity-assessment'").fetchone()[0]==counts_before
        assert protected=={str(p):digest(p) for p in run.rglob('*') if p.is_file()}
        result=dict(status='PASS_OFFLINE_NATIVE_BOUNDARY',historical_run=str(run),stage=stage['id'],
            inventory_ref=frozen['ref'],inventory_fingerprint=frozen['fingerprint'],inventory_version=frozen['version'],
            evidence_level=ctx['evidence_level'],frozen_entries=len(frozen['conditions']),
            material_conditions=len(c['material_parts']),context_headings={k:v['quote'] for k,v in c['context_parts'].items()},
            conditions_by_clause=dict(Counter(v['clause_ref'] for v in c['material_parts'].values())),
            plan=pipeline.plan(ctx),windows=windows,condition_coverage_exact=True,
            native_first_phase=first['context']['assessment_phase'],captured_requests=1,
            inventory_generation_requests=0,paid_calls=0,cost_usd=0,new_semantic_assessments=0,
            historical_files_unchanged=len(protected),
            limitation='Verifies planning, inventory reuse and the native request boundary. No new judgment, synthesis, semantic-quality result or human decision was generated.')
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');output.chmod(0o600)
        print(json.dumps({k:v for k,v in result.items() if k not in ('windows','context_headings','conditions_by_clause')},indent=2))
    finally:store.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();replay(args.run.resolve(),args.output.resolve())
