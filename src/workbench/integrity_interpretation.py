"""Model-authored meaning dispositions; application-enforced lossless carriage.

These are proposed readings and clarification requests, never human answers.
Evidence status, evidence level and the frozen inventory remain separate.
"""
from copy import deepcopy
from .integrity_explanations import explanation

VERSION = 'material-interpretation-disposition-v1'
INSTRUCTIONS = '''MEANING BEFORE ACTION: For every material condition, return an
explicit interpretation disposition separately from evidence status. A settled
reading means the supplied wording and context admit no unresolved material
alternative for this use; it is your reviewable judgment, not human ratification.
Use conditional when a bounded reading is usable provisionally but another
material reading changes the judgment or permitted action. Use clarification-required
when choosing the meaning requires an authorized answer before that dependent
action. Preserve the frozen condition; never silently narrow or rewrite it.
For either unresolved state, give the material alternative and its consequence,
one specific meaning question, the responsible role, the dependent action and a
testable release condition. Request evidence separately in remaining_gap. An
evidence shortage alone is not a language ambiguity. Do not invent a human answer,
permission, resolved interpretation or governing amendment. Never mark a condition
supported while its meaning is conditional or clarification-required; retain
partial supporting quotations and state uncertainty. Low evidence confidence does
not itself forbid a bounded investigation or prototype; specify what can proceed
and what depends on clarification. Clarification does not prove implementation.'''

def schema():
    def text():return dict(type='string',minLength=1,maxLength=500)
    def obj(**p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
    return obj(state=dict(type='string',enum=['settled','conditional','clarification-required']),
        reading=text(),basis=text(),alternatives=dict(type='array',maxItems=3,
            items=obj(reading=text(),consequence=text())),
        clarification=dict(anyOf=[dict(type='null'),obj(question=text(),owner_role=text(),
            dependent_action=text(),release_condition=text())]))

def validate(part):
    from .integrity_options import shape
    value=part.get('interpretation')
    shape(value,schema())
    for key in ('reading','basis'):explanation(value[key],'interpretation '+key)
    for alternative in value['alternatives']:
        for key,text in alternative.items():explanation(text,'alternative '+key)
    if value['state']=='settled':
        if value['alternatives'] or value['clarification'] is not None:
            raise ValueError('A settled interpretation cannot retain a material alternative or unanswered meaning question.')
    else:
        if not value['alternatives'] or value['clarification'] is None:
            raise ValueError('An unresolved interpretation needs its alternative, consequence and specific clarification route.')
        for key,text in value['clarification'].items():explanation(text,'clarification '+key)
        if part['status']=='supported':
            raise ValueError('Conditional or unresolved meaning cannot become unqualified support.')

def unresolved(findings):
    out=[]
    for finding in findings:
        for part in finding['parts']:
            value=part['interpretation']
            if value['state']=='settled':continue
            out.append(dict(key='I'+str(len(out)+1),packet_ref=finding['packet_ref'],
                obligation_ref=finding['obligation_ref'],part_ref=part['part_ref'],
                evidence_status=part['status'],interpretation=deepcopy(value),
                authority='Model request; no human answer or ratification recorded.'))
    return out

def project(out,summary):
    rec=out['recommendation'];items=unresolved(out['packet_findings'])
    rec['unresolved_interpretations']=items;rec['interpretation_version']=VERSION
    rec['interpretation_boundary']='Meaning decisions are model proposals. Clarification, evidence verification and authorized ratification are separate.'
    lines=[]
    for item in items:
        value=item['interpretation'];q=value['clarification']
        alternatives='; '.join(a['reading']+' — '+a['consequence'] for a in value['alternatives'])
        line=(f"{item['key']}. {value['state']}: {value['reading']} Alternative: {alternatives}. "
              f"Clarify: {q['question']} Role: {q['owner_role']}. Dependent action: {q['dependent_action']}. Release: {q['release_condition']}")
        item['text']=line;lines.append(line)
    if lines:
        rec['conditions'].extend(lines);rec['would_change_if'].extend(lines)
        summary+='\n\nUnresolved meaning ('+str(len(lines))+'):\n'+'\n'.join(lines)
    return summary
