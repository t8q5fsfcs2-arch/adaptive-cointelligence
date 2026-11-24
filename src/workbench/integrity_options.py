"""Version-bound decision trace and deterministic admissibility, not semantic proof.

All prose and support judgments remain model interpretations. Exact source spans,
reference membership and declared conditions are checked here; humans retain the
substantive evidence judgment and the separate ratification transaction.
"""
from copy import deepcopy
import re
from .validation import reference
from . import integrity_parts, integrity_recommendation, integrity_interpretation, integrity_rule_bindings, integrity_relationship, integrity_followup

VERSION = 'integrity-options-v10-evidence-relationships'
ELEMENTS = ('actor','action','object','timing','scope','condition','threshold','authority','exception','acceptance_criterion')
DIMENSIONS = ('fidelity','evidence','workability','risk_and_change','effort_and_cost')
KINDS = ('retain','revise-packet','add-control','change-handoff','investigate','escalate','amend-requirement')
DIFFERENCES = ('equivalent','complementary','conflict','gap','dependency','ambiguous')


def label(ref):
    return ref['id']+':v'+str(ref['revision'])


def context(ctx,*,for_inventory=False):
    anchors={label(r) for r in ctx['requirements']}
    clauses={k:v for k,v in ctx.get('citation_catalog',{}).items() if label(v) in anchors and v['field'] in ('text','conditions','acceptance_criteria')}
    if '_integrity_clause_filter' in ctx:clauses={k:v for k,v in clauses.items() if k in ctx['_integrity_clause_filter']}
    records={label(r['ref']):r for r in ctx['records']}
    rules={}
    for ref in ctx['conditions']:
        for c in records[label(ref)]['body']['conditions']:
            rules[label(ref)+'/'+c['key']]=dict(c,requirement=records[label(ref)]['body']['requirement'],declaration_ref=ref)
    packets={label(e['packet']):dict(packet=e['packet'],expression=e['ref'],requirements=records[label(e['ref'])]['body']['requirements']) for e in ctx['expressions']}
    material_parts=({k:v for k,v in ctx['condition_inventory']['conditions'].items() if v['clause_ref'] in clauses}
        if ctx.get('condition_inventory') else integrity_parts.catalog(clauses))
    linked = integrity_rule_bindings.build(ctx,clauses)
    if ctx.get('condition_inventory'):integrity_rule_bindings.validate_frozen(ctx,clauses,material_parts)
    headings={}
    if not for_inventory:
        material_parts,headings=integrity_parts.review_projection(material_parts)
        if any(not any(v['clause_ref']==cid for v in material_parts.values()) for cid in clauses):
            raise ValueError('A governing clause contains only a section heading; clarify its material obligation before grading.')
        if '_integrity_part_filter' in ctx:
            selected=ctx['_integrity_part_filter']
            if len(selected)!=len(set(selected)) or not set(selected)<=set(material_parts):
                raise ValueError('A condition window contains duplicate or unknown material references.')
            material_parts={k:v for k,v in material_parts.items() if k in selected}
            if any(not any(v['clause_ref']==cid for v in material_parts.values()) for cid in clauses):
                raise ValueError('Every clause in a condition window needs a selected material condition.')
    return dict(contract=VERSION,clauses=clauses,material_parts=material_parts,declared_rules=rules,packets=packets,
        rule_bindings=linked,context_parts=headings,review_projection=integrity_parts.PROJECTION_VERSION,
        intended_use=ctx.get('intended_use','Inform a named human decision; no approval, source amendment or external transaction.'),
        boundary='Clause spans are source authority. Extracted elements, claim support and option comparisons are interpretations awaiting human review. Absence of a control in a packet does not prove that no control exists.')


def schema(ctx):
    c=context(ctx)
    def string(n=600,minimum=1):return dict(type='string',minLength=minimum,maxLength=n)
    def enum(items):return dict(type='string',enum=sorted(items))
    def array(items,n=12,minimum=0):return dict(type='array',items=items,minItems=minimum,maxItems=n)
    def obj(**properties):return dict(type='object',additionalProperties=False,required=list(properties),properties=properties)
    cite=enum(ctx['citation_catalog']);clause=enum(c['clauses']);packet=enum(c['packets'])
    element=obj(status=enum(('specified','unspecified','disputed')),quote=string(500,0),interpretation=string(500,0))
    rule_value=dict(anyOf=[dict(type='string',maxLength=100),dict(type='boolean'),dict(type='number'),array(string(100),12)])
    # An empty rule catalog is valid. An empty list is required in that case.
    proposed=obj(rule=enum(c['declared_rules'] or ['no-declared-rule']),value=rule_value)
    part=obj(part_ref=enum(c['material_parts']),status=enum(('supported','contradicted','absent','uncertain')),
        evidence_refs=array(cite,4),evidence_quotes=array(obj(citation_ref=cite,quote=string(600)),4),
        claim_interpretation=string(400),support_scope=string(300),reasoning=string(400),remaining_gap=string(400,0),
        interpretation=integrity_interpretation.schema())
    if ctx.get('condition_inventory'):
        part['properties'].update(evidence_relationship=integrity_relationship.schema(),evidence_level=enum([ctx['evidence_level']]),entailment_check=obj(
            counterexample_possible=dict(type='boolean'),explanation=string(400)))
        part['required']=list(part['properties'])
    if ctx.get('follow_up'):
        part['properties']['change_review']=integrity_followup.change_schema()
        part['required']=list(part['properties'])
    part_bound=max(sum(v['clause_ref']==cid for v in c['material_parts'].values()) for cid in c['clauses'])
    return obj(
        obligations=array(obj(clause_ref=clause,elements=obj(**{k:element for k in ELEMENTS})),24,1),
        packet_findings=array(obj(packet_ref=packet,obligation_ref=clause,status=enum(('supported','contradicted','absent','uncertain')),
            evidence_refs=array(cite,6),reasoning=string(),material=dict(type='boolean'),parts=array(part,part_bound,1)),96,1),
        differences=array(obj(classification=enum(DIFFERENCES),packet_refs=array(packet,4,1),obligation_ref=clause,
            consequence=string(),evidence_refs=array(cite,6),would_disprove=string(),material=dict(type='boolean')),12),
        options=array(obj(id=string(40),kind=enum(KINDS),action=string(),owner=dict(type=['string','null'],maxLength=100),
            retained_packets=array(packet,4),proposed_conditions=array(proposed,24 if c['declared_rules'] else 0),
            implementation=enum(('reported-existing','proposed','unknown')),evidence_refs=array(cite,6),
            support=enum(('supported','contradicted','uncertain')),hard_gate=enum(('passes','blocked','requires_authorized_requirement_change')),
            comparison=obj(**{k:string() for k in DIMENSIONS}),dependencies=array(string(),8),uncertainties=array(string(),8)),5,1),
        recommendation=obj(preferred_option=dict(type=['string','null'],maxLength=40),why=string(),conditions=array(string(),10),
            would_change_if=array(string(),10,1),requested_decision=string(),disposition=enum(('proposed','unresolved'))))


def packet_slots(ctx):
    c=context(ctx)
    pairs=[(p,k) for p,pv in c['packets'].items() for k,source in c['clauses'].items()
           if any(label(r)==label(source) for r in pv['requirements'])]
    return {'F'+str(i+1):dict(packet_ref=p,obligation_ref=k) for i,(p,k) in enumerate(sorted(pairs))}

def clause_passages(text):
    """Exact bounded source selections, without model rewriting or normalization."""
    spans=[]
    for part in re.split(r'(?<=[.;])\s+|\n+',text):
        value=part.strip()
        while value:
            end=len(value) if len(value)<=500 else value.rfind(' ',0,501)
            if end<=0:end=500
            spans.append(value[:end]);value=value[end:].strip()
    return list(dict.fromkeys(spans))


def wire_schema(ctx):
    """Required object keys make complete coverage part of the provider contract.

    Canonical saved traces remain lists. No interpretation or missing result is
    manufactured by normalization; every required result must come from the model.
    """
    out=deepcopy(schema(ctx));c=context(ctx)
    authority=ctx['required_authority']
    owners={authority.get('decider'),*authority.get('reviewers',[]),*authority.get('delegates',[]),*authority.get('escalation_path',[])}
    # Only name participants already supplied in this decision context. Unknown
    # owners remain unassigned; project membership is still checked on save.
    out['properties']['options']['items']['properties']['owner']['enum']=[None,*sorted(owners-{None})]
    def obj(props):return dict(type='object',properties=props,required=list(props),additionalProperties=False)
    template=out['properties']['obligations']['items']['properties']['elements']
    element=next(iter(template['properties'].values()))
    definitions={};obligations={}
    for i,key in enumerate(sorted(c['clauses'])):
        passages=clause_passages(c['clauses'][key]['quote'])
        choices=[dict(type='null')]
        for status in ('specified','disputed'):
            value=deepcopy(element);props=value['properties'];props['status']['enum']=[status]
            props['interpretation']['minLength']=1
            props['quote']['enum']=passages if status=='specified' else ['',*passages]
            if status=='specified':props['quote']['minLength']=1
            choices.append(value)
        name='integrity_element_'+str(i);definitions[name]=dict(anyOf=choices)
        elements=deepcopy(template);elements['properties']={k:{'$ref':'#/$defs/'+name} for k in ELEMENTS}
        obligations[key]=obj(dict(elements=elements))
    finding=out['properties']['packet_findings']['items']['properties']['parts']['items']['properties']
    out['$defs']=definitions
    out['properties']['obligations']=obj(obligations)
    slots=packet_slots(ctx)
    for pid,p in c['packets'].items():
        claim_ids=integrity_parts.packet_citations(ctx,pid,c)
        choices={k:v for k,v in integrity_parts.quote_catalog(ctx,c).items() if v['citation_ref'] in claim_ids}
        # The model selects an exact located passage. Code copies that source
        # selection verbatim; it never repairs a generated quotation or judgment.
        variants=[]
        for state in ('supported','contradicted','absent','uncertain'):
            if state in ('supported','contradicted') and not choices:continue
            props={k:deepcopy(v) for k,v in finding.items() if k not in ('part_ref','evidence_refs')}
            if ctx.get('condition_inventory'):
                props.pop('claim_interpretation');props.pop('support_scope')
                rel=props['evidence_relationship']['properties']
                rel['relation']['enum']=list(integrity_relationship.RELATIONS[state])
                for key in ('missing_link','evidence_request'):
                    if state=='supported':rel[key]['enum']=['']
                    else:rel[key]['minLength']=1
                if state=='supported':rel['unstated_premise']['enum']=['']
                if state=='supported':props['entailment_check']['properties']['counterexample_possible']['enum']=[False]
            props['status']['enum']=[state]
            if state=='supported':props['interpretation']['properties']['state']['enum']=['settled']
            props['evidence_quotes']['items']=dict(type='string',enum=list(choices) or ['no-packet-evidence'])
            props['evidence_quotes']['maxItems']=4 if choices else 0
            if state in ('supported','contradicted') or ctx.get('condition_inventory') and state=='uncertain':props['evidence_quotes']['minItems']=1
            if state=='supported':props['remaining_gap']['enum']=['']
            else:props['remaining_gap']['minLength']=1
            # Source selection and explicit connection precede the grade on the wire.
            first=[k for k in ('evidence_quotes','evidence_relationship') if k in props]
            props={k:props[k] for k in [*first,*(k for k in props if k not in first)]}
            variants.append(obj(props))
        name='integrity_part_'+str(list(c['packets']).index(pid))
        out['$defs'][name]=dict(anyOf=variants)
        for slot,pair in slots.items():
            if pair['packet_ref']==pid:
                part_keys=[k for k,v in c['material_parts'].items() if v['clause_ref']==pair['obligation_ref']]
                pair['schema']=obj(dict(parts=obj({k:{'$ref':'#/$defs/'+name} for k in part_keys})))
    out['properties']['packet_findings']=obj({slot:pair['schema'] for slot,pair in slots.items()})
    return out


def normalize_wire(result,ctx):
    """Decode exact keys; preserve legacy/scripted canonical responses for tests."""
    out=deepcopy(result)
    if not isinstance(out,dict):return out
    if isinstance(out.get('obligations'),dict):
        expected=context(ctx)['clauses'];values=out['obligations']
        if set(values)!=set(expected):raise ValueError('Represent every selected governing clause exactly once, including unspecified elements.')
        if any(not isinstance(v,dict) or set(v)!={'elements'} for v in values.values()):raise ValueError('Invalid clause result.')
        out['obligations']=[dict(clause_ref=k,**values[k]) for k in expected]
        for o in out['obligations']:
            o['elements']={k:(dict(status='unspecified',quote='',interpretation='') if v is None else v) for k,v in o['elements'].items()}
    if isinstance(out.get('packet_findings'),dict):
        slots=packet_slots(ctx);values=out['packet_findings']
        if set(values)!=set(slots):raise ValueError('Assess each packet against each applicable clause before combining domains.')
        out['packet_findings']=[dict(**slots[k],**values[k]) for k in slots]
        for f in out['packet_findings']:
            if set(f)!={'packet_ref','obligation_ref','parts'} or not isinstance(f['parts'],dict):raise ValueError('Return part-level evidence; whole-clause support is computed by the application.')
            parts=[dict(part_ref=k,**v) for k,v in f['parts'].items()]
            selections=integrity_parts.quote_catalog(ctx,context(ctx))
            for part in parts:
                if ctx.get('condition_inventory') and any(k in part for k in ('claim_interpretation','support_scope')):
                    raise ValueError('Do not replace a frozen condition meaning or evidence scope in the grading response.')
                ids=part['evidence_quotes']
                if any(not isinstance(k,str) or k not in selections for k in ids):raise ValueError('Select an exact supplied evidence passage; no invented or rewritten quote.')
                part['evidence_quotes']=[{k:v for k,v in selections[key].items() if k in ('citation_ref','quote')} for key in ids]
                part['evidence_refs']=list(dict.fromkeys(q['citation_ref'] for q in part['evidence_quotes']))
                if ctx.get('condition_inventory'):
                    from .integrity_inventory import LEVELS
                    unit=context(ctx)['material_parts'].get(part['part_ref'])
                    if unit is None:raise ValueError('Grade only a condition in the frozen inventory.')
                    part['claim_interpretation']=unit['meaning']
                    part['support_scope']=LEVELS[ctx['evidence_level']]
            f.update(integrity_parts.parent(parts,context(ctx)['material_parts']))
    return out


def shape(value,spec,root=None):
    """Small strict validator for this closed schema, including non-OpenAI providers."""
    root=spec if root is None else root
    if '$ref' in spec:
        if not spec['$ref'].startswith('#/$defs/'):raise ValueError('Unsupported schema reference.')
        return shape(value,root['$defs'][spec['$ref'].split('/')[-1]],root)
    if 'anyOf' in spec:
        for candidate in spec['anyOf']:
            try:shape(value,candidate,root);return
            except ValueError:pass
        raise ValueError('Invalid option condition value.')
    types=spec['type'] if isinstance(spec['type'],list) else [spec['type']]
    actual='null' if value is None else 'boolean' if type(value) is bool else 'number' if type(value) in (int,float) else 'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object' if isinstance(value,dict) else 'invalid'
    if actual not in types:raise ValueError('Invalid decision trace value type.')
    if value is None:return
    if 'enum' in spec and value not in spec['enum']:raise ValueError('Unknown decision trace reference or state.')
    if actual=='object':
        if set(value)!=set(spec['required']):raise ValueError('Incomplete or extra decision trace fields.')
        for k,v in value.items():shape(v,spec['properties'][k],root)
    elif actual=='array':
        if not spec.get('minItems',0)<=len(value)<=spec['maxItems']:raise ValueError('Decision trace list exceeds its bounds.')
        for v in value:shape(v,spec['items'],root)
    elif actual=='string':
        if not spec.get('minLength',0)<=len(value)<=spec.get('maxLength',float('inf')):raise ValueError('Decision trace text exceeds its bounds.')
        if spec.get('minLength',0) and not value.strip():raise ValueError('Explain the decision trace judgment.')
    elif actual=='number':
        import math
        if not math.isfinite(value):raise ValueError('Use a finite option condition.')


def meets(rule,values):
    expected=rule['expected'];op=rule['operator']
    if not values:return False
    if op=='includes':return all(isinstance(v,list) for v in values) and set(expected)<=set(x for v in values for x in v)
    if op=='minimum':return all(type(v) in (int,float) and v>=expected for v in values)
    return all(type(v)==type(expected) and v==expected for v in values)


def validate(integrity,result,ctx,findings):
    shape(result,schema(ctx));out=deepcopy(result);c=context(ctx);catalog=ctx['citation_catalog']
    from .integrity_explanations import validate as explanations
    explanations(result)
    records={label(r['ref']):r for r in ctx['records']}
    allowed={reference(r) for r in ctx['manifest']['included']}
    def citations(ids):
        if ids:integrity.citations([catalog[k] for k in ids],allowed)
    def issue(key,title,effect,refs=(),origin='model'):
        return dict(key='options:'+key,title=title,classifications=['unresolved'],effect=effect,citations=[catalog[x] for x in refs],
            citation_validity='verified' if refs else 'no-passage-for-missing-information',support='unknown',
            support_verification='human-review-required',action='Inspect the exact sources; correct inputs or record a reasoned disposition and reassess where needed.',material=True,origin=origin)
    extra=[]
    if {o['clause_ref'] for o in out['obligations']}!=set(c['clauses']) or len(out['obligations'])!=len(c['clauses']):
        raise ValueError('Represent every selected governing clause exactly once, including unspecified elements.')
    for obligation in out['obligations']:
        source=catalog[obligation['clause_ref']];citations([obligation['clause_ref']])
        for name,e in obligation['elements'].items():
            if e['status']=='specified' and (not e['quote'] or e['quote'] not in source['quote']):raise ValueError('An explicit obligation element needs an exact passage from this governing clause.')
            if e['status']=='unspecified' and (e['quote'] or e['interpretation']):raise ValueError('Leave unspecified obligation elements empty; do not invent a condition.')
            if e['status']=='disputed' and (not e['interpretation'] or e['quote'] and e['quote'] not in source['quote']):raise ValueError('Explain a disputed element without inventing a passage.')
        obligation['source']=source;obligation['interpretation_status']='provisional; source remains authoritative'
    expected={(p,k) for p,pv in c['packets'].items() for k,source in c['clauses'].items() if any(label(r)==label(source) for r in pv['requirements'])}
    pairs=[(f['packet_ref'],f['obligation_ref']) for f in out['packet_findings']]
    if len(set(pairs))!=len(pairs) or set(pairs)!=expected:raise ValueError('Assess each packet against each applicable clause before combining domains.')
    for n,f in enumerate(out['packet_findings']):
        citations(f['evidence_refs'])
        if f['status'] in ('supported','contradicted') and not f['evidence_refs']:raise ValueError('A supported or contradicted claim needs evidence.')
        if f['status'] in ('supported','contradicted'):
            if not set(f['evidence_refs']) & set(integrity_parts.packet_citations(ctx,f['packet_ref'],c)):
                raise ValueError('Cite the selected packet claim as well as the governing basis; a requirement alone does not establish packet support.')
        integrity_parts.validate_finding(f,ctx,c)
        for part in f['parts']:
            citations(part['evidence_refs'])
            for q in part['evidence_quotes']:
                passage=catalog[q['citation_ref']];start=passage['quote'].index(q['quote'])
                q['verified_location']=dict(id=passage['id'],revision=passage['revision'],field=passage['field'],start=start,end=start+len(q['quote']))
                q['selection_ref']=next((key for key,value in integrity_parts.quote_catalog(ctx,c).items() if value['citation_ref']==q['citation_ref'] and value['quote']==q['quote']),None)
            part['source']=deepcopy(c['material_parts'][part['part_ref']])
            part['support_verification']='model-judgment-awaiting-human-review'
        f['status_derivation']=integrity_parts.VERSION
        f['support_verification']='model-judgment-awaiting-human-review'
        if f['material'] or f['status']=='contradicted':extra.append(issue('packet:'+f['packet_ref']+':'+f['obligation_ref'],'Packet interpretation needs a decision',f['reasoning'],[f['obligation_ref'],*f['evidence_refs']]))
    for n,d in enumerate(out['differences']):
        citations(d['evidence_refs'])
        if len(set(d['packet_refs']))!=len(d['packet_refs']):raise ValueError('Use distinct packet references.')
        if d['material']:extra.append(issue('difference:'+str(n),'Consequential difference — '+d['classification'],d['consequence']+' Evidence that would resolve it: '+d['would_disprove'],[d['obligation_ref'],*d['evidence_refs']]))
    from .integrity_grounding import disagreements
    conflicts=disagreements(ctx,out['packet_findings'])
    out['consistency']=dict(status='unresolved' if conflicts else 'no-conflicting-repeated-statuses',conflicts=conflicts,
        boundary='Consistency is not correctness or independent corroboration. Shared judgments require model-confirmed applicability.')
    for n,conflict in enumerate(conflicts):
        extra.append(issue('consistency:'+str(n),'Repeated obligation needs semantic reconciliation',conflict['quote']+' has conflicting model judgments; no winner is inferred.',[j['clause_ref'] for j in conflict['judgments']],origin='deterministic'))
    ids=[o['id'] for o in out['options']]
    if len(set(ids))!=len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',v) for v in ids):raise ValueError('Use distinct simple option IDs.')
    members=set(integrity.w.rights.members)
    rule_conflict=any(f['key'].startswith('anchor-conflict:') for f in findings)
    incomplete=bool(ctx['manifest']['omitted'] or ctx['manifest']['unavailable'])
    for option in out['options']:
        citations(option['evidence_refs'])
        if option['owner'] is not None and option['owner'] not in members:raise ValueError('Use a known decision participant or leave the owner unassigned.')
        if len(set(option['retained_packets']))!=len(option['retained_packets']):raise ValueError('Do not duplicate a retained packet.')
        if option['kind']=='retain' and option['proposed_conditions']:raise ValueError('Retaining packets cannot silently change their declared conditions.')
        proposed={v['rule']:v['value'] for v in option['proposed_conditions']}
        if len(proposed)!=len(option['proposed_conditions']):raise ValueError('Declare an option condition once.')
        rule_results=[]
        for rid,rule in c['declared_rules'].items():
            values=[]
            for pid in option['retained_packets']:
                e=records[label(c['packets'][pid]['expression'])]['body']
                f=e['facts'].get(rule['key'])
                if rule['requirement'] in e['requirements'] and f:values.append(f['value'])
            if rid in proposed:values=[proposed[rid]]
            rule_results.append(dict(rule=rid,result='covered-by-declaration' if meets(rule,values) else 'not-established',values=values))
        deliberation=option['kind'] in ('investigate','escalate')
        reasons=[];gate=option['hard_gate']
        if option['kind']=='amend-requirement':gate='requires_authorized_requirement_change';reasons.append('A separate named human requirement decision is required.')
        elif not option['owner']:
            gate='blocked';reasons.append('No accountable owner is assigned.')
        elif not deliberation:
            if conflicts:reasons.append('Repeated obligations have unresolved model judgments; reconcile their scope and evidence before substantive reliance.')
            if not c['declared_rules']:reasons.append('No explicit owner-declared conditions establish this substantive option; clarify the governing basis.')
            if any(records[label(r)]['body'].get('status')!='approved' for r in ctx['requirements']):reasons.append('A selected governing requirement is not approved.')
            if rule_conflict:reasons.append('Current governing declarations conflict; no precedence is inferred.')
            if incomplete:reasons.append('Selected context has omissions or access limitations.')
            if not option['owner']:reasons.append('No accountable owner is assigned.')
            if any(r['result']=='not-established' for r in rule_results):reasons.append('The option does not establish every declared governing condition.')
            if option['support']=='contradicted':reasons.append('The option reports contrary evidence.')
            if reasons:gate='blocked'
        option.update(model_hard_gate=option['hard_gate'],hard_gate=gate,gate_reasons=reasons,declared_condition_results=rule_results,
            approval_eligible=False,approval_boundary='This is a proposed next action, not approval. Evidence support, implementation and the existing named review/ratification process remain separate.')
        if not deliberation and (option['implementation']!='reported-existing' or option['support']!='supported' or not option['evidence_refs']):
            option['uncertainties'].append('Implementation and evidential support must be verified before this can support acceptance.')
    rec=out['recommendation'];preferred=next((o for o in out['options'] if o['id']==rec['preferred_option']),None)
    if rec['preferred_option'] is not None and preferred is None:raise ValueError('The recommended option must be one of the recorded alternatives.')
    rec['model_preferred_option']=rec['preferred_option']
    if preferred and preferred['hard_gate']!='passes':
        extra.append(issue('gate','The preferred option did not pass its hard gates','The model preference cannot authorize this option. '+ '; '.join(preferred['gate_reasons']),origin='deterministic'))
        rec['preferred_option']=None;rec['disposition']='unresolved';preferred=None
    if incomplete:
        rec['conditions'].append('The context is incomplete. Resolve the listed source or access limitations before a substantive acceptance judgment.')
    for conflict in conflicts:rec['conditions'].append('Resolve differing model judgments for: '+conflict['quote'])
    rec['authority']=deepcopy(ctx['required_authority'])
    rec['approval']='not-granted'
    if preferred:
        # Critical limits cannot disappear into a prose-only model summary.
        rec['conditions']=list(dict.fromkeys([*rec['conditions'],*preferred['uncertainties']]))
        heading='Investigate before deciding' if preferred['kind']=='investigate' else 'Seek an authorized resolution' if preferred['kind']=='escalate' else 'Conditional next step' if rec['conditions'] else 'Proposed next step'
        summary=heading+': '+preferred['action']
    else:summary='The choice remains unresolved. '+rec['requested_decision']
    # Preserve the model's basis, including whole-solution uncertainty, even when
    # clause coverage has no gaps or a bounded next action is preferred. This is
    # lossless carriage, never an application-authored confidence judgment.
    summary+='\nReview basis: '+rec['why']
    summary=integrity_recommendation.project(out,summary,{p:records[label(v['expression'])]['body']['label'] for p,v in c['packets'].items()})
    if conflicts:summary+='\nUnresolved model disagreement: '+'; '.join(c['quote'] for c in conflicts)
    # Keep the displayed difference finding consistent with its complete closure
    # checklist, including gaps the model's short would_disprove prose omitted.
    for n,d in enumerate(out['differences']):
        for finding in extra:
            if finding['key']=='options:difference:'+str(n):
                finding['effect']=d['consequence']+' Evidence that would resolve it: '+d['would_disprove']
    if not preferred or rec['disposition']=='unresolved' or rec['conditions'] or preferred['kind'] in ('investigate','escalate'):
        extra.append(issue('recommendation','The recommendation remains conditional',rec['requested_decision']+' '+ ' '.join(rec['conditions']),origin='deterministic'))
    out.update(version=VERSION,mode=ctx['mode'],scope=ctx['evaluation_scope'],domains=ctx['domains'],intended_use=c['intended_use'],
        context_parts=deepcopy(c['context_parts']),review_projection=c['review_projection'],
        input_manifest=deepcopy(ctx['manifest']),summary=summary,support_boundary='Source locations and declared-condition gates are checked in code. Semantic support is a provisional model judgment for named human review, not independently verified truth.')
    return out,extra
