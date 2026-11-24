"""Append-only, human recorded requirement assessments. No model or network calls.

Checks establish the record contract and exact citations, not semantic sufficiency.
Assessment, authority, evidence confidence and delivered fulfillment remain distinct.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import re

from .core import Ref, StaleBasis
from .decisions import SCOPE, now, fingerprint
from .validation import reference


STANDARD_PATH = Path(__file__).with_name('config') / 'requirement_assessment_profiles.v1.json'
INVENTORY_KIND = 'requirement-condition-inventory'
ASSESSMENT_KIND = 'requirement-assessment'
STANDARD_KIND = 'requirement-assessment-standard'
INTERNAL_KINDS = {INVENTORY_KIND, ASSESSMENT_KIND, STANDARD_KIND}
STATUSES = {'not-assessed': 'Not assessed', 'needs-work': 'Needs work',
            'suitable': 'Suitable for this use', 'needs-reassessment': 'Needs reassessment'}
JUDGMENTS = {'met': 'Met', 'partial': 'Partial', 'missing': 'Missing', 'uncertain': 'Uncertain',
             'contradicted': 'Contradicted', 'not-assessed': 'Not assessed',
             'not-applicable': 'Not applicable'}
EVIDENCE_LEVELS = {'documentary': 'Documented statement', 'authoritative': 'Authoritative obligation',
                   'observed': 'Observed behavior', 'runtime': 'Runtime/test evidence',
                   'outcome': 'Delivered outcome evidence'}
SOURCE_KINDS = {'source', 'intake-source', 'evidence', 'policy', 'intent', 'contribution',
                'knowledge-card', 'domain-brief', 'domain-deliverable', 'requirement',
                'goal', 'success-measure', 'intake-case', 'project-context'}
BOUNDARY = ('Human recorded assessment; not a ratification, execution authorization or fulfillment result. '
            'Exact-reference and contract validation do not prove semantic sufficiency or inventory completeness.')
PLACEHOLDERS = {'todo', 'tbd', 'n/a', 'na', 'none', 'unknown', 'placeholder', 'test', 'yes', 'no',
                'reason', 'rationale', 'explanation', 'pending', 'not applicable', 'not assessed'}


def standard():
    return json.loads(STANDARD_PATH.read_text())


def standard_ref(profile=None):
    profile = profile or standard()
    return dict(id=profile['id'], revision=profile['revision'])


def text(data, key, maximum=3000):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'Provide {key.replace("_", " ")} within {maximum} characters')
    value = value.strip()
    if value.casefold().strip(' .!?') in PLACEHOLDERS or re.fullmatch(r'[.\-?\s]+', value):
        raise ValueError(f'Explain {key.replace("_", " ")} rather than enter a placeholder')
    return value


def packed(record):
    return dict(ref=asdict(record['ref']), kind=record['kind'], scope=record['scope'], body=deepcopy(record['body']))


def distinct_refs(refs):
    return list(dict.fromkeys(refs))


class RequirementAssessments:
    def __init__(self, workspace):
        self.w, self.store = workspace, workspace.store

    def _member(self):
        self.w.rights.live_member(self.w.actor)

    def _reader(self):
        if not self.w.is_admin:
            self._member()

    def _latest(self, id):
        row = self.store.db.execute('SELECT MAX(revision) FROM records WHERE id=?', (id,)).fetchone()
        return self.store.read(Ref(id, row[0]), {SCOPE}) if row[0] else None

    def _requirement(self, raw, current=False):
        row = self.store.read(reference(raw), {SCOPE})
        if row['kind'] != 'requirement':
            raise ValueError('Choose a published requirement version')
        if current and self.store.latest(row['ref'].id, {SCOPE})['ref'] != row['ref']:
            raise StaleBasis('The requirement changed. Reopen its current version before recording an assessment.')
        return row

    def _source(self, raw, current=False):
        row = self.store.read(reference(raw), {SCOPE})
        if row['kind'] not in SOURCE_KINDS:
            raise ValueError('Use a shared source, requirement or published contribution as evidence')
        if current and self.store.latest(row['ref'].id, {SCOPE})['ref'] != row['ref']:
            raise StaleBasis('A selected source changed. Review and select its current version.')
        return row

    def _citation(self, data, current=False, level=False):
        if not isinstance(data, dict):
            raise ValueError('Provide an exact source citation')
        source = self._source(data.get('ref'), current)
        field = text(data, 'field', 160)
        value = source['body']
        # Only JSON fields, never attributes or evaluated paths.
        for part in field.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
                value = value[int(part)]
            else:
                value = None
                break
        quote = data.get('quote')
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 4000 or not isinstance(value, str) or quote not in value:
            raise ValueError('The quotation must be an exact passage in the selected source field')
        out = dict(ref=asdict(source['ref']), field=field, quote=quote)
        if level:
            claimed = data.get('level')
            if claimed not in EVIDENCE_LEVELS:
                raise ValueError('Choose the evidence level this source actually records')
            # A passage always documents a statement. Stronger claims need an
            # existing explicitly typed evidence record; a request cannot upgrade it.
            if claimed != 'documentary' and source['body'].get('evidence_level') != claimed:
                raise ValueError('This source does not record that evidence level; a document is not runtime or outcome proof')
            out['level'] = claimed
        return out

    def _standard(self, raw, persist=False):
        profile = standard()
        if raw != standard_ref(profile):
            raise StaleBasis('The assessment standard changed. Review the current standard.')
        if persist:
            saved = self._latest(profile['id'])
            if saved is None:
                if profile['revision'] != 1:
                    raise StaleBasis('The preceding standard snapshot must be retained before appending its successor.')
                self.store.put(profile['id'], STANDARD_KIND, SCOPE, profile)
            elif saved['kind'] == STANDARD_KIND and profile['revision'] == saved['ref'].revision + 1:
                self.store.put(profile['id'], STANDARD_KIND, SCOPE, profile, saved['ref'].revision)
            elif saved['ref'] != reference(raw) or saved['kind'] != STANDARD_KIND or saved['body'] != profile:
                raise StaleBasis('The saved assessment standard differs. A new standard version must be reviewed.')
        return profile

    def _inventory(self, raw, current=False):
        row = self.store.read(reference(raw), {SCOPE})
        if row['kind'] != INVENTORY_KIND:
            raise ValueError('Choose a frozen material-condition inventory')
        if current and self.store.latest(row['ref'].id, {SCOPE})['ref'] != row['ref']:
            raise StaleBasis('The inventory changed. Reopen its current version.')
        return row

    def freeze(self, data):
        self._member()
        if not isinstance(data, dict):
            raise ValueError('Provide the material-condition inventory')
        with self.store.transaction():
            req = self._requirement(data.get('requirement'), True)
            profile = self._standard(data.get('standard'))
            inventory_id = 'RINV-' + req['ref'].id
            previous = self._latest(inventory_id)
            if data.get('expected') != (asdict(previous['ref']) if previous else None):
                raise StaleBasis('The frozen inventory changed. Reopen it before saving another version.')
            supplied = data.get('material_conditions')
            if not isinstance(supplied, list) or not 1 <= len(supplied) <= 60:
                raise ValueError('Define between one and sixty material conditions before grading')
            conditions, keys = [], set()
            for condition in supplied:
                if not isinstance(condition, dict):
                    raise ValueError('Provide each material condition')
                key = text(condition, 'key', 80)
                if key in keys or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', key):
                    raise ValueError('Give each material condition a unique stable key')
                keys.add(key)
                source = self._citation(condition.get('source'), True)
                if source['ref'] != asdict(req['ref']) or source['field'] not in {'text', 'acceptance_criteria', 'conditions'}:
                    raise ValueError('Each material condition must identify its exact requirement clause')
                required_level = condition.get('required_evidence_level')
                if required_level not in EVIDENCE_LEVELS:
                    raise ValueError('Choose the required evidence level for every material condition')
                dependencies = condition.get('dependencies', [])
                if not isinstance(dependencies, list) or len(dependencies) > 12:
                    raise ValueError('Use at most twelve exact dependencies per condition')
                deps = distinct_refs(self._source(raw, True)['ref'] for raw in dependencies)
                conditions.append(dict(key=key, source=source,
                    expected_observation=text(condition, 'expected_observation'),
                    applicability=text(condition, 'applicability'), required_evidence_level=required_level,
                    consequence=text(condition, 'consequence'), dependencies=[asdict(r) for r in deps]))
            body = dict(requirement=asdict(req['ref']), standard=standard_ref(profile),
                scope=text(data, 'scope'), applicability=text(data, 'applicability'),
                material_conditions=conditions, rationale=text(data, 'rationale'),
                previous=asdict(previous['ref']) if previous else None,
                actor=self.w.actor, principal=self.w.principal_id, at=now(),
                boundary=BOUNDARY,
                inventory_review='Human supplied material-clause inventory; semantic completeness is not established by schema validation.')
            self._standard(data['standard'], True)
            ref = self.store.put(inventory_id, INVENTORY_KIND, SCOPE, body,
                                 previous['ref'].revision if previous else 0)
            for basis in [req['ref'], reference(body['standard']),
                          *(reference(r) for c in conditions for r in c['dependencies'])]:
                self.store.depend(ref, basis, {SCOPE})
        return dict(ref=asdict(ref), message='Material conditions frozen. No assessment or approval has been recorded.')

    def _judgments(self, supplied, checks, requirement, material=False):
        if not isinstance(supplied, list) or len(supplied) != len(checks):
            raise ValueError('Record one judgment for every frozen condition and required use check')
        by_key = {c['key']: c for c in checks}
        results, seen = [], set()
        for item in supplied:
            if not isinstance(item, dict) or item.get('key') not in by_key or item['key'] in seen:
                raise ValueError('Every frozen condition must appear exactly once; do not omit a difficult check')
            key = item['key']; seen.add(key); check = by_key[key]
            status = item.get('status')
            if status not in JUDGMENTS:
                raise ValueError('Choose a supported condition judgment')
            rationale = text(item, 'rationale')
            citations = item.get('evidence', [])
            if not isinstance(citations, list) or len(citations) > 8:
                raise ValueError('Use at most eight exact citations per judgment')
            evidence = [self._citation(e, True, True) for e in citations]
            if status == 'not-applicable':
                if not material and not check.get('allow_not_applicable'):
                    raise ValueError('This required profile check cannot be waived as Not applicable')
                if not evidence:
                    raise ValueError('Not applicable needs a grounded applicability reason and exact evidence')
            if status == 'met':
                supporting = [e for e in evidence if e['level'] == check['required_evidence_level']]
                if material:
                    supporting = [e for e in supporting if e['ref']['id'] != requirement['id']]
                if not supporting:
                    raise ValueError('Met needs evidence at the required level; requirement wording alone does not support its own proposition')
            dependencies = [reference(e['ref']) for e in evidence]
            if material:
                dependencies += [reference(check['source']['ref']), *(reference(r) for r in check['dependencies'])]
            results.append(dict(key=key, status=status, rationale=rationale, evidence=evidence,
                                dependencies=[asdict(r) for r in distinct_refs(dependencies)]))
        return [next(r for r in results if r['key'] == c['key']) for c in checks]

    def record(self, data):
        self._member()
        if not isinstance(data, dict):
            raise ValueError('Provide the human assessment')
        if data.get('confirm') is not True:
            raise ValueError('Explicitly record this human assessment')
        with self.store.transaction():
            inventory = self._inventory(data.get('inventory'), True); ib = inventory['body']
            req = self._requirement(ib['requirement'], True)
            profile = self._standard(ib['standard'], True)
            if any(self._changed(raw) for c in ib['material_conditions'] for raw in c['dependencies']):
                raise StaleBasis('An inventory dependency changed. Review and freeze the updated basis first.')
            use = data.get('intended_use')
            if use not in profile['profiles']:
                raise ValueError('Choose investigation, a bounded prototype, or implementation')
            assessment_id = 'RASM-' + req['ref'].id + '-' + use
            previous = self._latest(assessment_id)
            if data.get('expected') != (asdict(previous['ref']) if previous else None):
                raise StaleBasis('An assessment was recorded meanwhile. Review it before saving another.')
            conditions = self._judgments(data.get('condition_judgments'), ib['material_conditions'], ib['requirement'], True)
            checks = profile['profiles'][use]['checks']
            uses = self._judgments(data.get('use_judgments'), checks, ib['requirement'])
            confidence = data.get('confidence')
            if not isinstance(confidence, dict) or confidence.get('level') not in {'not-rated', 'low', 'moderate', 'high'}:
                raise ValueError('Record an explicit scoped confidence judgment')
            confidence = dict(level=confidence['level'], **{k: text(confidence, k) for k in ('claim', 'scope', 'rationale', 'limits')})
            # Necessary consistency rules, never a semantic confidence calculator.
            if confidence['level'] in {'moderate', 'high'} and any(c['status'] == 'contradicted' for c in conditions):
                raise ValueError('Resolve the material contradiction before recording Moderate or High confidence')
            if confidence['level'] == 'moderate' and not any(c['status'] == 'met' for c in conditions):
                raise ValueError('Moderate confidence needs relevant support for the core proposition')
            if confidence['level'] == 'high' and (not any(c['status'] == 'met' for c in conditions) or
                    any(c['status'] not in {'met', 'not-applicable'} for c in conditions)):
                raise ValueError('High confidence needs covered material claims and explicit residual limits')
            acceptable = {'met', 'not-applicable'}
            suitable = all(c['status'] in acceptable for c in uses) and any(c['status'] == 'met' for c in uses)
            if use == 'implementation':
                suitable = suitable and all(c['status'] in acceptable for c in conditions) and any(c['status'] == 'met' for c in conditions)
            body = dict(requirement=ib['requirement'], inventory=asdict(inventory['ref']), standard=ib['standard'],
                intended_use=use, scope=ib['scope'], applicability=ib['applicability'],
                condition_judgments=conditions, use_judgments=uses,
                status='suitable' if suitable else 'needs-work', confidence=confidence,
                next_action=text(data, 'next_action'), rationale=text(data, 'rationale'),
                actor=self.w.actor, principal=self.w.principal_id, assessor_type='human', at=now(),
                previous=asdict(previous['ref']) if previous else None, boundary=BOUNDARY)
            ref = self.store.put(assessment_id, ASSESSMENT_KIND, SCOPE, body,
                                 previous['ref'].revision if previous else 0)
            dependencies = [req['ref'], inventory['ref'], reference(ib['standard']),
                            *(reference(r) for j in conditions + uses for r in j['dependencies'])]
            for basis in distinct_refs(dependencies):
                self.store.depend(ref, basis, {SCOPE})
        return dict(ref=asdict(ref), message='Human assessment recorded. Approval, execution permission and fulfillment are unchanged.')

    def _changed(self, raw):
        try:
            previous = reference(raw)
            self.store.read(previous, {SCOPE})
            current = self.store.latest(previous.id, {SCOPE})['ref']
        except (PermissionError, ValueError):
            return dict(reason='Required basis is unavailable', unavailable=True)
        return dict(previous=asdict(previous), current=asdict(current), reason='Recorded basis has a newer version') if previous != current else None

    def _safe(self, row):
        """Do not return copied quotations after access to their basis is lost."""
        refs = [row['body'].get('requirement')]
        if row['kind'] == INVENTORY_KIND:
            refs += [c['source']['ref'] for c in row['body']['material_conditions']]
            refs += [r for c in row['body']['material_conditions'] for r in c['dependencies']]
        if row['kind'] == ASSESSMENT_KIND:
            refs += [r for j in row['body']['condition_judgments'] + row['body']['use_judgments'] for r in j['dependencies']]
        if any(reason.get('unavailable') for r in refs if r and (reason := self._changed(r))):
            return dict(ref=asdict(row['ref']), kind=row['kind'], scope=SCOPE,
                        body=dict(access_limited=True, intended_use=row['body'].get('intended_use'),
                                  at=row['body'].get('at'), boundary='The current evidence basis cannot be verified.'))
        return packed(row)

    def _results(self, judgments, definitions, old_definitions, basis_changed=False):
        by_key = {j['key']: j for j in judgments}
        old = {c['key']: c for c in old_definitions}
        out = []
        for definition in definitions:
            key = definition['key']; saved = by_key.get(key)
            if saved is None:
                out.append(dict(key=key, status='not-assessed', rationale='This condition has not been assessed.',
                                evidence=[], stale=[], current=False, reusable=False))
                continue
            reasons = [reason for raw in saved['dependencies'] if (reason := self._changed(raw))]
            if old and old.get(key) != definition:
                reasons.append(dict(reason='This material condition changed'))
            if basis_changed:
                reasons.append(dict(reason='The applicable context or assessment standard changed'))
            unavailable = any(r.get('unavailable') for r in reasons)
            value = deepcopy(saved) if not unavailable else dict(key=key, status='not-assessed',
                rationale='The current evidence basis cannot be verified.', evidence=[])
            value.update(stale=reasons, current=not reasons, reusable=not reasons)
            out.append(value)
        return out

    @staticmethod
    def _coverage(results):
        counts = dict(total=0, checked=0, supported=0, unresolved=0, contradicted=0, unchecked=0, excluded=0)
        for result in results:
            status = result['status'] if result.get('current') else 'not-assessed'
            if status == 'not-applicable':
                counts['excluded'] += 1
                continue
            counts['total'] += 1
            if status == 'not-assessed':
                counts['unchecked'] += 1
            else:
                counts['checked'] += 1
                counts['supported' if status == 'met' else 'contradicted' if status == 'contradicted' else 'unresolved'] += 1
        return counts

    def business_intent_basis(self, raw):
        """Project the exact already-shared direction review, never a new grade.

        Requirements pin the reviewed case revision, which commonly precedes its
        later published case revision. Do not borrow that newer case's content or
        private intake/change analysis to fill a missing historical conclusion.
        """
        if not raw:
            return None
        try:
            case = self.store.read(reference(raw), {SCOPE})
        except (ValueError, PermissionError):
            return None
        if case['kind'] != 'intake-case':
            return None
        body = case['body']; snapshot = body.get('snapshot')
        if not isinstance(snapshot, dict):
            return None
        values = snapshot.get('values') or {}
        acceptance = snapshot.get('value_acceptance') or {}
        if not isinstance(values, dict) or not isinstance(acceptance, dict):
            return None

        def bounded(value, maximum=1500):
            return value[:maximum] if isinstance(value, str) else ''

        def shortened(value, maximum=1500):
            return isinstance(value, str) and len(value) > maximum

        reviews = []
        reviewers = body.get('reviewers')
        complete = isinstance(reviewers, list) and 0 < len(reviewers) <= 20
        if complete:
            for actor in reviewers:
                try:
                    review = self.store.read(reference((body.get('reviews') or {}).get(actor)), {SCOPE})
                except (ValueError, PermissionError):
                    complete = False
                    continue
                rb = review['body']
                if (review['kind'] != 'intake-assessment' or rb.get('actor') != actor or
                        rb.get('snapshot_fingerprint') != fingerprint(snapshot) or
                        rb.get('disposition') not in {'ready-for-investigation', 'changes-requested'}):
                    complete = False
                    continue
                reviews.append(dict(ref=asdict(review['ref']), actor=actor,
                    disposition=rb['disposition'], rationale=bounded(rb.get('rationale')),
                    rationale_truncated=shortened(rb.get('rationale')), at=rb.get('at')))
        dispositions = [r['disposition'] for r in reviews]
        disposition = ('changes-requested' if 'changes-requested' in dispositions else
                       'ready-for-investigation' if complete and all(d == 'ready-for-investigation' for d in dispositions) else None)
        matched = None
        for row in self.store.db.execute("SELECT id,revision FROM records WHERE kind='intent' AND scope=? ORDER BY rowid DESC", (SCOPE,)):
            intent = self.store.read(Ref(row['id'], row['revision']), {SCOPE})
            if intent['body'].get('source_case') == asdict(case['ref']) and intent['body'].get('text') == values.get('value'):
                matched = intent
                break
        intent_status = {key: matched['body'].get(key) for key in ('status', 'fit_status', 'evidence_status', 'execution')} if matched else None
        acceptance_rationale = acceptance.get('rationale')
        walkthrough = next((value for value in [acceptance_rationale, *(r['rationale'] for r in reviews)]
                            if isinstance(value, str) and re.search(r'walkthrough|enacted|not actual', value, re.I)), None)
        draft_ref = body.get('source_draft')
        try:
            draft_ref = asdict(reference(draft_ref))
        except ValueError:
            draft_ref = None
        return dict(case_ref=asdict(case['ref']), source_draft_ref=draft_ref,
            published_intent_ref=asdict(matched['ref']) if matched else None,
            published_intent_status=intent_status,
            source_current=self.store.latest(matched['ref'].id, {SCOPE})['ref'] == matched['ref'] if matched else None,
            review_disposition=disposition, review_basis_complete=complete, reviews=reviews,
            value_acceptance_status=acceptance.get('status'),
            value_proposition=bounded(values.get('value')), value_proposition_truncated=shortened(values.get('value')),
            open_questions=bounded(values.get('open_questions')), open_questions_truncated=shortened(values.get('open_questions')),
            limits=dict(constraints=bounded(values.get('constraints')), out_scope=bounded(values.get('out_scope'))),
            limits_truncated=dict(constraints=shortened(values.get('constraints')), out_scope=shortened(values.get('out_scope'))),
            acceptance_rationale=bounded(acceptance_rationale), acceptance_rationale_truncated=shortened(acceptance_rationale),
            walkthrough_limitation=bounded(walkthrough), walkthrough_limitation_truncated=shortened(walkthrough),
            context='Recorded Business Intent conclusion for this exact basis; separate from the requirement assessment.')

    def _new_evidence(self, requirement_id, assessed_at):
        """D012: shared work published after a rating prompts reassessment; the rating itself is kept."""
        if not assessed_at:
            return []
        newer = []
        for row in self.store.db.execute(
                "SELECT id,MAX(revision) revision FROM records WHERE kind='contribution' AND scope=? GROUP BY id", (SCOPE,)):
            body = self.store.read(Ref(row['id'], row['revision']), {SCOPE})['body']
            if str(body.get('published_at') or '') > str(assessed_at) and any(
                    isinstance(r, dict) and r.get('id') == requirement_id for r in body.get('requirement_refs') or []):
                newer.append(dict(id=row['id'], revision=row['revision']))
        return [dict(reason='New shared evidence since this rating', contributions=newer)] if newer else []

    def _item(self, req):
        current_profile = standard(); profile = current_profile
        inventory = self._latest('RINV-' + req['ref'].id)
        if inventory:
            try:
                profile = self.store.read(reference(inventory['body']['standard']), {SCOPE})['body']
            except PermissionError:
                pass
        history = []
        ids = ['RASM-' + req['ref'].id + '-' + use for use in profile['profiles']]
        for row in self.store.db.execute('SELECT id,revision FROM records WHERE kind=? AND scope=? AND id IN (?,?,?) ORDER BY rowid DESC', (ASSESSMENT_KIND, SCOPE, *ids)):
            record = self.store.read(Ref(row['id'], row['revision']), {SCOPE})
            if record['body']['requirement']['id'] == req['ref'].id:
                history.append(record)
        uses = {}
        for use, config in profile['profiles'].items():
            assessment = next((r for r in history if r['body']['intended_use'] == use), None)
            empty = dict(status='not-assessed', current=None, confidence=dict(level='not-rated'),
                         stale=[], condition_results=[], use_results=[], reassess=[])
            if inventory is None or assessment is None:
                if inventory:
                    empty['condition_results'] = [dict(key=c['key'], status='not-assessed',
                        rationale='This condition has not been assessed.', evidence=[], stale=[], current=False, reusable=False)
                        for c in inventory['body']['material_conditions']]
                uses[use] = empty
                continue
            body = assessment['body']; old = self._inventory(body['inventory'])
            changed_profile = body['standard'] != standard_ref(profile) or standard_ref(profile) != standard_ref(current_profile)
            try:
                saved_standard = self.store.read(reference(body['standard']), {SCOPE})
                changed_profile = changed_profile or saved_standard['body'] != current_profile
            except PermissionError:
                changed_profile = True
            context_changed = any(old['body'][key] != inventory['body'][key] for key in ('scope', 'applicability'))
            conditions = self._results(body['condition_judgments'], inventory['body']['material_conditions'],
                                       old['body']['material_conditions'], changed_profile or context_changed)
            checks = self._results(body['use_judgments'], config['checks'], [], changed_profile or context_changed)
            reasons = [r for result in conditions + checks for r in result['stale']]
            if body['requirement'] != asdict(req['ref']):
                reasons.append(dict(reason='The requirement version changed', previous=body['requirement'], current=asdict(req['ref'])))
            if body['inventory'] != asdict(inventory['ref']):
                reasons.append(dict(reason='The frozen inventory version changed', previous=body['inventory'], current=asdict(inventory['ref'])))
            status = 'needs-reassessment' if reasons else body['status']
            confidence = dict(level='not-rated', rationale='The saved assessment needs reassessment.') if reasons else deepcopy(body['confidence'])
            uses[use] = dict(status=status, current=self._safe(assessment), confidence=confidence,
                             stale=reasons, condition_results=conditions, use_results=checks,
                             reassess=self._new_evidence(req['ref'].id, body.get('at')))
        recent = next((r for r in history), None)
        coverage = self._coverage(uses[recent['body']['intended_use']]['condition_results']) if recent else self._coverage(
            next(iter(uses.values()))['condition_results'])
        return dict(requirement=asdict(req['ref']), inventory=self._safe(inventory) if inventory else None,
                    history=[self._safe(r) for r in history], uses=uses, coverage=coverage,
                    business_intent_basis=self.business_intent_basis(req['body'].get('intake_case')),
                    boundary=BOUNDARY)

    def read(self, data):
        self._reader()
        return self._item(self._requirement(data.get('requirement'), True))

    def guidance(self, requirement=None):
        """Bounded advice context, never a grading call or a release of private work."""
        profile = standard()
        out = dict(standard=dict(ref=standard_ref(profile), body=profile), boundary=BOUNDARY,
            rules=[
                'A shell or clear statement is not evidence that a proposition is true.',
                'Apply the named-use checks; do not require every requirement to visit every domain.',
                'An authoritative obligation is distinct from an empirical hypothesis.',
                'A document supports documentary statements, not an unobserved runtime or outcome claim.',
                'Confidence is Not rated until explicitly assessed; never infer it from reports, fields or approval.',
                'Advice does not record an assessment or change ratification, authority or fulfillment.',
                'Schema checks cannot establish semantic sufficiency or complete material-clause coverage.',
                'This is selected-field advice. Omitted conditions, gaps or shortened passages prohibit a whole-requirement completeness or suitability judgment; explain the partial context.'])
        saved_standard = self._latest(profile['id'])
        if saved_standard and asdict(saved_standard['ref']) == standard_ref(profile) and saved_standard['body'] != profile:
            out.update(standard=dict(ref=asdict(saved_standard['ref']), body=deepcopy(saved_standard['body'])),
                       limitation='The configured standard conflicts with its saved version. No current suitability judgment can be made until its owner supplies a new version.')
            return out
        if not isinstance(requirement, dict) or requirement.get('kind') != 'requirement' or requirement.get('scope') != SCOPE:
            return out
        self._reader()
        raw = requirement.get('ref')
        req = self._requirement(asdict(raw) if isinstance(raw, Ref) else raw)
        if self.store.latest(req['ref'].id, {SCOPE})['ref'] != req['ref']:
            out.update(requirement=asdict(req['ref']),
                       limitation='Historical requirement selected; current inventory and assessment recommendations are not supplied for this older version.')
            return out
        item = self._item(req)
        out['requirement'] = asdict(req['ref'])
        inventory = item['inventory']
        if inventory and not inventory['body'].get('access_limited'):
            body = inventory['body']; conditions = body['material_conditions']
            out['inventory'] = dict(ref=inventory['ref'], standard=body['standard'],
                scope=body['scope'][:1000], applicability=body['applicability'][:1000],
                condition_count=len(conditions), omitted_condition_count=max(0, len(conditions)-20),
                material_conditions=[dict(key=c['key'], source=dict(ref=c['source']['ref'],
                    field=c['source']['field'], quote=c['source']['quote'][:600],
                    quote_truncated=len(c['source']['quote']) > 600),
                    expected_observation=c['expected_observation'][:500],
                    expected_observation_truncated=len(c['expected_observation']) > 500,
                    required_evidence_level=c['required_evidence_level']) for c in conditions[:20]])
        out['assessments'] = {}
        for use, value in item['uses'].items():
            gaps = [dict(key=result['key'], inventory=kind, status=result['status'],
                rationale=result['rationale'][:500], rationale_truncated=len(result['rationale']) > 500,
                needs_reassessment=bool(result['stale']))
                for kind, results in [('material', value['condition_results']), ('intended-use', value['use_results'])]
                for result in results if result['status'] not in {'met', 'not-applicable'} or result['stale']]
            out['assessments'][use] = dict(status=value['status'],
                assessment=value['current']['ref'] if value['current'] else None,
                confidence=value['confidence']['level'], needs_reassessment=bool(value['stale']),
                gaps=gaps[:12], gap_count=len(gaps), omitted_gap_count=max(0, len(gaps)-12))
        return out

    def state(self):
        profile = standard()
        try:
            self._member()
            can_record = True
        except PermissionError:
            can_record = False
        # No records are created by discovery or by an ordinary page read.
        items = {r['ref'].id: self._item(r) for r in self.w.latest_records('requirement') if r['scope'] == SCOPE} if can_record or self.w.is_admin else {}
        standards = [dict(ref=standard_ref(profile), body=profile)]
        conflict = False
        for row in self.store.db.execute('SELECT id,revision FROM records WHERE kind=? AND scope=? ORDER BY revision DESC', (STANDARD_KIND, SCOPE)):
            saved = self.store.read(Ref(row['id'], row['revision']), {SCOPE})
            if asdict(saved['ref']) != standard_ref(profile):
                standards.append(dict(ref=asdict(saved['ref']), body=deepcopy(saved['body'])))
            elif saved['body'] != profile:
                conflict = True
                standards[0] = dict(ref=asdict(saved['ref']), body=deepcopy(saved['body']))
        intent = next((r for r in self.w.latest_records('intent') if r['scope'] == SCOPE), None)
        legacy = self.business_intent_basis(intent['body'].get('source_case')) if intent and (can_record or self.w.is_admin) else None
        return dict(standards=standards, current_standard=None if conflict else standard_ref(profile),
                    standard_conflict=conflict, statuses=deepcopy(STATUSES),
                    judgments=deepcopy(JUDGMENTS), evidence_levels=deepcopy(EVIDENCE_LEVELS),
                    can_record=can_record and not conflict, items=items,
                    business_intent_basis=legacy, boundary=BOUNDARY)
