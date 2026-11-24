"""Two-level requirement taxonomy. Criteria are versioned guidance, not approval."""
from copy import deepcopy
from .validation import required, optional
from .requirement_drafts import save_entries

WHEN = {'always', 'digital', 'operational', 'market', 'other', 'disabled'}

def validate_children(raw, actors, fields):
    if not isinstance(raw, list) or len(raw) > 20:
        raise ValueError('Use at most twenty sub-drawers per category')
    result, keys = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError('Each sub-drawer must have a definition')
        key = required(item, 'key')
        if not key.replace('-', '').isalnum() or len(key) > 60 or key in keys:
            raise ValueError('Each sub-drawer needs a unique short key within its category')
        keys.add(key)
        if item.get('children'):
            raise ValueError('Use category, sub-drawer, then requirements; deeper nesting is not supported')
        if item.get('owner') not in actors or item.get('when') not in WHEN:
            raise ValueError('Choose a sub-drawer lead and applicability')
        basis = item.get('basis_fields')
        if not isinstance(basis, list) or not basis or any(f not in fields for f in basis):
            raise ValueError('Each sub-drawer needs valid intake field links')
        result.append(dict(key=key, owner=item['owner'], when=item['when'], basis_fields=basis,
            **{k:required(item,k) for k in ('label','question','criteria','evidence','revisit')},
            references=optional(item,'references')))
    return result

def prepare_children(config, previous, values, changed):
    old = {d['key']: d for d in previous}
    result = []
    for template in config:
        before = old.get(template['key'], {})
        applicable = template['when'] in {'always', values['work_kind']}
        retained = {k:deepcopy(before[k]) for k in ('included','label','question','owner','rationale',
            'requirement','acceptance_criteria','requirements','agent_provenance','exclusion_reason','project_focus','goal_ids') if k in before}
        # Preserve deliberate edits, but let unchanged template wording follow the SME's revision.
        if before.get('question') == before.get('template_question'):
            retained.pop('question', None)
        child = dict(template, included=True, requirement='', acceptance_criteria='',
            rationale='Connect ' + template['label'].lower() + ' to the intended user outcome and the applicable constraints.',
            exclusion_reason='')
        child.update(retained)
        child.update(template_question=template['question'], configured_applicable=applicable,
            intake_fields=list(values), changed_intake_fields=changed)
        if not applicable:
            child.update(included=False, exclusion_reason='Excluded by the configured applicability rule.')
        elif before.get('configured_applicable') is False:
            child.update(included=True, exclusion_reason='')
        result.append(child)
    return result

def save_focus_edits(item,saved):
    if saved.get('project_focus') and 'project_checks' in item:
        focus=saved['project_focus']
        edits={k:(required if k in ('question','rationale') else optional)(item,'project_'+k) for k in ('question','rationale','checks','gaps')}
        if any(focus[k]!=edits[k] for k in edits):focus['edited']=True
        focus.update(edits)

def save_children(raw, current, actors, parent_key=None):
    if not isinstance(raw,list) or [d.get('key') for d in raw] != [d['key'] for d in current]:
        raise ValueError('The sub-drawer set changed. Reload the scaffold')
    for item, saved in zip(raw,current):
        if type(item.get('included')) is not bool or item.get('owner') not in actors:
            raise ValueError('Choose an inclusion and lead for each sub-drawer')
        if item['included'] and saved.get('configured_applicable') is False:
            raise ValueError('Change applicability in Intake settings before including this sub-drawer')
        reason = optional(item,'exclusion_reason')
        if not item['included'] and not reason:
            raise ValueError('Explain why the sub-drawer is excluded from this project')
        saved.update({k:required(item,k) for k in ('label','question','rationale')})
        save_entries(item, saved, (parent_key + '/' if parent_key else '') + saved['key'])
        saved.update(included=item['included'],owner=item['owner'],exclusion_reason=reason)
        save_focus_edits(item,saved)

def select_drawer(scaffold, path):
    parts = path.split('/') if isinstance(path,str) else []
    if not 1 <= len(parts) <= 2:
        raise ValueError('Choose a category or sub-drawer')
    parent = next((d for d in scaffold if d['key']==parts[0] and d['included']), None)
    if not parent:
        raise ValueError('Choose an included category')
    if len(parts)==1:
        return parent, None
    child = next((d for d in parent.get('children',[]) if d['key']==parts[1] and d['included']),None)
    if not child:
        raise ValueError('Choose an included sub-drawer')
    return child, parent

def published_drawers(scaffold):
    """Flat persisted IDs retain parent links; requirements attach to the precise area."""
    for parent in scaffold:
        if not parent['included']:
            continue
        yield {**parent, 'parent_id':None}
        for child in parent.get('children',[]):
            if child['included']:
                yield {**child, 'local_key':child['key'], 'key':parent['key']+'/'+child['key'],
                       'parent_id':'DRW-'+parent['key'], 'category_label':parent['label']}
