"""Versioned method grounding. Source metadata is not an expertise certification."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .core import StaleBasis
from .decisions import now
from .intake import PRIVATE
from .validation import required

LIBRARY = json.loads((Path(__file__).parent/'config/expertise_methods.json').read_text())
VERSION = LIBRARY['version']
METHODS = {m['id']:m for m in LIBRARY['methods']}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def configured_methods(intake, persona):
    if persona not in ('P02','P04'): raise ValueError('Choose an implemented agent')
    saved=intake.latest('SETTINGS-METHODS-'+persona)
    methods={k:deepcopy(v) for k,v in METHODS.items() if persona in v['personas']}
    for key,patch in (saved['body']['overrides'] if saved else {}).items():
        if key in methods:
            methods[key]['project_guidance']=patch['guidance']
            methods[key]['project_example']=patch['example']
    body=dict(library_version=VERSION,methods=methods,ref=asdict(saved['ref']) if saved else None)
    body['fingerprint']=digest(body)
    return body


def grounding(persona,skill,field=None,configuration=None):
    config=configuration or dict(library_version=VERSION,methods={k:v for k,v in METHODS.items() if persona in v['personas']})
    if persona=='P04': ids=['requirement','measurement','evidence']
    elif skill in ('compose-value','review-value'): ids=['value-fit','evidence']
    elif skill=='coach-field': ids=[k for k,v in METHODS.items() if field in v['fields'] and persona in v['personas']]
    elif skill=='context-questions': ids=['journey','evidence']
    else: ids=list(config['methods'])
    # P04 receives measurement guidance as a dependency, not an editable P02 configuration.
    chosen=[deepcopy(config['methods'].get(k,METHODS[k])) for k in dict.fromkeys(ids)]
    return dict(library_version=VERSION,methods=chosen,fingerprint=digest(chosen))


def method_instructions(value):
    return '\nApplicable methods and fictional worked examples:\n'+json.dumps(value)+'\nApply only what helps this task. Examples teach reasoning; never copy their facts into the user’s answers. Source links identify the method, not evidence about this project. Project refinements cannot override output, evidence or authority rules.\n'


class ExpertiseMethods:
    def __init__(self,intake): self.intake,self.store=intake,intake.store
    def state(self):
        if self.intake.actor!='priya' and not getattr(self.intake,'settings_access',False):return None
        return {p:configured_methods(self.intake,p) for p in ('P02','P04')}
    def save(self,data):
        self.intake.settings_editor()
        persona=data.get('persona_id');key=data.get('method_id')
        with self.store.transaction():
            cfg=configured_methods(self.intake,persona)
            if data.get('expected')!=cfg['ref']:raise StaleBasis('Methods changed. Reopen this method before saving.')
            if key not in cfg['methods']:raise ValueError('Choose a method for this agent')
            guidance=required(data,'guidance');example=required(data,'example')
            if len(guidance)>3000 or len(example)>2000:raise ValueError('Keep guidance under 3,000 and the example under 2,000 characters')
            saved=self.intake.latest('SETTINGS-METHODS-'+persona)
            overrides=deepcopy(saved['body']['overrides'] if saved else {})
            overrides[key]=dict(guidance=guidance,example=example)
            ref=self.store.put('SETTINGS-METHODS-'+persona,'agent-method-settings',PRIVATE,
                dict(overrides=overrides,library_version=VERSION,previous=cfg['ref'],author=self.intake.actor,at=now()),cfg['ref']['revision'] if cfg['ref'] else 0)
        return dict(ref=asdict(ref),message='Method refinement saved. The next agent request uses it; earlier evaluations remain tied to their original configuration.')
