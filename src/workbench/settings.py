"""Project-scoped, versioned AI partner configuration and connection definitions.

Configuration is trusted only after an authorized human saves it. It cannot grant
agent tools, workflow authority, or access to additional records.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import re
from urllib.parse import urlsplit
from uuid import uuid4

from .agent_catalog import catalog, PERSONA_IDS
from .core import StaleBasis, Ref
from .decisions import now
from .intake import PRIVATE
from .intake_expertise import PROFILES, VERSION
from .expertise_methods import configured_methods
from .validation import required, optional

SKILLS = {
    'assess-business': {'label': 'Assess the Business Intent argument', 'trigger': 'Review Business Intent against the evidence and reasoning standard',
        'instructions': 'Freeze material claims before grading them against the versioned common evidence and reasoning standard. Keep argument completeness, scoped evidence confidence and authority distinct; preserve counterevidence and source independence limits.'},
    'assess-change': {'label': 'Assess document impact', 'trigger': 'New document after a proposition exists',
        'instructions': 'Compare new source claims with the saved proposition and earlier documents. Explain supported, challenged and unresolved claims; propose edits with exact evidence and identify possible downstream impacts. Preserve human decisions.'},
    'coach-field': {'label': 'Ask your AI partner about a response', 'trigger': 'Ask your AI partner',
        'instructions': 'Evaluate the selected answer against its expert profile and the initiative context. Offer one useful improvement, or explain why it is adequate.'},
    'compose-value': {'label': 'Draft the value proposition', 'trigger': 'Refresh from answers',
        'instructions': 'Connect the supplied answers into one coherent, editable proposition. Preserve uncertainty, existing wording and unanswered questions.'},
    'review-value': {'label': 'Review the value proposition', 'trigger': 'Review the proposition',
        'instructions': 'Assess the logic connecting beneficiaries, jobs, pains, gains and proposed fit. Prioritize the most consequential gap.'},
    'seed-value': {'label': 'Draft from source material', 'trigger': 'Upload document',
        'instructions': 'Use only the selected sources to prepare starting answers. Distinguish documented observations from hypotheses and leave thin fields open.'},
    'context-questions': {'label': 'Shape context questions', 'trigger': 'Shape context questions',
        'instructions': 'Use the working value proposition and available intake answers to prioritize context questions. Connect each question to the answers that make it relevant.'},
}
PERSONA = {'name': 'Business Intent AI partner',
    'remit': 'Help the sponsor articulate a coherent business case, connecting needs, proposed value, evidence and assumptions.',
    'style': 'Plain language, empathetic and direct. Lead with one useful observation. Keep advice concise and avoid unnecessary work.'}
GUARDRAILS = 'The AI partner proposes wording; people choose what to use. It cannot approve, publish, change permissions or call external tools. Evidence and uncertainty remain explicit.'


def defaults():
    return {'persona': deepcopy(PERSONA), 'skills': {k: v['instructions'] for k, v in SKILLS.items()},
            'questions': deepcopy(PROFILES), 'defaults_version': VERSION}


def text(data, key, limit=4000):
    value = required(data, key)
    if len(value) > limit:
        raise ValueError(f'{key.replace("_", " ").capitalize()} must be under {limit} characters')
    return value


def lines(data, key, maximum=12):
    values = data.get(key)
    if not isinstance(values, list) or not 1 <= len(values) <= maximum:
        raise ValueError(f'Provide one to {maximum} entries for {key.replace("_", " ")}')
    return [text({'item': item}, 'item', 1000) for item in values]


class ProjectSettings:
    def __init__(self, intake, model=None):
        self.intake, self.store = intake, intake.store
        self.model = model

    def coaching(self):
        record = self.intake.latest('SETTINGS-COACH')
        config = defaults()
        if record:
            saved = record['body']['config']
            config['persona'].update(saved['persona'])
            config['skills'].update(saved['skills'])
            config['questions'].update(saved['questions'])
        config['methods'] = configured_methods(self.intake,'P02')
        fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        return {'ref': asdict(record['ref']) if record else None, 'config': config,
                'fingerprint': fingerprint, 'saved_at': record['body']['at'] if record else None}

    def state(self):
        if self.intake.actor != 'priya' and not getattr(self.intake, 'settings_access', False):
            return None
        return {**self.coaching(), 'defaults': defaults(), 'skills': SKILLS, 'guardrails': GUARDRAILS,
                'integrations': self.connections(), 'agent_registry': self.agent_registry(),
                'intake_ref': asdict(draft['ref']) if (draft := self.intake.latest('INTAKE-001')) else None}

    def proposed_coaching(self, data, current=None):
        """Validate unsaved configuration using the same rules as activation."""
        current = current or self.coaching()
        if data.get('expected') != current['ref']:
            raise StaleBasis('AI partner settings changed. Reopen Settings before testing or saving.')
        config = deepcopy(current['config']); area = data.get('area'); patch = data.get('config')
        if not isinstance(patch, dict):
            raise ValueError('Provide a configuration')
        if area == 'persona':
            config['persona'] = {key: text(patch, key, 200 if key == 'name' else 4000) for key in PERSONA}
        elif area == 'skill' and isinstance(data.get('key'), str) and data['key'] in SKILLS:
            config['skills'][data['key']] = text(patch, 'instructions')
        elif area == 'question' and isinstance(data.get('key'), str) and data['key'] in PROFILES:
            key = data['key']; p = config['questions'][key]
            for name in ('expert_role', 'answer_goal', 'hint', 'starter'):
                p[name] = text(patch, name, 200 if name == 'expert_role' else 4000)
            for name in ('quality_checks', 'answer_shape'):
                p[name] = lines(patch, name)
            connected = patch.get('connections')
            if not isinstance(connected, list) or len(connected) > len(PROFILES) or any(not isinstance(k, str) or k not in PROFILES or k == key for k in connected) or len(set(connected)) != len(connected):
                raise ValueError('Choose distinct, valid related answers')
            p['connections'] = connected
        else:
            raise ValueError('Choose a supported setting')
        return {'ref': current['ref'], 'config': config, 'fingerprint': hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}

    def save_coaching(self, data):
        self.intake.settings_editor()
        with self.store.transaction():
            current = self.coaching()
            if data.get('expected') != current['ref']:
                raise StaleBasis('AI partner settings changed. Reopen Settings before saving.')
            proposed = self.proposed_coaching(data, current)
            config = proposed['config']; area = data.get('area')
            if data.get('comparison'):
                test = self.store.read(Ref(**data['comparison']), {PRIVATE})
                b = test['body']
                if test['kind'] != 'coach-config-test' or b.get('status') != 'completed':
                    raise ValueError('Choose a completed configuration test')
                if b['current_fingerprint'] != current['fingerprint'] or b['proposed_fingerprint'] != proposed['fingerprint']:
                    raise StaleBasis('These settings differ from the tested configuration. Test the changes again.')
                self.intake.draft(b['basis'])
            reason = optional(data, 'reason') or f'Updated {area}: {data.get("key") or config["persona"]["name"]}'
            result = self.store.put('SETTINGS-COACH', 'coach-settings', PRIVATE,
                {'config': config, 'previous': current['ref'], 'reason': reason,
                 'author': self.intake.actor, 'at': now(), 'comparison': data.get('comparison')}, current['ref']['revision'] if current['ref'] else 0)
        return {'message': 'AI partner settings saved for this project. They apply to your next AI partner request.', 'ref': asdict(result)}

    def agent_registry(self):
        record = self.intake.latest('SETTINGS-AGENTS')
        overrides = record['body']['descriptors'] if record else {}
        result = catalog(self.model)
        result['ref'] = asdict(record['ref']) if record else None
        for profile in result['profiles']:
            profile['descriptor'] = overrides.get(profile['id'], profile['descriptor'])
        result['history'] = []
        for row in self.store.db.execute("SELECT revision FROM records WHERE id='SETTINGS-AGENTS' ORDER BY revision DESC LIMIT 20"):
            previous = self.store.read(Ref('SETTINGS-AGENTS', row['revision']), {PRIVATE})
            b = previous['body']
            result['history'].append({'revision': row['revision'], 'persona_id': b['persona_id'],
                'descriptor': b['descriptors'][b['persona_id']], 'author': b['author'],
                'at': b['at'], 'reason': b['reason']})
        return result

    def save_agent_descriptor(self, data):
        self.intake.settings_editor()
        key = data.get('persona_id')
        if not isinstance(key, str) or key not in PERSONA_IDS:
            raise ValueError('Choose a persona from the agent inventory')
        descriptor = text(data, 'descriptor', 600)
        with self.store.transaction():
            previous = self.intake.latest('SETTINGS-AGENTS')
            expected = asdict(previous['ref']) if previous else None
            if data.get('expected') != expected:
                raise StaleBasis('Agent descriptors changed. Reopen Settings before saving.')
            descriptors = deepcopy(previous['body']['descriptors']) if previous else {}
            descriptors[key] = descriptor
            result = self.store.put('SETTINGS-AGENTS', 'agent-descriptors', PRIVATE,
                {'descriptors': descriptors, 'persona_id': key, 'previous': expected,
                 'reason': optional(data, 'reason') or f'Updated descriptor for {key}',
                 'author': self.intake.actor, 'at': now()}, expected['revision'] if expected else 0)
        return {'message': 'Agent descriptor saved for this project.', 'ref': asdict(result)}

    def connections(self):
        record = self.intake.latest('SETTINGS-INTEGRATIONS')
        return {'ref': asdict(record['ref']) if record else None,
                'items': record['body']['items'] if record else []}

    def save_connection(self, data, *, admin=False, principal=None):
        if not admin:
            self.intake.settings_editor()
        with self.store.transaction():
            current = self.connections()
            if data.get('expected') != current['ref']:
                raise StaleBasis('Integration settings changed. Reopen Settings before saving.')
            items = current['items']; key = data.get('id')
            prior = next((item for item in items if item['id'] == key), None)
            if key and not prior:
                raise ValueError('Choose an existing connection')
            if not prior and len(items) >= 20:
                raise ValueError('Keep at most twenty connection definitions')
            kind = data.get('kind')
            if kind not in {'mcp', 'api'}:
                raise ValueError('Choose MCP or API')
            endpoint = text(data, 'endpoint', 2000)
            try:
                url = urlsplit(endpoint)
                valid = url.scheme in {'http', 'https'} and url.hostname and url.port != 0
            except ValueError:
                valid = False
            if not valid or url.username or url.password or url.query or url.fragment:
                raise ValueError('Use an HTTP(S) endpoint without credentials, query parameters or fragments')
            credential = optional(data, 'credential_ref')
            if credential and not re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', credential):
                raise ValueError('Use an environment-variable name, such as JIRA_API_TOKEN, not a secret value')
            item = {'id': key or uuid4().hex, 'name': text(data, 'name', 120), 'kind': kind,
                    'endpoint': endpoint, 'purpose': text(data, 'purpose', 1000),
                    'credential_ref': credential, 'status': 'not-connected'}
            items = [item if entry['id'] == key else entry for entry in items] if prior else [*items, item]
            result = self.store.put('SETTINGS-INTEGRATIONS', 'integration-settings', PRIVATE,
                {'items': items, 'previous': current['ref'], 'reason': f'Saved connection definition: {item["name"]}',
                 'author': self.intake.actor, 'principal': principal, 'at': now()}, current['ref']['revision'] if current['ref'] else 0)
        return {'message': 'Connection details saved. This integration is not connected; no request was sent.', 'ref': asdict(result)}
