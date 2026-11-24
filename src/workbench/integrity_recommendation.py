"""Lossless projection of validated material gaps into the recommendation.

This preserves model-authored judgments; it neither invents missing assessments
nor proves semantic support. Completeness is derived after evidence validation.
"""
from copy import deepcopy

VERSION = 'complete-material-gap-recommendation-v2-open-outcomes'
CLOSURE = ('These gaps and affected blockers remain unresolved unless a relevant '
           'change supports a different reviewed judgment. Reassess affected claims '
           'when evidence, meaning or governing scope changes; resolution is not '
           'guaranteed. An authorized scope change does not make the old evidence '
           'sufficient. Completing a next action or accepting risk does not erase '
           'these findings or establish support or approval.')


def project(out, summary, packet_labels):
    from .integrity_interpretation import project as project_interpretations
    summary=project_interpretations(out,summary)
    rec = out['recommendation']
    gaps = []
    multiple_packets = len({f['packet_ref'] for f in out['packet_findings']}) > 1
    for finding in out['packet_findings']:
        for part in finding['parts']:
            if part['status'] == 'supported':
                continue
            # Source, status, citations and remaining_gap were validated already.
            gap = dict(key='G'+str(len(gaps)+1), packet_ref=finding['packet_ref'],
                       obligation_ref=finding['obligation_ref'], part_ref=part['part_ref'],
                       status=part['status'], source=deepcopy(part['source']),
                       evidence_refs=list(part['evidence_refs']), remaining_gap=part['remaining_gap'])
            label = packet_labels[finding['packet_ref']] + ' — ' if multiple_packets else ''
            state = {'uncertain':'Uncertain', 'absent':'Not supplied', 'contradicted':'Contrary evidence'}[part['status']]
            gap['text'] = f"{gap['key']}. {label}{state}: {part['remaining_gap']}"
            gaps.append(gap)
    rec['unresolved_material_gaps'] = gaps
    rec['coverage_version'] = VERSION
    if not gaps:
        return summary

    # Derived lists are bounded by the validated source parts, never by the
    # model's shorter prose/list limits. Repeated wording in distinct parts or
    # packets remains distinct; no clipping, salience selection or deduplication.
    lines = [g['text'] for g in gaps]
    rec['conditions'].extend([CLOSURE, *lines])
    rec['would_change_if'].extend([CLOSURE, *lines])
    for difference in out['differences']:
        relevant = [g for g in gaps if g['obligation_ref'] == difference['obligation_ref']
                    and g['packet_ref'] in difference['packet_refs']]
        if relevant:
            difference['model_would_disprove'] = difference['would_disprove']
            difference['unresolved_material_gap_keys'] = [g['key'] for g in relevant]
            difference['would_disprove'] += '\n' + CLOSURE + '\n' + '\n'.join(g['text'] for g in relevant)
    return summary + f'\n\nUnresolved material gaps ({len(gaps)}):\n' + '\n'.join(lines) + '\n' + CLOSURE
