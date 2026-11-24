"""Admin-managed local model profiles and explicit project assignments.

Credentials live only in this server-owned file, never in project/chat records.
Each request gets one immutable provider adapter and a safe configuration reference.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from uuid import uuid4

from .core import StaleBasis
from .model_provider import OpenAIModel, AnthropicModel, UnconfiguredModel, ModelUnavailable

GENERAL = '__general__'
PROVIDERS = {'openai': 'OpenAI', 'anthropic': 'Anthropic'}
TEST_SCHEMA = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
               'required': ['ready'], 'additionalProperties': False}


def validated(provider, model, key):
    if provider not in PROVIDERS:
        raise ValueError('Choose a supported provider.')
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}', model):
        raise ValueError('Enter the model ID supplied by your provider.')
    if not isinstance(key, str) or not re.fullmatch(r'[!-~]{1,4096}', key):
        raise ValueError('Enter an API key without spaces or line breaks.')
    return dict(provider=provider, model=model, api_key=key)


def public_profile(profile):
    return {k: deepcopy(profile.get(k)) for k in ('id', 'name', 'provider', 'model', 'revision', 'test')}


def adapter(profile):
    if not profile:
        return UnconfiguredModel()
    cls = OpenAIModel if profile['provider'] == 'openai' else AnthropicModel
    model = cls(profile['api_key'], profile['model'])
    model.connection_ref = {k: profile[k] for k in ('id', 'name', 'revision', 'provider', 'model')}
    return model


class ModelConnections:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.config = dict(version=1, revision=0, profiles={}, assignments={}, history=[])
        if self.path.is_symlink():
            raise ValueError('The model connection file must not be a symbolic link.')
        if self.path.exists():
            try:
                cfg = json.loads(self.path.read_text(encoding='utf-8'))
                if cfg['version'] != 1 or type(cfg['revision']) is not int or cfg['revision'] < 0:
                    raise ValueError()
                if not isinstance(cfg['profiles'], dict) or not isinstance(cfg['assignments'], dict) or not isinstance(cfg['history'], list):
                    raise ValueError()
                for key, row in cfg['profiles'].items():
                    if key != row['id'] or type(row['revision']) is not int or row['revision'] < 1:
                        raise ValueError()
                    validated(row['provider'], row['model'], row['api_key'])
                if any(value not in cfg['profiles'] for value in cfg['assignments'].values()):
                    raise ValueError()
                self.config = cfg
            except (ValueError, KeyError, TypeError):
                raise ValueError('The local model connections file could not be read. It was not replaced.') from None

    def import_existing(self, model, projects):
        """Explicit one-time CLI migration, preserving the previous local runtime scope."""
        with self.lock:
            if self.path.exists() or self.config['revision']:
                return False
            if not model.status().get('configured'):
                return False
            if not isinstance(model, (OpenAIModel, AnthropicModel)):
                raise ValueError('Only a native model connection can be imported.')
            provider = 'openai' if isinstance(model, OpenAIModel) else 'anthropic'
            values = validated(provider, model.model, model.api_key)
            cfg = deepcopy(self.config)
            key = 'MODEL-' + uuid4().hex
            cfg['profiles'][key] = dict(id=key, name='Existing model connection', revision=1, **values)
            cfg['assignments'] = {p: key for p in set(projects) | {GENERAL}}
            self.persist(cfg, 'existing-server-connection-imported', 'server-startup', profile=key,
                         projects=sorted(cfg['assignments']), configuration=public_profile(cfg['profiles'][key]))
            return True

    def effective(self, project=GENERAL):
        with self.lock:
            row = self.config['profiles'].get(self.config['assignments'].get(project))
            return dict(configured=bool(row), profile=public_profile(row) if row else None)

    def select(self, projects=()):
        """No fallback to another project's key, and no cross-provider fan-out."""
        with self.lock:
            targets = set(projects) or {GENERAL}
            selected = {self.config['assignments'].get(project) for project in targets}
            if len(selected) > 1:
                raise ValueError('These projects use different model connections. Use a separate conversation for each connection, or ask the Administrator to align their assignments.')
            key = next(iter(selected))
            return adapter(deepcopy(self.config['profiles'].get(key)))

    def state(self, projects, admin=False, project=GENERAL):
        with self.lock:
            out = dict(available=True, can_manage=admin, revision=self.config['revision'], **self.effective(project))
            if admin:
                valid = {row['id'] for row in projects} | {GENERAL}
                out.update(profiles=[public_profile(row) for row in self.config['profiles'].values()],
                           projects=[dict(id=GENERAL, title='General AI partner'),
                                     *[dict(id=row['id'], title=row['title'], reference=row.get('reference'), display_title=row.get('display_title',row['title'])) for row in projects]],
                           assignments={k: v for k, v in self.config['assignments'].items() if k in valid},
                           history=deepcopy(self.config['history'][-20:]))
            return out

    def check_version(self, data):
        if type(data.get('expected')) is not int or data['expected'] != self.config['revision']:
            raise StaleBasis('Model settings changed. Reopen Settings before continuing.')

    def persist(self, cfg, action, actor, **details):
        if self.path.is_symlink():
            raise ValueError('The model connection file must not be a symbolic link.')
        cfg['revision'] += 1
        cfg['history'] = [*cfg['history'], dict(action=action, actor=actor,
            at=datetime.now(timezone.utc).isoformat(), **details)][-100:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.model-', suffix='.json', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump(cfg, out)
                out.flush()
                os.fsync(out.fileno())
            os.chmod(name, 0o600)
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)
        self.config = cfg

    def save(self, data, actor):
        with self.lock:
            self.check_version(data)
            cfg = deepcopy(self.config)
            key = data.get('id') or 'MODEL-' + uuid4().hex
            prior = cfg['profiles'].get(key)
            if data.get('id') and not prior:
                raise ValueError('Choose an existing model connection.')
            if not prior and len(cfg['profiles']) >= 20:
                raise ValueError('Keep at most twenty model connections in this local copy.')
            name = data.get('name')
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or any(ord(c) < 32 for c in name):
                raise ValueError('Give this connection a short name.')
            provider = data.get('provider')
            secret = data.get('api_key')
            if secret == '' and prior and provider == prior['provider']:
                secret = prior['api_key']
            values = validated(provider, data.get('model'), secret)
            cfg['profiles'][key] = dict(id=key, name=name.strip(), revision=prior['revision'] + 1 if prior else 1, **values)
            affected = [project for project, selected in cfg['assignments'].items() if selected == key]
            self.persist(cfg, 'connection-saved', actor, profile=key, profile_revision=cfg['profiles'][key]['revision'], projects=affected, configuration=public_profile(cfg['profiles'][key]))
        return dict(message='Model connection saved. Test it, then assign it to projects.', modelConnectionProfile=key)

    def assign(self, data, actor, valid_projects):
        with self.lock:
            self.check_version(data)
            cfg = deepcopy(self.config)
            key = data.get('id')
            if key not in cfg['profiles']:
                raise ValueError('Choose a saved connection.')
            selected = data.get('projects')
            if not isinstance(selected, list) or any(not isinstance(v, str) for v in selected) or len(set(selected)) != len(selected) or not set(selected) <= set(valid_projects) | {GENERAL}:
                raise ValueError('Choose valid, distinct project destinations.')
            previous = {p for p, value in cfg['assignments'].items() if value == key}
            cfg['assignments'] = {p: value for p, value in cfg['assignments'].items() if value != key}
            cfg['assignments'].update({p: key for p in selected})
            self.persist(cfg, 'assignments-saved', actor, profile=key, projects=selected, removed=sorted(previous - set(selected)))
        return dict(message='Assignments saved. New requests use these settings; existing work is unchanged.', modelConnectionProfile=key)

    def test(self, data, actor):
        with self.lock:
            self.check_version(data)
            cfg = deepcopy(self.config)
            row = cfg['profiles'].get(data.get('id'))
            if not row:
                raise ValueError('Choose a saved connection first.')
            version = cfg['revision']
            model = adapter(row)
        result = dict(status='passed', at=datetime.now(timezone.utc).isoformat())
        try:
            response = model.generate(instructions='Connection check only. Return ready=true. Do not use tools.',
                                      context={'purpose': 'local-connection-test'}, schema=TEST_SCHEMA)
            if response.get('output') != {'ready': True}:
                raise ModelUnavailable('The model did not return the required structured response. Check that it supports this API.')
        except ModelUnavailable as error:
            result.update(status='failed', error=str(error).replace(row['api_key'], '[redacted]'))
        except Exception:
            result.update(status='failed', error='The connection test could not complete. Check the model and API key, then retry.')
        with self.lock:
            if self.config['revision'] != version:
                raise StaleBasis('Model settings changed during the test. Test the current connection again.')
            cfg['profiles'][row['id']]['test'] = result
            self.persist(cfg, 'connection-tested', actor, profile=row['id'], status=result['status'])
        return dict(message='Connection test passed.' if result['status'] == 'passed' else result['error'], modelConnectionProfile=row['id'])

    def remove(self, data, actor):
        if data.get('confirm_remove') is not True:
            raise ValueError('Confirm removing this connection and its saved key.')
        with self.lock:
            self.check_version(data)
            cfg = deepcopy(self.config)
            key = data.get('id')
            if key not in cfg['profiles']:
                raise ValueError('Choose a saved connection.')
            affected = [p for p, value in cfg['assignments'].items() if value == key]
            cfg['assignments'] = {p: value for p, value in cfg['assignments'].items() if value != key}
            del cfg['profiles'][key]
            self.persist(cfg, 'connection-removed', actor, profile=key, projects=affected)
        return dict(message='Connection and key removed. Existing project work and conversations are retained.', modelConnectionProfile='')
