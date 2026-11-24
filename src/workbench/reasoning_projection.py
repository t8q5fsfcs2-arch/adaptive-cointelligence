"""Small task views of exact records; canonical storage and lineage stay intact."""
from copy import deepcopy


def reasoning_record(record):
    view=deepcopy(record);body=view['body'];omitted=[]
    if record['kind']=='intent':
        if 'scaffold' in body:
            body.pop('scaffold');omitted.append('scaffold: taxonomy supplied separately from scoped requirements')
        brief=body.get('business_brief')
        if isinstance(brief,dict) and isinstance(body.get('intake'),dict):
            # Keep structured role cards; the other answers are already normalized
            # in intake, including framing, evidence and investment-case fields.
            roles=deepcopy(brief.get('answers',{}).get('q4'))
            body['business_brief']=dict(answers={'q4':roles}) if roles else {}
            omitted.append('business_brief: normalized answers supplied in intake; structured roles retained')
    if record['kind'] in {'goal','success-measure'}:
        spec=body.get('specification')
        if isinstance(spec,dict) and all(k in body and body[k]==v for k,v in spec.items()):
            body.pop('specification');omitted.append('specification: exact duplicate of body fields')
    if record['kind']=='need-context' and body.get('review_items'):
        for item in body['review_items']:item.pop('current_text',None)
        omitted.append('review_items.current_text: exact targets are supplied by reference; the saved comparison remains in the canonical record')
    if record['kind']=='bridge-issue' and 'observed_versions' in body:
        body.pop('observed_versions');omitted.append('observed_versions: audit snapshot remains in canonical issue')
    if omitted:view['context_projection']=dict(note='Selective task view; inspect the pinned canonical record for the complete structure and audit snapshot.',omitted=omitted)
    return view
