"""Validate a model's explicit evidence connection, never infer its semantics."""
from .integrity_explanations import explanation

VERSION = 'evidence-relationship-v1'
RELATIONS = {
    'supported': ('full',),
    'contradicted': ('incompatible',),
    'uncertain': ('partial', 'ambiguous'),
    'absent': ('adjacent-only', 'no-assertion'),
}
INSTRUCTIONS = '''EVIDENCE RELATIONSHIP RECORD: Before choosing a condition's grade,
complete evidence_relationship. required_relationship states the decisive relationship
while retaining every material actor, action, object, authority, scope and qualifier
from the frozen meaning; it cannot replace that meaning. source_assertion describes
only what the selected evidence_quotes actually assert. Those exact source references
are the record's evidence basis. connection explains whether that assertion covers
the same relationship fully, partially, ambiguously, incompatibly, or only an adjacent
topic; no-assertion is bounded to the inspected selection. unstated_premise records any
assumption needed to bridge them; leave it empty only when none is needed. A plausible
premise is a hunch to verify, not necessary implication. missing_link and evidence_request
state the unresolved issue and a useful bounded request (both empty for supported).
Only full maps to supported; incompatible to contradicted; partial or ambiguous to
uncertain; adjacent-only or no-assertion to absent. Partial/ambiguous requires an exact
quote addressing the same relationship, not a shared noun. Report truncation/access
limits separately. The application checks this contract, not the truth of the model's
interpretation. Do not force closure, reopen settled scope or infer ratification.
CALIBRATION (conditional examples, never project evidence): manufacturer dispensation
without an asserted return-to-service relationship is adjacent-only/absent; a reassignment
audit marker without its reason is partial/uncertain; named billing/referral channel exclusions
without an asserted instruction-provision relationship are adjacent-only/absent; manufacturer
permission without a regulatory authority/sign-off relationship is adjacent-only/absent.
Additional evidence establishing those relationships may change these judgments.'''


def schema():
    text = lambda empty=False: dict(type='string', minLength=0 if empty else 1, maxLength=500)
    fields = dict(required_relationship=text(), source_assertion=text(),
                  relation=dict(type='string', enum=[r for rs in RELATIONS.values() for r in rs]),
                  connection=text(), unstated_premise=text(True), missing_link=text(True),
                  evidence_request=text(True))
    return dict(type='object', additionalProperties=False, required=list(fields), properties=fields)


def validate(part):
    from .integrity_options import shape
    receipt = part.get('evidence_relationship')
    shape(receipt, schema())
    for field, value in receipt.items():
        if field != 'relation' and value:
            explanation(value, 'evidence relationship '+field)
    if receipt['relation'] not in RELATIONS[part['status']]:
        raise ValueError('Grade disagrees with the stated evidence relationship.')
    if receipt['relation'] in ('full', 'partial', 'ambiguous', 'incompatible') and not part['evidence_quotes']:
        raise ValueError('A relevant evidence relationship requires exact source quotations.')
    if part['status'] == 'supported':
        if any(receipt[k] for k in ('unstated_premise', 'missing_link', 'evidence_request')):
            raise ValueError('Full support cannot depend on an unstated premise or unresolved link.')
    else:
        for k in ('missing_link', 'evidence_request'):
            explanation(receipt[k], 'evidence relationship '+k)
