"""Stable requirement candidates inside versioned intake; no approval or record rewrite."""
from copy import deepcopy
import re
from .validation import optional

LIMIT = 100


def legacy_id(path):
    return 'REQ-INTAKE-' + path


def valid_id(value, path):
    return isinstance(value, str) and (value == legacy_id(path) or
        re.fullmatch(re.escape(legacy_id(path)) + r'--[a-f0-9]{12,32}', value) is not None)


def entries(area, path):
    if 'requirements' in area:
        return deepcopy(area['requirements'])
    if area.get('requirement', '').strip() or area.get('acceptance_criteria', '').strip():
        return [dict(id=legacy_id(path), title=area['label'] + ' · initial requirement',
            requirement=area.get('requirement', ''), acceptance_criteria=area.get('acceptance_criteria', ''),
            included=True, **({'agent_provenance': deepcopy(area['agent_provenance'])} if area.get('agent_provenance') else {}))]
    return []


def select_entry(area, path, id=None, *, allow_new=False):
    id = id or legacy_id(path)
    if not valid_id(id, path):
        raise ValueError('Choose a requirement belonging to this area')
    found = next((x for x in entries(area, path) if x['id'] == id), None)
    if found is None and allow_new:
        return dict(id=id, title='', requirement='', acceptance_criteria='', included=True)
    if found is None:
        raise ValueError('This requirement draft is no longer available. Reload the area')
    return found


def mirror(area, path):
    """Keep older single-draft readers compatible without flattening the collection."""
    rows = area['requirements']
    primary = next((x for x in rows if x['id'] == legacy_id(path)), rows[0] if rows else {})
    for key in ('requirement', 'acceptance_criteria'):
        area[key] = primary.get(key, '')
    if primary.get('agent_provenance'):
        area['agent_provenance'] = deepcopy(primary['agent_provenance'])


def save_entries(supplied, area, path):
    prior = {x['id']: x for x in entries(area, path)}
    if 'requirements' not in supplied:
        if 'requirements' in area and (len(prior) > 1 or any(id != legacy_id(path) for id in prior)):
            raise ValueError('Reload the requirement entries before saving; an older form cannot replace them')
        for key in ('requirement', 'acceptance_criteria'):
            area[key] = optional(supplied, key)
        if 'requirements' in area:
            area['requirements'] = [{**x, **{k: area[k] for k in ('requirement', 'acceptance_criteria')}} for x in prior.values()]
        return
    raw = supplied['requirements']
    if not isinstance(raw, list) or len(raw) > LIMIT:
        raise ValueError('Use at most one hundred requirements per area')
    result, ids = [], set()
    for row in raw:
        if not isinstance(row, dict) or not valid_id(row.get('id'), path) or row['id'] in ids:
            raise ValueError('Each requirement needs its own stable identity within the area')
        if type(row.get('included')) is not bool:
            raise ValueError('Choose whether to include each requirement')
        ids.add(row['id'])
        item = {**deepcopy(prior.get(row['id'], {})), 'id': row['id'], 'included': row['included']}
        item.update({key: optional(row, key) for key in ('title', 'requirement', 'acceptance_criteria')})
        result.append(item)
    if set(prior) - ids:
        raise ValueError('Keep existing requirements; exclude them from direction instead of deleting their history')
    area['requirements'] = result
    mirror(area, path)


def put_entry(area, path, item):
    rows = entries(area, path)
    index = next((n for n, x in enumerate(rows) if x['id'] == item['id']), None)
    if index is None:
        if len(rows) >= LIMIT:
            raise ValueError('Use at most one hundred requirements per area')
        rows.append(deepcopy(item))
    else:
        rows[index] = deepcopy(item)
    area['requirements'] = rows
    mirror(area, path)
