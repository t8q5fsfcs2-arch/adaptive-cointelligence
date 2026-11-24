"""Private main-chat plan proposals and deliverable-level plan evaluation.

These helpers do not write, publish or confer requirement authority.
"""
from copy import deepcopy
from dataclasses import asdict
from . import project_implications as implications

GUIDANCE='''PRIVATE BRIEF DEVELOPMENT: Help refine the supplied work plan in this same
conversation using accepted project inputs and configured domain knowledge. This
is a private thinking vault, not a continuous conflict approval gate. Explain
alternatives, gaps and tradeoffs. When you recommend concrete wording, label it
Brief recommendation: in ordinary prose and optionally return brief_changes for
only the supplied editable target IDs. Each value replaces that field; preserve
useful existing substance. An empty array is correct for discussion, a question,
or a review without a concrete plan recommendation. Never change incoming meaning,
requirements, acceptance criteria, evidence, authority or status. Do not claim an
update was saved. The author reviews and edits proposed wording before saving.
A later evaluation assesses the resulting deliverable, not whether a plan was filled.
'''

PLAN_GUIDANCE='''DELIVERABLE AGAINST PLAN: brief_evaluation contains author-selected working
plan criteria, separate from governing requirements. Assess each supplied section
once in plan_review: addressed, partial or not-addressed, with exact evidence,
limits and a useful next step. Addressed requires substantive cited evidence; a
mention of the plan, a completed brief or a recommendation is not performance
proof. Static screens do not prove tested behavior. Preserve obsolete-plan notices
and assess current requirements independently. Proposed/unadopted sections
are not mandatory criteria. This is advisory preparation before explicit release,
not project approval. Do not modify the plan or accepted upstream contributions.
'''

def focus(w,thread):
    from .brief_refinement import targets
    plan=w.domain_brief.for_draft(w.domain_chat.draft(thread))
    if not plan:raise ValueError('Start a working brief before developing it in chat')
    editable=targets(plan)
    if not editable:raise ValueError('Add an objective or draft a brief before discussing plan changes')
    return dict(plan=asdict(plan['ref']),editable_targets=editable,authority='Private plan proposals only; input meaning and governing records are not editable targets.')

def schema(ctx):
    return implications.obj(dict(target=dict(type='string',enum=list(ctx['brief_development']['editable_targets'])),value=dict(type='string',minLength=1,maxLength=max(v['limit'] for v in ctx['brief_development']['editable_targets'].values())),why=dict(type='string',minLength=1,maxLength=350)))

def validated(out,ctx):
    allowed=ctx.get('brief_development',{}).get('editable_targets',{});values=out.get('brief_changes',[]);result=[];seen=set()
    if not isinstance(values,list):return []
    for item in values[:20]:
        if not isinstance(item,dict) or set(item)!={'target','value','why'}:continue
        key=item['target']
        if not isinstance(key,str) or key not in allowed or key in seen:continue
        if not isinstance(item['value'],str) or not item['value'].strip() or len(item['value'])>allowed[key]['limit'] or item['value']==allowed[key]['value']:continue
        if not isinstance(item['why'],str) or not item['why'].strip() or len(item['why'])>350:continue
        seen.add(key);result.append(dict(item))
    return result

def evaluation_context(ctx):
    plan=ctx.get('brief_for_coaching')
    if not plan or plan['status'] not in {'working','completed'}:return None
    sections=[dict(id=s.get('id','section-'+str(i)),title=s['title'],text=s['text'],kind=s['kind']) for i,s in enumerate(plan['plan']) if s.get('disposition')=='use']
    return dict(ref=plan['ref'],sections=sections,authority='Author-selected private work plan; not governing requirements or evidence of completed work.')

def criteria_context(ctx):
    copy=deepcopy(ctx);copy['working_objectives']=dict(objectives=ctx.get('brief_evaluation',{}).get('sections',[]));return copy

def plan_schema(ctx):
    out=implications.objective_schema(criteria_context(ctx));props=out['items']['properties'];props['section_id']=props.pop('objective_id');out['items']['required']=[k if k!='objective_id' else 'section_id' for k in out['items']['required']];return out

def validate_plan(items,ctx):
    remapped=[]
    if not isinstance(items,list):raise ValueError('Invalid plan evaluation')
    for item in items:
        if not isinstance(item,dict) or 'section_id' not in item:raise ValueError('Use a supplied plan section')
        row={**item,'objective_id':item['section_id']};row.pop('section_id');remapped.append(row)
    implications.validate_objectives(remapped,criteria_context(ctx))
    if {r['objective_id'] for r in remapped}!=set(implications.objectives(criteria_context(ctx))):raise ValueError('Assess each selected plan section once')
