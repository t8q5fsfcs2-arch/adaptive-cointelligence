"""Reject empty/placeholder model explanations; do not infer their meaning."""
import re

PLACEHOLDERS={'na','none','null','nil','unknown','tbd','todo','pending','placeholder',
    'not applicable','not available','not provided','not supplied','no evidence',
    'missing','uncertain','absent','see above','same as above','to be determined','to do'}

def explanation(value,field='explanation'):
    if not isinstance(value,str):raise ValueError('Provide a substantive '+field+'.')
    words=' '.join(re.findall(r'[^\W\d_]+',value.casefold()))
    if sum(c.isalpha() for c in value)<3 or words in PLACEHOLDERS:
        raise ValueError('Placeholder '+field+' is not an explanation; supply the specific condition and evidence gap.')
    return value

def validate(value):
    fields={'reasoning','claim_interpretation','support_scope','remaining_gap','rationale',
        'coverage_rationale','meaning','why','requested_decision','consequence','would_disprove',
        'fidelity','evidence','workability','risk_and_change','effort_and_cost','explanation'}
    lists={'conditions','would_change_if','uncertainties','dependencies','omissions','source_limitations'}
    if isinstance(value,dict):
        for key,item in value.items():
            if key in fields and isinstance(item,str) and item:explanation(item,key)
            elif key in lists and isinstance(item,list):
                for text in item:
                    if isinstance(text,str):explanation(text,key)
            if isinstance(item,(dict,list)):validate(item)
    elif isinstance(value,list):
        for item in value:validate(item)
