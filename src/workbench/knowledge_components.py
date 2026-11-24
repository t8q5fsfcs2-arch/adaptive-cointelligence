"""D014: components, block recipes and the feeds rule. Deterministic; no model calls, no writes.

A block carries a component when one of the component's configured sources holds content.
A block is *eligible* to count toward a requirement category when it carries every
component the category needs, links to the requirement with an accepted relation and
belongs to an accepted family. Eligible is not counted: only validated (saved or
published) blocks count, and a person validates (D003, D004).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .knowledge_cards import TYPES, TYPE_FAMILY, RELATIONS, LEGACY_TYPES

CONFIG = Path(__file__).with_name('config') / 'knowledge_components.json'
COMPONENT_ORDER = ('actor', 'situation', 'claim', 'basis', 'strength', 'time', 'rationale',
                   'alternatives', 'criterion', 'measure', 'owner', 'status')


@lru_cache(maxsize=1)
def config() -> dict:
    data = json.loads(CONFIG.read_text())
    validate(data)
    return data


def validate(data: dict) -> None:
    """The component set is fixed; recipes and categories may only use it."""
    if tuple(data['components']) != COMPONENT_ORDER:
        raise ValueError('The component set is fixed by D014; change it only with a decision record')
    if set(data['recipes']) != set(TYPES):
        raise ValueError('Every building block type needs a recipe')
    for name, recipe in data['recipes'].items():
        used = recipe['required'] + recipe['optional']
        if set(used) - set(COMPONENT_ORDER) or len(set(used)) != len(used):
            raise ValueError(f'{name}: a recipe uses only distinct, known components')
    for key, category in data['categories'].items():
        if set(category['needs']) - set(COMPONENT_ORDER):
            raise ValueError(f'{key}: a category needs only known components')
        if set(category['relations']) - set(RELATIONS) - {'references'}:
            raise ValueError(f'{key}: a category accepts only known relations')
        if set(category['families']) - set(data['use_by_family']):
            raise ValueError(f'{key}: a category accepts only known families')


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def block_parts(record: dict) -> dict:
    """Normalise a private or shared block into type, statement, fields, links and evidence."""
    body = record['body']
    if record['kind'] == 'knowledge-card':
        kind = body.get('type', 'note')
        return dict(type=kind, statement=body.get('statement', ''), rationale=body.get('rationale', ''),
                    fields=body.get('fields') or {}, relations=body.get('relations') or [],
                    evidence=body.get('evidence') or [], reviewed=(body.get('evidence_assessment') or {}).get('support', {}).get('assessment') not in (None, 'unassessed'),
                    status='published', author=body.get('owner'))
    payload = body.get('payload') or {}
    card = body.get('card') or {}
    kind = card.get('type') or LEGACY_TYPES.get(payload.get('kind'), 'note')
    return dict(type=kind if kind in TYPES else 'note', statement=payload.get('statement', ''),
                rationale=payload.get('rationale', ''), fields=card.get('fields') or {},
                relations=card.get('relations') or [], evidence=payload.get('evidence') or [],
                reviewed=bool(body.get('evidence_review')), status=body.get('status', 'held'),
                author=body.get('owner'))


def components_of(record: dict) -> list[str]:
    """Which components a block carries, in the fixed order."""
    parts = block_parts(record)
    carried = []
    for key, spec in config()['components'].items():
        has = bool(spec.get('always'))
        has = has or any(_text(parts['fields'].get(f)) for f in spec.get('fields', []))
        has = has or any(_text(parts.get(f)) for f in spec.get('payload', []))
        has = has or (spec.get('evidence') and bool(parts['evidence']))
        has = has or (spec.get('evidence_review') and parts['reviewed'])
        has = has or (spec.get('author_fallback') and _text(parts['author']) and
                      not any(f in TYPES[parts['type']]['fields'] for f in spec.get('fields', [])))
        if has:
            carried.append(key)
    return carried


def recipe(block_type: str) -> dict:
    return config()['recipes'][block_type]


def missing_for_recipe(record: dict) -> list[str]:
    parts = block_parts(record)
    have = set(components_of(record))
    return [c for c in recipe(parts['type'])['required'] if c not in have]


def link_use(block_type: str) -> str:
    """D014 Rule 5: a link's use follows the family of the block that makes it."""
    return config()['use_by_family'][TYPE_FAMILY.get(block_type, 'outputs')]


def suggested_conditions(record: dict) -> str:
    """A provisional suggestion for link conditions, taken from the block's own scope fields."""
    fields = block_parts(record)['fields']
    people = next((fields[f] for f in ('applies_people', 'people', 'population', 'participants', 'role') if _text(fields.get(f))), '')
    situation = next((fields[f] for f in ('applies_situation', 'situation', 'conditions', 'scope') if _text(fields.get(f))), '')
    return '; '.join(v.strip() for v in (people, situation) if v)[:800]


def drawers(records: list[dict]) -> list[dict]:
    """The project's requirement areas: the published intake profile, else the default profile."""
    profile = next((r for r in records if r['kind'] == 'intake-profile'), None)
    if profile and isinstance(profile['body'].get('drawers'), list):
        return profile['body']['drawers']
    return json.loads((Path(__file__).with_name('config') / 'intake_profile.json').read_text())['drawers']


def public_config() -> dict:
    data = config()
    return dict(components={k: dict(label=v['label'], holds=v['holds']) for k, v in data['components'].items()},
                recipes=data['recipes'], categories=data['categories'], packet_types=data['packet_types'])


def area_of(requirement: dict, drawers: list[dict]) -> str | None:
    """The requirement category (area key) a requirement belongs to."""
    rid = requirement['ref'].id if hasattr(requirement.get('ref'), 'id') else requirement.get('ref', {}).get('id', '')
    keys = {d['key'] for d in drawers}
    if isinstance(rid, str) and rid.startswith('REQ-INTAKE-'):
        head = rid[len('REQ-INTAKE-'):].split('/')[0]
        if head in keys:
            return head
    label = (requirement.get('body') or {}).get('drawer', '')
    if isinstance(label, str):
        tail = label.split(' / ')[-1].strip().lower()
        head = label.split(' / ')[0].strip().lower()
        for d in drawers:
            if d['label'].lower() in (head, tail):
                return d['key']
            if any(c['label'].lower() == tail for c in d.get('children', [])):
                return d['key']
    return None


def eligibility(record: dict, relation: str, area: str) -> dict:
    """Whether a block may count toward one requirement category, and what it lacks."""
    category = config()['categories'].get(area)
    parts = block_parts(record)
    if category is None:
        return dict(area=area, eligible=False, missing=[], relation_ok=False, family_ok=False, counts=False,
                    coaching='This requirement has no category, so eligibility cannot be judged.')
    have = set(components_of(record))
    missing = [c for c in category['needs'] if c not in have]
    relation_ok = relation in category['relations']
    family = TYPE_FAMILY.get(parts['type'], 'outputs')
    family_ok = family in category['families']
    eligible = not missing and relation_ok and family_ok
    labels = config()['components']
    if eligible:
        coaching = f"Eligible for {category['label']}." + (' Counts once validated.' if parts['status'] == 'suggested' else '')
    elif missing:
        coaching = 'Add ' + ', '.join(labels[c]['holds'].lower() for c in missing) + f" and it can count toward {category['label']}."
    elif not relation_ok:
        coaching = f"{category['label']} accepts these links: " + ', '.join(RELATIONS.get(r, r).lower() for r in category['relations']) + '.'
    else:
        coaching = f"{category['label']} counts {', '.join(category['families'])} blocks; this is a {family} block."
    return dict(area=area, label=category['label'], eligible=eligible, missing=missing, relation_ok=relation_ok,
                family_ok=family_ok, counts=eligible and parts['status'] != 'suggested', coaching=coaching)


def block_view(record: dict, requirement_lookup, drawers: list[dict]) -> dict:
    """Components, recipe gaps, link uses, suggested conditions and eligibility for one block."""
    parts = block_parts(record)
    links = []
    for link in parts['relations']:
        target = requirement_lookup(link.get('ref', {}).get('id'))
        entry = dict(ref=link.get('ref'), relation=link.get('relation'), use=link_use(parts['type']))
        if target is not None:
            area = area_of(target, drawers)
            entry['eligibility'] = eligibility(record, link.get('relation'), area)
        links.append(entry)
    return dict(type=parts['type'], components=components_of(record), missing=missing_for_recipe(record),
                use=link_use(parts['type']), suggested_conditions=suggested_conditions(record), links=links)
