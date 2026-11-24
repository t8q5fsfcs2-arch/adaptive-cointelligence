"""Replaceable model boundary. No workflow, UI, database or decision authority."""
from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailable(ValueError):
    pass


def openai_limit_message(error):
    """Use known error codes only; never expose provider bodies or credentials."""
    fallback = 'The model service usage or rate limit was reached. Check API billing and project limits.'
    try:
        raw = error.read(16_385)
        if len(raw) > 16_384:
            return fallback
        body = json.loads(raw)
        detail = body.get('error', {}) if isinstance(body, dict) else {}
        if not isinstance(detail, dict):
            return fallback
        code, kind = detail.get('code'), detail.get('type')
    except (OSError, TypeError, ValueError):
        return fallback
    messages = {
        'credit_balance_exhausted': 'The model service reports no API credits remaining. Check the billing balance for the organization that owns this API key.',
        'organization_spend_limit_exceeded': 'The model service organization has reached its API spending limit. Review that limit in API settings.',
        'project_spend_limit_exceeded': 'This model API project has reached its spending limit. Review the project limit in API settings.',
        'organization_usage_limit_exceeded': 'The model service organization has reached its API usage allowance. Review the organization limits in API settings.',
        'insufficient_quota': 'The model service reports an API billing or quota limit. Check available credits and organization/project limits in the model service settings.',
        'rate_limit_exceeded': 'The model service is temporarily limiting requests. Wait briefly before trying again.',
        'slow_down': 'The model service is temporarily limiting requests. Wait briefly before trying again.',
    }
    if isinstance(code, str) and code in messages:
        return messages[code]
    if kind == 'insufficient_quota':
        return messages['insufficient_quota']
    if kind == 'rate_limit_error':
        return messages['rate_limit_exceeded']
    return fallback


def request_timeout(context):
    """Whole-document drafting needs more time than a focused AI partner response."""
    if context.get('skill') in ('integrity-review','integrity-decision-dialogue'):return 120
    return 180 if context.get('skill') in ('seed-value','assess-change','assess-business','tailor-scaffold','design-pdf-review','domain-conversation','domain-brief-objectives','domain-design-brief','domain-prototype-alternatives','domain-submission-evaluation') else 55


def response_failure(provider, error, timeout):
    """Return model-neutral failures without exposing provider payloads; receipts retain provider identity."""
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, TimeoutError):
        return f"The configured model took longer than {timeout} seconds to respond. Your document and answers are saved. You can retry."
    if isinstance(error, (URLError, OSError)):
        return f"The connection to the configured model was interrupted. Your document and answers are saved. You can retry."
    return f"The configured model returned an unreadable response. Your document and answers are saved. You can retry."


class ModelProvider(Protocol):
    def status(self) -> dict: ...
    def generate(self, *, instructions: str, context: dict, schema: dict) -> dict: ...


class UnconfiguredModel:
    def status(self):
        return {"configured": False, "provider": None, "model": None}

    def generate(self, **kwargs):
        raise ModelUnavailable("No model connection is assigned. Ask the Administrator to check Settings → Model connections, or use the server configuration. Your draft and sources are saved; no substitute answer was generated.")


@dataclass(repr=False)
class OpenAIModel:
    api_key: str
    model: str

    def status(self):
        return {"configured": True, "provider": "OpenAI", "model": self.model, **({"connection": self.connection_ref} if hasattr(self, "connection_ref") else {})}

    def generate(self, *, instructions, context, schema):
        return self._generate(instructions=instructions,context=context,schema=schema)

    def generate_visual(self, *, instructions, context, schema, images):
        if not isinstance(images,list) or not 1<=len(images)<=6:raise ValueError('Choose one to six page images')
        return self._generate(instructions=instructions,context=context,schema=schema,images=images)

    def request_settings(self, context):
        settings = dict(timeout_seconds=request_timeout(context), max_output_tokens=14000 if context.get('skill') in ('assess-change','assess-business','tailor-scaffold','domain-prototype-alternatives') else 8000)
        # Narrow latency policy for the measured integrity task. Other models/tasks
        # retain their provider defaults; never send GPT-5-only parameters broadly.
        if context.get('skill') in ('integrity-review','integrity-decision-dialogue') and re.fullmatch(r'gpt-5(?:-mini|-nano)?(?:-\d{4}-\d{2}-\d{2})?',self.model):
            settings.update(reasoning_effort='low',verbosity='low',max_output_tokens=6000)
            contract=context.get('option_contract',{})
            if contract.get('required_packet_findings') is not None:
                clauses=len(contract.get('clauses',{}));pairs=len(contract['required_packet_findings'])
                settings.update(max_output_tokens=min(24000,max(8000,4000+clauses*650+pairs*200)),timeout_seconds=300)
            if context.get('assessment_phase') in ('clause-mapping','joint-comparison'):
                settings.update(reasoning_effort='medium',max_output_tokens=10000 if context['assessment_phase']=='clause-mapping' else 18000)
                if context['assessment_phase']=='clause-mapping' and context.get('option_contract',{}).get('material_parts'):
                    settings['max_output_tokens']=min(16000,10000+200*len(context['option_contract']['material_parts']))
            if context.get('assessment_phase') in ('condition-inventory','condition-inventory-review'):
                settings.update(reasoning_effort='medium',max_output_tokens=18000,timeout_seconds=300)
        if context.get('skill')=='domain-submission-evaluation' and re.fullmatch(r'gpt-5(?:-mini|-nano)?(?:-\d{4}-\d{2}-\d{2})?',self.model):
            settings.update(reasoning_effort='low',verbosity='low',max_output_tokens=16000,timeout_seconds=180)
        return settings

    def _generate(self, *, instructions, context, schema, images=None):
        settings=self.request_settings(context)
        payload = {"model": self.model, "store": False, "max_output_tokens": settings["max_output_tokens"],
                   "instructions": instructions, "input": json.dumps(context),
                   "text": {"format": {"type": "json_schema", "name": "intake_coaching", "strict": True, "schema": schema}}}
        if 'reasoning_effort' in settings:payload['reasoning']={'effort':settings['reasoning_effort']}
        if 'verbosity' in settings:payload['text']['verbosity']=settings['verbosity']
        if images:
            parts=[dict(type='input_text',text=json.dumps(context))]
            for image in images:
                if image.get('mime_type')!='image/png' or not isinstance(image.get('data'),str) or len(image['data'])>7*1024*1024:raise ValueError('Use bounded PNG page inputs')
                parts.extend([dict(type='input_text',text=image['label']),dict(type='input_image',image_url='data:image/png;base64,'+image['data'],detail='high')])
            payload['input']=[dict(role='user',content=parts)]
        req = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key}, method="POST")
        try:
            with urlopen(req, timeout=settings["timeout_seconds"]) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ModelUnavailable("The model response was too large. Nothing was applied.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError('Expected response object')
        except HTTPError as e:
            if e.code == 429:
                raise ModelUnavailable(openai_limit_message(e)) from None
            messages = {401: "The model API key was not accepted.", 403: "This model connection is not permitted.",
                        404: "The configured model is unavailable. Check the model name."}
            raise ModelUnavailable(messages.get(e.code, "The model service rejected the request. Check the model configuration and retry.")) from None
        except (URLError, TimeoutError, OSError, ValueError) as e:
            if isinstance(e, ModelUnavailable):
                raise
            raise ModelUnavailable(response_failure("OpenAI", e, request_timeout(context))) from None
        if result.get('status') != 'completed':
            raise ModelUnavailable("The model response was incomplete. Try a narrower question or fewer sources. Nothing was applied.")
        content = [c for o in result.get('output', []) if o.get('type') == 'message' for c in o.get('content', [])]
        if any(c.get('type') == 'refusal' for c in content):
            raise ModelUnavailable("The model declined this request. Your draft remains unchanged.")
        try:
            output = json.loads(''.join(c.get('text','') for c in content if c.get('type') == 'output_text'))
        except (TypeError, ValueError):
            raise ModelUnavailable("The model returned an unusable AI partner response. Nothing was applied.") from None
        return {'output': output, 'usage': result.get('usage', {}), 'model': result.get('model', self.model), 'response_id': result.get('id'), 'request_settings': settings}


@dataclass(repr=False)
class AnthropicModel:
    api_key: str
    model: str

    def status(self):
        return {"configured": True, "provider": "Anthropic", "model": self.model, **({"connection": self.connection_ref} if hasattr(self, "connection_ref") else {})}

    def generate(self, *, instructions, context, schema):
        payload = {"model": self.model, "max_tokens": 6000, "system": instructions,
                   "messages": [{"role": "user", "content": json.dumps(context)}],
                   "tools": [{"name": "propose_intake_help", "description": "Return bounded AI partner proposals. This does not change records or call application tools.", "input_schema": schema}],
                   "tool_choice": {"type": "tool", "name": "propose_intake_help"}}
        req = Request("https://api.anthropic.com/v1/messages", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, method="POST")
        try:
            with urlopen(req, timeout=request_timeout(context)) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ModelUnavailable("The model response was too large. Nothing was applied.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError('Expected response object')
        except HTTPError as e:
            messages = {401: "The model credential was not accepted.", 403: "This model connection is not permitted.",
                        404: "The configured model is unavailable. Check the model name.", 429: "The model service is busy or its usage limit was reached."}
            raise ModelUnavailable(messages.get(e.code, "The model service rejected the request. Check its configuration and retry.")) from None
        except (URLError, TimeoutError, OSError, ValueError) as e:
            if isinstance(e, ModelUnavailable):
                raise
            raise ModelUnavailable(response_failure("Anthropic", e, request_timeout(context))) from None
        if result.get("stop_reason") == "max_tokens":
            raise ModelUnavailable("The response was incomplete. Try a narrower question or fewer sources. Nothing was applied.")
        blocks = [b for b in result.get("content", []) if b.get("type") == "tool_use" and b.get("name") == "propose_intake_help"]
        if len(blocks) != 1 or not isinstance(blocks[0].get("input"), dict):
            raise ModelUnavailable("The model did not return usable AI partner proposals. Nothing was applied.")
        return {"output": blocks[0]["input"], "usage": result.get("usage", {}), "model": result.get("model", self.model)}


def load_model(config_path=None):
    """Read server-only configuration; never execute shell syntax or expose secrets."""
    def read(path):
        p = Path(path).expanduser()
        if not p.is_file():
            return {}
        values = {}
        for line in p.read_text().splitlines():
            if line.strip().startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
        return values
    values = read(config_path or '.env.local')
    # A local pointer can reuse the developer's existing broker settings without copying a key.
    if values.get('COACH_CONFIG_FILE'):
        values = {**read(values['COACH_CONFIG_FILE']), **values}
    for key in ('COACH_LLM_PROVIDER', 'COACH_LLM_API_KEY', 'COACH_LLM_MODEL', 'OPENAI_API_KEY'):
        if os.environ.get(key):
            values[key] = os.environ[key]
    if values.get('COACH_LLM_PROVIDER') == 'anthropic' and all(values.get(k) for k in ('COACH_LLM_API_KEY','COACH_LLM_MODEL')):
        return AnthropicModel(values['COACH_LLM_API_KEY'], values['COACH_LLM_MODEL'])
    if values.get('COACH_LLM_PROVIDER', 'openai') == 'openai' and (values.get('OPENAI_API_KEY') or values.get('COACH_LLM_API_KEY')):
        return OpenAIModel(values.get('OPENAI_API_KEY') or values['COACH_LLM_API_KEY'], values.get('COACH_LLM_MODEL') or 'gpt-5-mini')
    return UnconfiguredModel()


def configure():
    """Local terminal setup. Keys never travel through the browser or chat."""
    from getpass import getpass
    path = Path('.env.local')
    if path.exists():
        raise SystemExit('A .env.local already exists. Edit it locally to change the model; it was not overwritten.')
    print('Configure OpenAI for the local AI partner agent. Nothing is sent during setup.')
    key = getpass('OpenAI API key (hidden): ').strip()
    if not key or any(c.isspace() for c in key):
        raise SystemExit('No valid key entered. Nothing saved.')
    model = input('Model [gpt-5-mini]: ').strip() or 'gpt-5-mini'
    if any(c.isspace() for c in model):
        raise SystemExit('Use a model ID without spaces. Nothing saved.')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('COACH_LLM_PROVIDER=openai\nCOACH_LLM_MODEL=' + model + '\nOPENAI_API_KEY=' + key + '\n')
    print('Saved server-only configuration to .env.local (excluded from Git). Restart workbench-web to connect.')
