"""Compare real model behavior on a frozen intake, without activating edits."""
from copy import deepcopy
from dataclasses import asdict
import json
from uuid import uuid4

from .agent_runs import AgentRun
from .agent_catalog import CATALOG_VERSION, CATALOG_FINGERPRINT
from .decisions import now
from .core import StaleBasis
from .intake import PRIVATE
from .intake_expertise import PROFILES, expert_context
from .model_provider import ModelUnavailable
from .expertise_methods import grounding


def compare(coaching, data):
    coaching.intake.settings_editor()
    if data.get('consent') is not True:
        raise ValueError('Confirm sending this intake and selected material for two model responses')
    current = coaching.settings.coaching()
    proposed = coaching.settings.proposed_coaching(data, current)
    if current['fingerprint'] == proposed['fingerprint']:
        raise ValueError('Change the AI partner instructions before comparing responses')
    if not coaching.agent.model.status()['configured']:
        raise ModelUnavailable('Connect a model before testing. No substitute response was generated.')
    skill = data['key'] if data['area'] == 'skill' else 'coach-field'
    field = data['key'] if data['area'] == 'question' else data.get('field', 'business_challenge')
    if field not in PROFILES:
        raise ValueError('Choose a question for this test')
    request = dict(expected=data.get('draft_expected'), consent=True, skill=skill, field=field,
                   sources=data.get('sources', []), message='Evaluate this intake using the assigned skill. Offer the most useful improvement while preserving uncertainty.')
    prepared = coaching.prepare(request, include_history=False, settings_test=True,
                                test_answer=data.get('test_answer') if skill == 'coach-field' else None)
    if prepared['configuration']['fingerprint'] != current['fingerprint']:
        raise StaleBasis('AI partner settings changed. Reopen Settings before testing.')
    baseline = prepared['context']
    candidate = deepcopy(baseline)
    cfg = proposed['config']
    candidate.update(expert_context(field, candidate['values'], skill, cfg['questions']))
    candidate['method_grounding']=grounding('P02',skill,field,cfg['methods'])
    candidate['field_guidance'] = {k:p['hint'] for k,p in cfg['questions'].items()}
    candidate['coach_configuration'] = dict(ref=None, fingerprint=proposed['fingerprint'],
        persona=cfg['persona'], skill_instructions=cfg['skills'][skill])
    if len(json.dumps(candidate)) > 170_000:
        raise ValueError('This test is too large. Use shorter configuration or source excerpts.')
    from .intake_coach import task_instructions
    # Persist the frozen inputs before inference; interrupted and failed tests remain visible.
    body = dict(status='running', author=coaching.intake.actor, at=now(), agent=coaching.agent.id,
        agent_version=coaching.agent.version, persona_id=coaching.agent.persona_id,
        catalog_version=CATALOG_VERSION, catalog_fingerprint=CATALOG_FINGERPRINT,
        basis=asdict(prepared['draft']['ref']), profile=asdict(coaching.intake.profile()['ref']),
        configuration=current['ref'], current_fingerprint=current['fingerprint'],
        proposed_fingerprint=proposed['fingerprint'], current_config=current['config'],
        proposed_config=cfg, area=data['area'], key=data.get('key',''), field=field, skill=skill,
        provider=coaching.agent.model.status()['provider'], model=coaching.agent.model.status()['model'],
        results={})
    test_id = 'COACH-TEST-'+uuid4().hex[:10]
    for label, context in [('current',baseline),('proposed',candidate)]:
        body['results'][label] = dict(status='pending', context=context, instructions=task_instructions(context))
    ref = coaching.store.put(test_id, 'coach-config-test', PRIVATE, body)
    for label, context in [('current',baseline),('proposed',candidate)]:
        entry = body['results'][label]
        try:
            with AgentRun(coaching.store, coaching.intake.actor, coaching.agent, skill, body['basis'],
                          current['ref'] if label=='current' else None,
                          current['fingerprint'] if label=='current' else proposed['fingerprint'],
                          purpose='configuration-test', context=context, instructions=task_instructions(context)) as execution:
                result = coaching.agent.run(context)
                execution.result = result
                entry.update(status='completed', output=result['output'], model=result.get('model'), usage=result.get('usage',{}))
                execution.complete(result, ref)
        except ModelUnavailable as error:
            entry.update(status='failed', error=str(error))
        ref = coaching.store.put(test_id, 'coach-config-test', PRIVATE, body, ref.revision)
    complete = all(r['status']=='completed' for r in body['results'].values())
    body['status'] = 'completed' if complete else 'partial' if any(r['status']=='completed' for r in body['results'].values()) else 'failed'
    body['finished_at'] = now()
    ref = coaching.store.put(test_id, 'coach-config-test', PRIVATE, body, ref.revision)
    # UI needs results, not the full saved prompt/configuration snapshots.
    results = {k:{n:v for n,v in r.items() if n not in ('context','instructions')} for k,r in body['results'].items()}
    return dict(ref=asdict(ref), status=body['status'], results=results,
        configuration=current['ref'], basis=body['basis'], model=body['model'],
        current=coaching.settings.coaching()['fingerprint']==current['fingerprint'] and
                asdict(coaching.intake.draft()['ref'])==body['basis'],
        message='Comparison saved. Your settings and intake answers have not changed.')
