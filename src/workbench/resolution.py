"""Shared progress is a projection of released records, never of private activity."""
from dataclasses import asdict


def shared_resolution(records, cases, impacts):
    contributions = [r for r in records if r['kind'] == 'contribution']
    result = {}
    for req in (r for r in records if r['kind'] == 'requirement'):
        id = req['ref'].id
        related = [c for c in cases if c['body']['target']['id'] == id]
        case = related[0] if related else None  # latest saved case first
        open_case = case and case['body']['status'] not in {'approved', 'rejected'}
        basis = case['body']['basis'] if case else []
        selected_ids = {r['id'] for r in basis}
        shared = [c for c in contributions if c['ref'].id in selected_ids or
                  any(r['id'] == id for r in c['body'].get('requirement_refs', []))]
        domains = []
        issues = []
        reviewers = case['body'].get('required_reviews') if case else None
        if not reviewers:
            counterpart = 'lee' if any(c['body']['domain']=='Design' for c in shared) else 'maya'
            reviewers = {'sam':'supported-with-limits',counterpart:'cleared-with-conditions'}
        for actor, support in sorted(reviewers.items(), key=lambda pair: {"sam":0,"lee":1,"maya":2}[pair[0]]):
            domain = {'sam':'Research','lee':'Design','maya':'Operations'}[actor]
            published = [c for c in shared if c['body']['domain'] == domain]
            reviewed = [r for r in basis if any(c['ref'].id == r['id'] for c in published)]
            response = case['reviews'].get(actor) if case else None
            if open_case and case['stale']:
                status = 'Basis changed — review again'
            elif response:
                status = ('Review supports proposal' if response['body']['disposition'] == support
                          else 'Concern needs resolution')
                if not open_case:
                    status = 'Prior ' + status[0].lower() + status[1:]
            else:
                status = 'Awaiting domain review' if open_case else (
                    'Contribution shared' if published else 'No linked contribution shared')
            if not published:
                issues.append(f'{domain}: link a published contribution')
            domains.append({'domain': domain, 'actor': actor, 'status': status,
                            'contributions': [asdict(c['ref']) for c in published],
                            'reviewed_versions': reviewed, 'response': response})
        intent_requests = [r for r in records if r['kind'] == 'intent-refinement' and r['body']['status'] in {'open', 'drafted', 'deferred'}
                           and (not r['body']['requirement_refs'] or any(x['id'] == id for x in r['body']['requirement_refs']))]
        if intent_requests:
            issues.append('Resolve the sponsor intent refinement affecting this requirement')
        if req['body']['status'] != 'approved':
            issues.append('Requirement approval is pending')
        if not req['body'].get('acceptance_criteria', '').strip():
            issues.append('Acceptance criteria need to be defined')
        if open_case:
            issues.append('Resolve the open proposal' if not case['stale'] else 'Refresh the changed review basis')
        if impacts.get(id):
            issues.append('Reassess changed requirement dependencies')
        # New publication is not silently treated as part of an older approval.
        approval = next((c for c in related if c['body']['status'] == 'approved'), None)
        if req['body']['status'] == 'approved' and shared:
            approved_basis = approval['body']['basis'] if approval else []
            if any(asdict(c['ref']) not in approved_basis for c in shared):
                issues.append('Assess contributions outside the recorded approval basis')
        result[id] = {'domains': domains, 'case': asdict(case['ref']) if case else None,
                      'case_status': case['body']['status'] if case else None,
                      'brief_considerations': issues,
                      'next_owner': case['body'].get('next_owner') if open_case else None,
                      'next_question': case['body'].get('next_question') if open_case else None}
    return result
