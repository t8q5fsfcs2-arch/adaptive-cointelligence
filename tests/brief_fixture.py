"""Explicit fictional author-completed Design brief for lifecycle fixtures."""
from dataclasses import asdict
from workbench.domain_brief import BRIEF_ESSENTIALS

def complete_design_brief(w,draft):
    if w.domains.key!='design':return None
    existing=w.domain_brief.readiness(draft)
    if existing['ready']:return w.store.read(type(draft['ref'])(**existing['brief']),w.scopes)
    w.command('domain-brief-create',dict(work_request=draft['body'].get('work_request')))
    r=w.domain_brief.state()[0];reqs=r['body']['design_inputs']['requirements']
    sections=[dict(id='new-'+kind,kind=kind,title=title,text='Fictional author-defined '+title.lower()+'.',rationale='A synthetic lifecycle fixture, not operational guidance.',disposition='use',requirement_ids=[]) for kind,title in BRIEF_ESSENTIALS.items()]
    for section in sections:
        if section['kind']=='validation':section['requirement_ids']=[v['ref']['id'] for v in reqs]
    objective=dict(id='new-objective',title='Validate the fictional task',question='Can the fictional user complete the task?',why='Tests the declared intent.',output='A bounded prototype and review.',evidence='Synthetic task evidence.')
    w.command('domain-objectives-save',dict(expected=asdict(r['ref']),objectives=[objective],brief_sections=sections,complete=True))
    return w.domain_brief.state()[0]
