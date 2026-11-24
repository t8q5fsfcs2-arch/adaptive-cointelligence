"""Durable execution receipts. Operational success is not an expert-quality score."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from statistics import median
from threading import Lock
from time import perf_counter
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import now
from .intake import PRIVATE
from .model_provider import ModelUnavailable, OpenAIModel, AnthropicModel


# An unfinished receipt can survive a restart. Only this process can confirm
# that the corresponding execution is still in progress.
_running = set()
_running_lock = Lock()


def run_is_active(path, run_id):
    with _running_lock:
        return (str(path), run_id) in _running


def execution_mode(model):
    if not model.status().get('configured'):
        return 'not-connected'
    # A name or an editable setting cannot turn a test double into a live adapter.
    return 'live' if isinstance(model, (OpenAIModel, AnthropicModel)) else 'simulated'


class AgentRun:
    def __init__(self, store, actor, agent, skill, basis, configuration=None,
                 fingerprint=None, purpose='workflow', context=None, instructions=None, scope=PRIVATE):
        self.store = store
        self.scope = scope
        self.body = dict(persona_id=agent.persona_id, agent=agent.id, agent_version=agent.version,
            skill=skill, mode=execution_mode(agent.model), purpose=purpose, actor=actor,
            started_at=now(), status='running', basis=basis, configuration=configuration,
            configuration_fingerprint=fingerprint, provider=agent.model.status().get('provider'),
            model=agent.model.status().get('model'), model_connection=agent.model.status().get('connection'), duration_ms=None, usage=None, cost=None,
            context=deepcopy(context), instructions=instructions, output_ref=None, error=None)
        self.ref = store.put('RUN-'+uuid4().hex[:12], 'agent-execution', self.scope, self.body)
        self.started = perf_counter()
        self.result = None

    def __enter__(self):
        path = self.store.db.execute("PRAGMA database_list").fetchone()["file"]
        self.active_key = (path, self.ref.id)
        with _running_lock:
            _running.add(self.active_key)
        return self

    def complete(self, result, output_ref):
        self.result = result
        self.body.update(output_ref=asdict(output_ref), output=result.get('output'))

    def __exit__(self, kind, error, traceback):
        self.body.update(finished_at=now(), duration_ms=round((perf_counter()-self.started)*1000),
            status='stale' if isinstance(error, StaleBasis) else 'failed' if error else 'succeeded')
        if self.result:
            self.body.update(model=self.result.get('model', self.body['model']), usage=self.result.get('usage'), output=self.result.get('output'))
        if error:
            # Do not persist arbitrary exception text, provider bodies, or credentials.
            self.body['error'] = ('Inputs changed before the result could be used.' if isinstance(error, StaleBasis)
                else 'The model request or output validation failed. No substitute response was used.' if isinstance(error, ModelUnavailable)
                else 'Execution did not finish successfully. Review the request and retry explicitly.')
        try:
            self.ref = self.store.put(self.ref.id, 'agent-execution', self.scope, self.body, self.ref.revision)
        finally:
            with _running_lock:
                _running.discard(self.active_key)
        return False


def monitoring(store, actor, admin=False):
    if actor != 'priya' and not admin:
        return None
    cutoff = datetime.now(timezone.utc)-timedelta(days=30)
    # Admin telemetry exposes operational metadata only, never private domain input/output.
    monitoring_scopes = {PRIVATE, 'domain:research', 'domain:design'} | {'coach:'+a for a in ('priya','sam','lee','maya','alex')}
    from .domain import configured_domains
    monitoring_scopes.update(d['scope'] for d in configured_domains(store).values())
    if not admin:monitoring_scopes={PRIVATE,'coach:'+actor}
    rows = store.db.execute("SELECT id,MAX(revision) revision FROM records WHERE kind='agent-execution' AND scope IN ("+",".join("?" for _ in monitoring_scopes)+") GROUP BY id ORDER BY MIN(rowid) DESC", tuple(monitoring_scopes)).fetchall()
    runs = []
    for row in rows:
        record = store.read(Ref(row['id'], row['revision']), monitoring_scopes)
        b = record['body']
        start = datetime.fromisoformat(b['started_at'].replace('Z', '+00:00'))
        if start < cutoff:
            continue
        visible = {k:v for k,v in b.items() if k not in {'context','instructions','output'}}
        if b['status']=='running' and start < datetime.now(timezone.utc)-timedelta(minutes=5):
            visible['status']='unknown'
            visible['error']='No completion receipt. The request may have been interrupted; its outcome is unknown.'
        visible['ref'] = asdict(record['ref'])
        visible['applied'] = False
        if b.get('output_ref'):
            output = store.latest(b['output_ref']['id'], monitoring_scopes)
            visible['applied'] = bool(output['body'].get('applied'))
        runs.append(visible)
    summaries = []
    for persona in sorted({r['persona_id'] for r in runs}):
        for mode in ('live','simulated','not-connected'):
            for purpose in ('workflow','configuration-test','evaluation','evaluation-assessment'):
                selected = [r for r in runs if (r['persona_id'],r['mode'],r['purpose'])==(persona,mode,purpose)]
                if not selected:
                    continue
                finished = [r for r in selected if r['status'] in ('succeeded','failed','stale')]
                durations = [r['duration_ms'] for r in finished if r['duration_ms'] is not None]
                tokens = []
                for r in selected:
                    u = r.get('usage') or {}
                    n = u.get('total_tokens')
                    if n is None and isinstance(u.get('input_tokens'), int) and isinstance(u.get('output_tokens'), int):
                        n = u['input_tokens']+u['output_tokens']
                    if isinstance(n,int) and n>=0:
                        tokens.append(n)
                summaries.append(dict(persona_id=persona, mode=mode, purpose=purpose, total=len(selected),
                    completed=sum(r['status']=='succeeded' for r in selected),
                    failed=sum(r['status']=='failed' for r in selected), stale=sum(r['status']=='stale' for r in selected),
                    running=sum(r['status']=='running' for r in selected), unknown=sum(r['status']=='unknown' for r in selected),
                    completion_rate=round(100*sum(r['status']=='succeeded' for r in finished)/len(finished),1) if finished else None,
                    median_ms=median(durations) if durations else None, tokens=sum(tokens) if tokens else None,
                    usage_coverage=len(tokens), applied=sum(r['applied'] for r in selected), cost=None, quality='not-evaluated'))
    legacy = store.db.execute("SELECT COUNT(DISTINCT id) FROM records WHERE kind='intake-coach-run' AND id NOT IN (SELECT json_extract(body,'$.output_ref.id') FROM records WHERE kind='agent-execution' AND json_extract(body,'$.output_ref.id') IS NOT NULL)").fetchone()[0]
    return dict(window_days=30, summaries=summaries, runs=runs[:100], total=len(runs), legacy_count=legacy)
