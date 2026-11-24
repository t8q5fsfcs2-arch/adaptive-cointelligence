"""Versioned sponsor intake and explicit publication into requirement drawers.

Scaffold preparation is configurable deterministic processing, not an AI agent.
Sponsor drafts are separate from the released review snapshot. All commitments
use an exact version and an explicit human command.
"""
from dataclasses import asdict
from copy import deepcopy
from .scaffold import validate_children, prepare_children, save_children, published_drawers, save_focus_edits
from .requirement_drafts import entries as requirement_entries, save_entries
import json
from pathlib import Path
from uuid import uuid4

from .goals import snapshot as goals_snapshot, stale_fields as goal_stale_fields, validate_links, publish_snapshot, linked_records
from .core import Ref, StaleBasis
from . import packet_preparation as packets
from .decisions import ACTORS, SCOPE, DecisionBlocked, fingerprint, now
from .validation import optional, required, reference
from .refinements import IntentRefinements, requests as refinement_requests, OPEN

PRIVATE = "intake:sponsor"
VALUE_MODEL = "jobs-pains-gains-v1"
FIT_FIELDS = ("business_challenge", "jobs", "gains", "pain_relievers", "gain_creators", "job_support")
VALUE_FIELDS = (*FIT_FIELDS, "supporting_users", "beneficiaries", "need", "value", "why_now", "measures", "approach", "evidence", "assumptions", "assumption_owner")
PROPOSITION_FIELDS = ("beneficiaries", "jobs", "need", "gains", "approach", "job_support", "pain_relievers", "gain_creators", "value")
VALUE_REQUIRED = PROPOSITION_FIELDS
RATIONALE_FIELDS = ("business_challenge", "strategic_relevance", "why_now")
SUCCESS_FIELDS = ("measures", "measure_review")

CONTEXT_FIELDS = ("in_scope", "out_scope", "constraints", "sources", "open_questions", "work_kind", "research_question", "operations_question", "user_situation", "supporting_users", "user_actions", "bottlenecks", "tools", "handoffs", "desired_outputs", "dependencies", "evidence", "assumptions", "assumption_owner")
REQUIRED_FIELDS = ("beneficiaries", "need", "value", "why_now", "measures", "assumptions", "assumption_owner", "in_scope", "out_scope", "constraints", "work_kind", "research_question", "operations_question")
SECTION_FIELDS = {"rationale": RATIONALE_FIELDS, "value": PROPOSITION_FIELDS, "context": CONTEXT_FIELDS, "success": SUCCESS_FIELDS}
SPONSOR_FIELDS = ('business_problems', 'desired_outcomes', 'user_roles', 'current_process', 'pain_points', 'formal_evidence', 'informal_evidence', 'future_process', 'must_haves', 'uncertain_scenarios', 'fallbacks', 'edge_cases', 'scope_unknowns', 'operating_limits', 'project_limits', 'project_risks', 'stakeholders', 'investment_case', 'executive_summary')
ALL_FIELDS = tuple(dict.fromkeys((*VALUE_FIELDS, *RATIONALE_FIELDS, *CONTEXT_FIELDS, *SUCCESS_FIELDS)))
FIELD_SECTIONS = {field: section for section, fields in SECTION_FIELDS.items() for field in fields}



class Intake:
    def __init__(self, store, actor, rights=None):
        from .decision_rights import DecisionRights
        self.rights=rights or DecisionRights(store,actor)
        self.store, self.actor = store, actor
        self.refinements = IntentRefinements(self)

    def latest(self, id):
        row = self.store.db.execute("SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 1", (id,)).fetchone()
        return self.store.read(Ref(id, row[0]), {SCOPE, PRIVATE}) if row else None

    def sponsor(self):
        if self.actor != "priya":
            raise PermissionError("Only the Business sponsor profile can change or publish intake")

    def settings_editor(self, require_draft=True):
        """Local prototype configuration access does not grant intake authorship."""
        if not getattr(self, 'settings_access', False):
            self.sponsor()
            if require_draft:
                self.draft()

    def draft(self, expected="read"):
        record = self.latest("INTAKE-001")
        if not record:
            raise DecisionBlocked("Start the sponsor intake first")
        if expected != "read" and record["ref"] != reference(expected):
            raise StaleBasis("The intake changed. Reload before saving")
        return record

    def save_draft(self, current, body):
        if current:
            from .setup_governance import require_edit
            previous = self.store.read(current['ref'], {PRIVATE})['body']
            if any(previous.get(k) != body.get(k) for k in ('scaffold', 'goals_refs', 'measures_refs')):
                require_edit(self.store, body)
        body.update(saved_at=now(), saved_by=self.actor)
        return self.store.put("INTAKE-001", "intake-draft", PRIVATE, body, current["ref"].revision if current else 0)

    def profile(self):
        return self.latest("PROFILE-INTAKE")

    def cases(self):
        rows = self.store.db.execute("SELECT r.id,MAX(r.revision) revision FROM records r WHERE kind='intake-case' GROUP BY id ORDER BY MIN(rowid) DESC")
        return [self.store.read(Ref(r["id"], r["revision"]), {SCOPE}) for r in rows]

    def signature(self, values, profile):
        return fingerprint({"values": values, "profile": asdict(profile["ref"])})

    def gaps(self, body):
        fields = (*REQUIRED_FIELDS, *FIT_FIELDS, "approach") if body.get("value_model") == VALUE_MODEL else REQUIRED_FIELDS
        return [key for key in fields if not body["values"].get(key, "").strip()]

    def value_checkpoint(self, body):
        values = {k: body['values'].get(k, '') for k in PROPOSITION_FIELDS}
        accepted = self.latest('VALUE-ACCEPTANCE-001')
        # Old acceptances cover a broader snapshot; compare its proposition subset without rewriting history.
        current = bool(accepted and values == {k: accepted['body']['values'].get(k, '') for k in PROPOSITION_FIELDS})
        from .document_changes import pending_sources
        evidence_pending = pending_sources(self)
        current = current and not evidence_pending
        history = [self.store.read(Ref('VALUE-ACCEPTANCE-001', row[0]), {PRIVATE})
                   for row in self.store.db.execute("SELECT revision FROM records WHERE id='VALUE-ACCEPTANCE-001' ORDER BY revision DESC")]
        return {'status': 'accepted' if current else 'needs-review' if accepted else 'draft',
                'current': current, 'accepted': accepted, 'history': history, 'evidence_pending':evidence_pending,
                'missing': [k for k in VALUE_REQUIRED if not values[k].strip()],
                'changed_fields': [k for k in PROPOSITION_FIELDS if accepted and values[k] != accepted['body']['values'].get(k, '')]}

    def require_value(self, body):
        checkpoint = self.value_checkpoint(body)
        if not checkpoint['current']:
            raise DecisionBlocked('Review the value proposition before sharing the intake for direction review. Drafting remains available.')
        return checkpoint['accepted']

    def accept_value(self, data):
        self.sponsor()
        if data.get('confirm') is not True:
            raise ValueError('Confirm that you have reviewed the complete value proposition and its assumptions')
        with self.store.transaction():
            draft = self.draft(data.get('expected'))
            checkpoint = self.value_checkpoint(draft['body'])
            if checkpoint['evidence_pending']:
                raise DecisionBlocked('Resolve the new document impact review before reviewing this proposition. Drafting remains available.')
            if checkpoint['missing']:
                raise DecisionBlocked('Articulate these parts, including any explicit unknowns: ' + ', '.join(checkpoint['missing']))
            if checkpoint['current']:
                return {'message': 'This value proposition is already reviewed.', 'ref': asdict(checkpoint['accepted']['ref'])}
            prior = checkpoint['accepted']
            rationale = required(data, 'rationale') if prior else optional(data, 'rationale') or 'Sponsor reviewed the complete starting proposition and its stated assumptions.'
            values = {k: draft['body']['values'].get(k, '') for k in PROPOSITION_FIELDS}
            ref = self.store.put('VALUE-ACCEPTANCE-001', 'value-acceptance', PRIVATE,
                {'values': values, 'signature': fingerprint(values), 'basis': asdict(draft['ref']),
                 'accepted_by': self.actor, 'at': now(), 'rationale': rationale,
                 'supersedes': asdict(prior['ref']) if prior else None,
                 'changed_fields': checkpoint['changed_fields'], 'status': 'reviewed-starting-proposition',
                 'evidence_status': 'hypotheses-remain-to-be-tested', 'execution': 'not-authorized'},
                prior['ref'].revision if prior else 0)
        return {'message': 'Value proposition review recorded. This does not approve evidence or authorize delivery.', 'ref': asdict(ref)}

    def start(self, data):
        self.sponsor()
        with self.store.transaction():
            if self.latest("INTAKE-001"):
                raise DecisionBlocked("An intake already exists. Continue its saved draft")
            title = required(data, "title")
            if not self.profile():
                self.store.put("PROFILE-INTAKE", "intake-profile", SCOPE, json.loads((Path(__file__).parent / "config/intake_profile.json").read_text()))
            project = self.latest("PROJECT-001")
            if not project:
                self.store.put("PROJECT-001", "project", SCOPE, {"title": title, "sponsor": "priya", "created_at": now()})
            old_intent, old_policy = self.latest("INT-001"), self.latest("POL-001")
            values = {k: "" for k in ALL_FIELDS}
            values.update(work_kind="digital", assumption_owner="sam")
            if old_intent:
                values["value"] = old_intent["body"].get("text", "")
            if old_policy:
                values["constraints"] = old_policy["body"].get("text", "")
            carried = {}
            if old_intent:
                from .scope_context import snapshot
                saved = snapshot(old_intent['body'], published=True)
                values.update(saved['values'])
                carried = dict(sponsor_brief={'answers': saved['answers']},
                    field_provenance=saved['field_provenance'],
                    sponsor_question_provenance=saved['question_provenance'])
            ref = self.save_draft(None, {"title": title, "value_model": VALUE_MODEL, "values": values, "scaffold": [], "scaffold_signature": None, "profile": asdict(self.profile()["ref"]), "legacy_basis": asdict(old_intent["ref"]) if old_intent else None, **carried})
        return {"message": "Sponsor draft created. Existing requirements and decisions are unchanged.", "ref": asdict(ref)}

    def save(self, data):
        self.sponsor()
        step = data.get("step")
        if step not in SECTION_FIELDS:
            raise ValueError("Unknown intake section")
        with self.store.transaction():
            current = self.draft(data.get("expected"))
            body = current["body"]
            # Preserve legacy value-save clients; the current UI uses the four section contracts.
            for key in VALUE_FIELDS if step == "value" else SECTION_FIELDS[step]:
                if key in data:
                    value = optional(data, key)
                    if value != body["values"].get(key) and key in body.get("field_provenance", {}):
                        body["field_provenance"][key]["status"] = "sponsor-edited-after-coaching"
                    body["values"][key] = value
            if step == "value" and data.get("value_model") == VALUE_MODEL:
                body["value_model"] = VALUE_MODEL
            if body["values"]["work_kind"] not in {"digital", "operational", "market", "other"}:
                raise ValueError("Choose a valid work type")
            if body["values"]["assumption_owner"] not in ACTORS:
                raise ValueError("Choose an owner for the open assumptions")
            ref = self.save_draft(current, body)
        return {"message": "Intake saved. Changes require a fresh scaffold and direction review.", "ref": asdict(ref)}

    def configure(self, data):
        with self.store.transaction():
            current = self.profile()
            if not current or current["ref"] != reference(data.get("expected")):
                raise StaleBasis("The profile changed. Reload its settings")
            raw = data.get("drawers")
            if not isinstance(raw, list) or not 1 <= len(raw) <= 20:
                raise ValueError("Configure between one and twenty categories")
            if self.actor != 'priya' and not getattr(self, 'settings_access', False):
                old = current['body']['drawers']
                if data.get('name') != current['body']['name'] or [x.get('key') for x in raw] != [x['key'] for x in old]:
                    raise PermissionError('Only the sponsor can rename the profile or add categories')
                for proposed, saved in zip(raw, old):
                    if saved['owner'] != self.actor and proposed != saved:
                        raise PermissionError('You can configure only categories you lead')
                    if proposed.get('owner') != saved['owner']:
                        raise PermissionError('Only the sponsor can change a category lead')
            categories, keys = [], set()
            for item in raw:
                key = required(item, "key")
                if not key.replace('-', '').isalnum() or key in keys or len(key) > 60:
                    raise ValueError("Each category needs a unique short key")
                keys.add(key)
                owner, when = item.get("owner"), item.get("when")
                if owner not in ACTORS or when not in {"always", "digital", "operational", "market", "other", "disabled"}:
                    raise ValueError("Invalid category owner or applicability")
                fields = item.get("basis_fields")
                if not isinstance(fields, list) or not fields or any(f not in ALL_FIELDS for f in fields):
                    raise ValueError("Each category needs valid intake field links")
                categories.append({"key": key, "label": required(item, "label"), "question": required(item, "question"), "owner": owner, "when": when, "basis_fields": fields, "children": validate_children(item.get("children", []), ACTORS, ALL_FIELDS)})
            ref = self.store.put("PROFILE-INTAKE", "intake-profile", SCOPE, {"name": required(data, "name"), "description": current["body"]["description"], "drawers": categories, "changed_by": self.actor, "changed_at": now()}, current["ref"].revision)
        return {"message": "Profile version saved. Rebuild and review the draft scaffold before publication.", "ref": asdict(ref)}

    def build(self, data):
        self.sponsor()
        with self.store.transaction():
            current = self.draft(data.get("expected"))
            body = current["body"]
            gaps = self.gaps(body)
            if gaps:
                raise DecisionBlocked("Complete or explicitly describe what is unknown: " + ", ".join(gaps))
            if body["scaffold"] and data.get("confirm") is not True:
                raise DecisionBlocked("Confirm refreshing the full intake basis; your drawer wording will be retained")
            profile = self.profile()
            values = body["values"]
            previous = {d['key']: d for d in body['scaffold']}
            earlier_values = body.get('scaffold_values', {})
            changed = [k for k in sorted(set(values)|set(earlier_values)) if values.get(k, '') != earlier_values.get(k, '')]
            scaffold = []
            for item in profile['body']['drawers']:
                if item['when'] not in {'always', values['work_kind']}:
                    continue
                old = previous.get(item['key'], {})
                editable = {k: old[k] for k in ('included', 'label', 'question', 'owner', 'rationale', 'requirement', 'acceptance_criteria', 'requirements', 'agent_provenance', 'project_focus', 'goal_ids') if k in old}
                scaffold.append({**item, 'included': True, 'requirement': '', 'acceptance_criteria': '',
                    'rationale': 'Investigate ' + item['label'].lower() + ' against the complete business intent; confirm the question and rationale.',
                    **editable, 'origin': 'Configured category, reviewed against the full intake',
                    'intake_fields': list(values), 'changed_intake_fields': changed,
                    'value_fit_fields': [k for k in PROPOSITION_FIELDS if values.get(k)],
                    'children': prepare_children(item.get('children', []), old.get('children', []), values, changed)})
            body['scaffold'] = scaffold
            body['scaffold_values'] = dict(values)
            body['refinements'] = [x for x in body.get('refinements', []) if self.store.latest(x['id'], {SCOPE})['body']['status'] == 'drafted']
            if not body["scaffold"]:
                raise DecisionBlocked("No configured category applies. Update the intake profile")
            body["profile"] = asdict(profile["ref"])
            body["scaffold_signature"] = self.signature(values, profile)
            ref = self.save_draft(current, body)
        return {"message": "Drawers refreshed against the full intake. Prior wording retained; review changed inputs and applicability.", "ref": asdict(ref)}

    def save_drawers(self, data):
        self.sponsor()
        with self.store.transaction():
            current = self.draft(data.get("expected"))
            body = current["body"]
            if body["scaffold_signature"] != self.signature(body["values"], self.profile()):
                raise StaleBasis("Intake or profile changed. Rebuild the scaffold first")
            raw = data.get("drawers")
            if not isinstance(raw, list) or [r.get("key") for r in raw] != [r["key"] for r in body["scaffold"]]:
                raise ValueError("The drawer set changed. Reload the scaffold")
            if 'goals_catalog' in data:
                from .goals import Goals
                body = Goals(self)._write(current, goals_snapshot(self, body), data['goals_catalog'])
            goal_ids = {g['id'] for g in goals_snapshot(self, body)['goals']}
            for item, original in zip(raw, body["scaffold"]):
                for supplied, saved in [(item, original), *zip(item.get('children', []), original.get('children', []))]:
                    if 'goal_ids' in supplied:
                        saved['goal_ids'] = validate_links(supplied['goal_ids'], goal_ids)
                save_children(item.get('children', []), original.get('children', []), ACTORS, item['key'])
                if type(item.get("included")) is not bool or item.get("owner") not in ACTORS:
                    raise ValueError("Choose an owner and inclusion for each drawer")
                original.update({k: required(item, k) for k in ("label", "question", "rationale")})
                save_entries(item, original, item['key'])
                original.update(included=item["included"], owner=item["owner"])
                save_focus_edits(item,original)
            if not any(d["included"] for d in body["scaffold"]):
                raise DecisionBlocked("Retain at least one requirement drawer")
            ref = self.save_draft(current, body)
        return {"message": "Scaffold saved. Draft requirements remain proposals.", "ref": asdict(ref)}

    def review_snapshot(self, expected, business_assessment=None):
        self.sponsor()
        current = self.draft(expected)
        body = deepcopy(current['body'])
        accepted = self.require_value(body)
        if self.gaps(body) or not body['scaffold'] or body['scaffold_signature'] != self.signature(body['values'], self.profile()):
            raise DecisionBlocked('Complete the intake and review a current scaffold first')
        issues = self.refinements.freshness(body)
        if issues:
            raise StaleBasis('; '.join(issues))
        body['goal_snapshot'] = goals_snapshot(self, body)
        if any(item['body']['active'] and goal_stale_fields(item, body['values']) for items in body['goal_snapshot'].values() for item in items):
            raise StaleBasis('Intake answers changed. Review the affected goals or measures and save before sharing direction.')
        body['finding_basis'] = self.refinements.finding_basis(body)
        body['value_acceptance'] = {k: accepted['body'][k] for k in ('accepted_by', 'at', 'rationale', 'signature', 'status')}
        if business_assessment is not None:
            # This remains a private preview until the sponsor explicitly releases
            # the assessment and its selected evidence excerpts in request().
            body['business_assessment_preview'] = self.business_assessments.snapshot_for_publication(
                current, business_assessment)
        baseline = self.latest('INT-001')
        basis = dict(draft=asdict(current['ref']), profile=asdict(self.profile()['ref']),
                     base_intent=asdict(baseline['ref']) if baseline else None, snapshot=body)
        return basis

    def preflights(self):
        if self.actor != 'priya':
            return []
        rows = self.store.db.execute("SELECT id,MAX(revision) revision FROM records WHERE kind='sponsor-preflight' AND scope=? GROUP BY id ORDER BY MIN(rowid) DESC", (PRIVATE,))
        return [self.store.read(Ref(row['id'], row['revision']), {PRIVATE}) for row in rows]

    def prepare_preflight(self, data):
        self.sponsor()
        with self.store.transaction():
            assessment = data.get('business_assessment')
            basis = self.review_snapshot(data.get('expected'), assessment)
            handoff = {}
            for field in ('research_focus', 'design_focus', 'open_questions'):
                text = data.get(field, '')
                if not isinstance(text, str) or len(text) > 12000:
                    raise ValueError('Keep each handoff note within 12,000 characters')
                handoff[field] = text.strip()
            signature = fingerprint(dict(basis=basis, handoff=handoff))
            for record in self.preflights():
                if record['body'].get('packet') and record['body']['signature'] == signature:
                    return dict(message='This exact package is already prepared.', id=record['ref'].id)
            id = 'SPREF-'+uuid4().hex[:12]
            body = dict(**basis, handoff=handoff, signature=signature, owner=self.actor,
                        at=now(), reviewers=['sam', 'lee'], audience='project', stage='prepared',
                        packet=dict(id=packets.prepared_id(id), revision=1))
            if assessment is not None:
                body['business_assessment'] = deepcopy(assessment)
            ref = self.store.put(id, 'sponsor-preflight', PRIVATE, body)
            packet_refs = [reference(item['ref']) for group in basis['snapshot']['goal_snapshot'].values() for item in group]
            packet_refs.extend(reference(raw) for raw in basis['snapshot'].get('finding_basis', []))
            if basis['base_intent']:
                packet_refs.append(reference(basis['base_intent']))
            packets.prepare(self.store, ref, 'Business direction for Research and Design: '+basis['snapshot']['title'], packet_refs, PRIVATE)
            refs = [reference(basis['draft']), reference(basis['profile'])]
            for group in basis['snapshot']['goal_snapshot'].values():
                refs.extend(reference(item['ref']) for item in group)
            for raw in refs:
                self.store.depend(ref, raw, {PRIVATE, SCOPE})
        return dict(message='Sponsor context packet prepared for private inspection.', id=ref.id)

    def checked_preflight(self, raw):
        self.sponsor()
        ref = reference(raw)
        record = self.store.read(ref, {PRIVATE})
        if record['kind'] != 'sponsor-preflight' or record['body']['owner'] != self.actor:
            raise PermissionError('Choose your sponsor preflight package')
        if self.store.latest(ref.id, {PRIVATE})['ref'] != ref:
            raise StaleBasis('Reopen the current sponsor package')
        basis = self.review_snapshot(record['body']['draft'], record['body'].get('business_assessment'))
        if fingerprint(dict(basis=basis, handoff=record['body']['handoff'])) != record['body']['signature']:
            raise StaleBasis('The intake, evidence, goals or published direction changed. Prepare a fresh package')
        packets.read_prepared(self.store, record, {PRIVATE, SCOPE})
        return record

    def preflight_state(self):
        if self.actor != 'priya':
            return None
        blockers, basis = [], None
        try:
            basis = self.review_snapshot(asdict(self.draft()['ref']))
        except (DecisionBlocked, StaleBasis) as error:
            blockers.append(str(error))
        # Reuse the current validated basis across package comparisons in this read.
        packages = []
        for record in self.preflights():
            selected_basis = basis
            if record['body'].get('business_assessment'):
                try:
                    selected_basis = self.review_snapshot(record['body']['draft'], record['body']['business_assessment'])
                except (DecisionBlocked, StaleBasis, PermissionError, ValueError):
                    selected_basis = None
            packages.append({**record, 'current': bool(record['body'].get('packet') and selected_basis and fingerprint(dict(
                basis=selected_basis, handoff=record['body']['handoff'])) == record['body']['signature'])})
        return dict(blockers=blockers, packages=packages)

    def release_business_assessment(self, preview, case_id):
        """Explicit snapshot release; callers must hold the publication transaction."""
        standard = preview['standard']
        standard_ref = reference(standard['ref'])
        existing_standard = self.latest(standard_ref.id)
        if existing_standard:
            try:
                pinned = self.store.read(standard_ref, {SCOPE})
            except PermissionError:
                pinned = None
            if pinned:
                if pinned['kind'] != 'evidence-reasoning-standard' or pinned['body'] != standard['body']:
                    raise StaleBasis('The evidence standard conflicts with its saved version; issue a new standard version')
            elif standard_ref.revision != existing_standard['ref'].revision + 1:
                raise StaleBasis('The evidence standard version cannot be reconstructed')
            else:
                self.store.put(standard_ref.id, 'evidence-reasoning-standard', SCOPE,
                    deepcopy(standard['body']), existing_standard['ref'].revision)
        elif standard_ref.revision == 1:
            self.store.put(standard_ref.id, 'evidence-reasoning-standard', SCOPE, deepcopy(standard['body']))
        else:
            raise StaleBasis('The evidence standard history is unavailable')
        release_map = {}
        for source in preview['source_excerpt_manifest']:
            raw = source['source_ref']
            identity = fingerprint(dict(assessment=preview['assessment_ref'], source=raw))[:20]
            source_id = 'RELEASE-BASSESS-' + identity
            text = '\n\n'.join(dict.fromkeys(p['quote'] for p in source['passages']))
            content = dict(title=source['source_title'], text=text, source_version=deepcopy(raw),
                original_passages=[{k:p[k] for k in ('passage_id','start','end')} for p in source['passages']],
                evidence_level='documentary', released_by=self.actor, released_at=now(),
                boundary='Selected documentary evidence excerpts, explicitly released with a Business Intent assessment. Source claims do not establish runtime or outcome evidence.')
            old = self.latest(source_id)
            if old:
                if old['kind'] != 'source' or old['body'].get('source_version') != raw or old['body'].get('text') != text:
                    raise StaleBasis('The selected evidence release conflicts with its saved version')
                shared = old['ref']
            else:
                shared = self.store.put(source_id, 'source', SCOPE, content)
            release_map[reference(raw).label()] = asdict(shared)
        release_id = 'BASSESS-RELEASE-' + case_id
        shared_ref = Ref(release_id, 1)
        public = self.business_assessments.public_snapshot(preview, release_map, asdict(shared_ref))
        self.store.put(release_id, 'business-assessment-release', SCOPE,
            dict(**public, released_by=self.actor, released_at=now(), authority='assessment-only'))
        for raw in release_map.values():
            self.store.depend(shared_ref, reference(raw), {SCOPE})
        self.store.depend(shared_ref, standard_ref, {SCOPE})
        return dict(ref=asdict(shared_ref), snapshot=public)

    def request(self, data):
        self.sponsor()
        if data.get('confirm') is not True:
            raise ValueError('Review and confirm the shared intake snapshot')
        with self.store.transaction():
            prepared = self.checked_preflight(data['preflight']) if data.get('preflight') else None
            assessment = prepared['body'].get('business_assessment') if prepared else data.get('business_assessment')
            basis = self.review_snapshot(data.get('expected'), assessment)
            if prepared and prepared['body']['draft'] != basis['draft']:
                raise StaleBasis('Use the package for this exact intake version')
            for case in self.cases():
                if case['body']['source_draft'] == basis['draft'] and case['body']['status'] in {'pending-review', 'published', 'deferred'}:
                    raise DecisionBlocked('This exact draft already has a review. Open that review or revise the draft')
            reviewers = ['sam', 'lee'] if prepared else ['sam', 'maya']
            id = 'INTREV-'+uuid4().hex[:10]
            shared_snapshot = deepcopy(basis['snapshot'])
            assessment_preview = shared_snapshot.pop('business_assessment_preview', None)
            if assessment_preview is not None:
                if data.get('release_business_assessment') is not True:
                    raise DecisionBlocked('Review and explicitly share the Business Intent assessment and selected evidence excerpts with this package')
                shared_snapshot['business_assessment'] = self.release_business_assessment(assessment_preview, id)
            body = dict(snapshot=shared_snapshot, source_draft=basis['draft'], base_intent=basis['base_intent'],
                        status='pending-review', reviews={}, reviewers=reviewers, requested_by=self.actor,
                        requested_at=now(), decision_ids=[])
            self.rights.bind(body,"intent",review_field="reviewers")
            if prepared:
                body['preflight'] = asdict(prepared['ref'])
                body['snapshot']['handoff'] = deepcopy(prepared['body']['handoff'])
                body['prepared_packet'] = prepared['body']['packet']
                body['packet'] = dict(id='PKT-'+id, revision=1)
            ref = self.store.put(id, 'intake-case', SCOPE, body)
            if shared_snapshot.get('business_assessment'):
                self.store.depend(ref, reference(shared_snapshot['business_assessment']['ref']), {SCOPE})
            if prepared:
                prepared_packet = packets.read_prepared(self.store, prepared, {PRIVATE, SCOPE})
                mapping = {prepared['ref']: ref}
                for group in prepared['body']['snapshot']['goal_snapshot'].values():
                    for item in group:
                        source = self.store.read(reference(item['ref']), {PRIVATE})
                        proposal = self.store.put('REVIEW-'+id+'-'+item['id'], source['kind'].removesuffix('-draft')+'-proposal', SCOPE,
                            {**deepcopy(source['body']), 'status':'proposed-for-direction-review',
                             'source_draft':item['ref'], 'source_case':asdict(ref)})
                        mapping[source['ref']] = proposal
                        self.store.depend(proposal, ref, {SCOPE})
                packets.release(self.store, prepared_packet, 'PKT-'+id, 1, mapping, self.actor)
        names = 'Research and Design' if prepared else 'Research and Operations'
        return dict(message='Direction review opened for '+names+'. The released snapshot is now shared.', id=ref.id)

    def case(self, expected):
        ref = reference(expected)
        current = self.latest(ref.id)
        if not current or current["kind"] != "intake-case" or current["ref"] != ref:
            raise StaleBasis("The intake review changed. Reload before responding")
        if current["body"]["status"] in {"published", "declined"}:
            raise DecisionBlocked("This direction review is closed. Revise the intake to reconsider it")
        return current

    def freshness(self, body):
        messages = []
        from .document_changes import pending_sources
        if pending_sources(self):
            messages.append('The sponsor has new material to resolve before continuing direction review.')
        if body["source_draft"] != asdict(self.draft()["ref"]):
            messages.append("Sponsor draft changed; request a fresh review")
        if body["snapshot"]["profile"] != asdict(self.profile()["ref"]):
            messages.append("Intake profile changed; rebuild and review the scaffold")
        baseline = self.latest("INT-001")
        if body["base_intent"] != (asdict(baseline["ref"]) if baseline else None):
            messages.append("Published direction changed; request a fresh review")
        messages.extend(self.refinements.freshness(body["snapshot"]))
        return messages

    def review(self, data):
        disposition = data.get("disposition")
        if disposition not in {"ready-for-investigation", "changes-requested"}:
            raise ValueError("Choose a direction review response")
        with self.store.transaction():
            case = self.case(data.get("expected"))
            self.rights.check_review(case['body'],"intent",self.actor)
            if self.actor not in case['body'].get('reviewers', ['sam', 'maya']):
                raise PermissionError('Only an assigned domain reviewer can respond to this direction')
            if self.freshness(case["body"]):
                raise StaleBasis("The direction basis changed. Ask the sponsor for a fresh review")
            r = self.store.put("INTASSESS-" + uuid4().hex[:10], "intake-assessment", SCOPE, {"actor": self.actor, "disposition": disposition, "rationale": required(data, "rationale"), "snapshot_fingerprint": fingerprint(case["body"]["snapshot"]), "at": now()})
            body = case["body"]
            body["reviews"][self.actor] = asdict(r)
            body["status"] = "pending-review"
            result = self.store.put(case["ref"].id, "intake-case", SCOPE, body, case["ref"].revision)
        return {"message": "Direction review recorded. Evidence and requirements are not approved by this response.", "ref": asdict(result)}

    def publish(self, data):
        from .setup_governance import require_publication
        require_publication(self.store, self.draft()['body'])
        if data.get("confirm") is not True:
            raise ValueError("Explicitly confirm publication for investigation")
        with self.store.transaction():
            case = self.case(data.get("expected"))
            body = case["body"]
            authority=self.rights.authorize(body,"intent",approval=True)
            stale = self.freshness(body)
            if stale:
                raise StaleBasis("; ".join(stale))
            for actor in body.get('reviewers', ['sam', 'maya']):
                r = body["reviews"].get(actor)
                review = self.store.read(Ref(**r), {SCOPE})["body"] if r else None
                if not review or review["disposition"] != "ready-for-investigation" or review["snapshot_fingerprint"] != fingerprint(body["snapshot"]):
                    raise DecisionBlocked("Resolve and record " + ACTORS[actor]["name"] + "'s direction review first")
            selected_ids = {x['id'] for x in body['snapshot'].get('refinements', [])}
            if any(r['body']['status'] in OPEN and r['ref'].id not in selected_ids for r in refinement_requests(self.store)):
                raise DecisionBlocked('Respond to the other open intent requests before publishing a new direction')
            rationale = required(data, "rationale")
            snap, decision_id = body["snapshot"], "INTDEC-" + uuid4().hex[:10]
            v = snap["values"]
            prior_intent = self.latest('INT-001')
            previous_values = self.refinements.values(prior_intent) if prior_intent else {}
            # Sponsor questions also save material fields outside the original
            # scaffold inventory (for example fallback, risks and investment).
            # Compare the complete snapshots, including removed fields, instead
            # of silently omitting those answers from the decision receipt.
            changes = {k: {'before': previous_values.get(k, ''), 'after': v.get(k, '')}
                       for k in sorted(set(previous_values) | set(v))
                       if previous_values.get(k, '') != v.get(k, '')}
            selected_requests = self.refinements.selected(snap)
            finding_refs = sorted({reference(r) for r in snap.get('finding_basis', [])} | {reference(r['body']['source']) for r in selected_requests})
            def put_version(id, kind, content):
                old = self.latest(id)
                return self.store.put(id, kind, SCOPE, content, old["ref"].revision if old else 0)
            goal_catalog = publish_snapshot(self, snap, case['ref'], decision_id)
            all_goal_bases = [*goal_catalog['goals'].values(), *goal_catalog['measures'].values()]
            active_goal_ids = {g['id'] for g in snap.get('goal_snapshot', {}).get('goals', []) if g['body']['active']}
            assessment = snap.get('business_assessment')
            assessment_anchor = dict(ref=deepcopy(assessment['ref'])) if assessment else None
            intent = put_version("INT-001", "intent", {"goal_refs": [asdict(r) for r in goal_catalog['goals'].values()], "text": v["value"], "field_provenance": snap.get("field_provenance", {}), "sponsor_question_provenance": deepcopy(snap.get("sponsor_question_provenance", {})), "intake": dict(v), "scaffold": snap["scaffold"], "profile": snap["profile"], "business_brief": snap.get("sponsor_brief", {}), "source_case": asdict(case["ref"]), "supersedes": asdict(prior_intent["ref"]) if prior_intent else None, "finding_basis": [asdict(r) for r in finding_refs], "value_proposition": {k:v[k] for k in PROPOSITION_FIELDS if k in v}, "value_model": snap.get("value_model", "legacy-intake"), "fit_status": "hypothesis-to-test", "status": "ratified-for-investigation", "evidence_status": "not-validated-by-publication", "execution": "not-authorized", "decision_id": decision_id, **({'business_assessment': assessment_anchor} if assessment else {})})
            policy = put_version("POL-001", "policy", {"text": v["constraints"] + "\nOutside scope: " + v["out_scope"], "status": "user-declared-boundary", "note": "Source applicability requires its authorized owner"})
            context = put_version("CTX-001", "project-context", {"text": v["in_scope"], **{k:v[k] for k in CONTEXT_FIELDS if k in v}, "profile": snap["profile"], "intent": asdict(intent)})
            decision = self.store.put(decision_id, "intent-decision", SCOPE, {"actor": self.actor, "authority": authority, "disposition": "publish-for-investigation", "rationale": rationale, "case": asdict(case["ref"]), "reviews": body["reviews"], "intent": asdict(intent), "at": now(), "changes": changes, "previous_intent": asdict(prior_intent["ref"]) if prior_intent else None, "finding_basis": [asdict(r) for r in finding_refs], "refinements": snap.get("refinements", []), "boundary": "Direction for investigation; evidence limits remain, requirements reviewed separately, delivery not authorized"})
            resolved = self.refinements.finalize(snap, intent, decision)
            bases = [intent, policy, context, decision, Ref(**snap["profile"]), *finding_refs, *resolved]
            if assessment:
                bases.append(reference(assessment['ref']))
                self.store.depend(intent, reference(assessment['ref']), {SCOPE})
            for source in finding_refs:
                self.store.depend(intent, source, {SCOPE})
            self.store.depend(intent, decision, {SCOPE})
            drawers, requirements = [], []
            flattened = list(published_drawers(snap['scaffold']))
            active_keys = {d['key'] for d in flattened}
            for d in flattened:
                if not d["included"]:
                    continue
                goal_refs = [asdict(goal_catalog['goals'][id]) for id in d.get('goal_ids', []) if id in active_goal_ids]
                selected_goals, selected_measures = linked_records(self.store, goal_refs)
                goal_bases = [*selected_goals, *selected_measures]
                drawer = put_version("DRW-" + d["key"], "requirement-drawer", {**d, 'goal_refs': goal_refs, 'measure_refs': [asdict(r) for r in selected_measures], "status": "active", "intent": asdict(intent), "context": asdict(context), "profile": snap["profile"], "source_case": asdict(case["ref"]), "open_questions": v["open_questions"]})
                drawers.append(drawer)
                if d.get('parent_id'):
                    self.store.depend(drawer, self.latest(d['parent_id'])['ref'], {SCOPE})
                for base in [*bases, *goal_bases]:
                    self.store.depend(drawer, base, {SCOPE})
                for candidate in requirement_entries(d, d['key']):
                    if not candidate['included'] or not candidate['requirement'].strip():
                        continue
                    req_id = candidate['id']
                    existing = self.latest(req_id)
                    if existing:
                        if existing['kind'] != 'requirement' or existing['body'].get('drawer_id') != drawer.id:
                            raise ValueError('Requirement identity belongs to a different area')
                        requirements.append(existing['ref'])
                        continue  # Shared wording changes through its existing human decision process.
                    assessment_links = []
                    if assessment:
                        frozen = next((r for r in assessment['snapshot'].get('requirement_targets', []) if r['id'] == req_id), None)
                        if frozen and frozen.get('text') == candidate['requirement'] and frozen.get('acceptance_criteria') == candidate['acceptance_criteria']:
                            assessment_links = [deepcopy(link) for link in assessment['snapshot']['assessment'].get('requirement_links', []) if link['target'] == req_id]
                    req = self.store.put(req_id, "requirement", SCOPE, {"goal_refs": goal_refs, "measure_refs": [asdict(r) for r in selected_measures], "title": candidate['title'] or d['label'] + ' · initial requirement', "text": candidate['requirement'], "drawer": d["label"], "drawer_id": drawer.id, "rationale": d["rationale"], "acceptance_criteria": candidate['acceptance_criteria'], "conditions": v["constraints"] + "\nOutside scope: " + v["out_scope"], "status": "proposed", "fulfillment": "not-evaluated", "execution": "not-authorized", "created_by": self.actor, "created_at": now(), "intake_case": asdict(case["ref"]), "owner": self.rights.rules("requirement")["decider"], **({'business_assessment':dict(ref=deepcopy(assessment['ref']), claim_links=assessment_links)} if assessment else {})})
                    for base in [*bases, drawer, *goal_bases]:
                        self.store.depend(req, base, {SCOPE})
                    self.store.packet("PKT-" + req_id, 1, "Initial requirement from sponsor intake", [req, *bases, drawer, *goal_bases], {SCOPE}, {SCOPE})
                    requirements.append(req)
            # Retiring a drawer never removes its requirements or historical versions.
            for row in self.store.db.execute("SELECT id,MAX(revision) rev FROM records WHERE kind='requirement-drawer' GROUP BY id").fetchall():
                old = self.latest(row["id"])
                if old["body"]["key"] not in active_keys and old["body"]["status"] == "active":
                    put_version(row["id"], "requirement-drawer", {**old["body"], "status": "retired", "retired_by": decision_id})
            packet_version = self.store.db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM packets WHERE id='PKT-INTENT' ").fetchone()[0]
            packet = self.store.packet("PKT-INTENT", packet_version, "Published starting direction and requirement scaffold", [*bases, *all_goal_bases, *drawers, *requirements, case["ref"], *[Ref(**r) for r in body["reviews"].values()]], {SCOPE}, {SCOPE})
            project = self.latest("PROJECT-001")
            self.store.put("PROJECT-001", "project", SCOPE, {**project["body"], "title": snap["title"], "sponsor": "priya"}, project["ref"].revision)
            body.update(status="published", result={"intent": asdict(intent), "drawers": [asdict(r) for r in drawers], "requirements": [asdict(r) for r in requirements], "packet": {"id": packet["id"], "revision": packet["revision"]}})
            body["decision_ids"].append(decision_id)
            self.store.put(case["ref"].id, "intake-case", SCOPE, body, case["ref"].revision)
        return {"message": "Business intent published. Drawers reflect the full intake; existing requirements retain their versions and require reassessment where their basis changed.", "id": intent.id}

    def close(self, data):
        disposition = data.get("disposition")
        if disposition not in {"defer", "decline"}:
            raise ValueError("Choose defer or decline")
        with self.store.transaction():
            case = self.case(data.get("expected"))
            body = case["body"]
            authority=self.rights.authorize(body,"intent")
            owner, question = data.get("next_owner"), optional(data, "next_question")
            if disposition == "defer" and (owner not in ACTORS or not question):
                raise ValueError("Deferral needs an owner and next question")
            decision = self.store.put("INTDEC-" + uuid4().hex[:10], "intent-decision", SCOPE, {"actor": self.actor, "authority": authority, "disposition": disposition, "case": asdict(case["ref"]), "rationale": required(data,"rationale"), "next_owner": owner if disposition == "defer" else None, "next_question": question if disposition == "defer" else None, "at": now()})
            body.update(status="deferred" if disposition == "defer" else "declined", next_owner=owner, next_question=question)
            body["decision_ids"].append(decision.id)
            self.store.put(case["ref"].id, "intake-case", SCOPE, body, case["ref"].revision)
        return {"message": "Direction decision recorded. The published baseline and requirements remain unchanged."}

    def state(self):
        draft, profile = self.latest("INTAKE-001"), self.profile()
        scaffold_defaults = json.loads((Path(__file__).parent / "config/intake_profile.json").read_text())["drawers"] if not profile else []
        cases = self.cases()
        for case in cases:
            body = case["body"]
            case["stale"] = self.freshness(body) if body["status"] not in {"published", "declined"} else []
            case["reviews"] = {a:self.store.read(Ref(**r), {SCOPE}) for a,r in body["reviews"].items()}
            case["rights"]=self.rights.status(body,"intent")
            case["ready"] = not case["rights"]["blockers"] and not case["stale"] and body["status"] not in {"published", "declined"} and all(case["reviews"].get(a, {}).get("body", {}).get("disposition") == "ready-for-investigation" for a in body.get('reviewers', ['sam','maya']))
        published = next((c for c in cases if c["body"]["status"] == "published"), None)
        refinements = refinement_requests(self.store)
        for r in refinements:
            r['source_record'] = self.store.read(reference(r['body']['source']), {SCOPE})
            r['source_current'] = self.store.latest(r['body']['source']['id'], {SCOPE})['ref'] == reference(r['body']['source'])
        if draft and self.actor == 'priya':
            draft['body']['finding_basis'] = self.refinements.finding_basis(draft['body'])
            draft['body']['goal_snapshot'] = goals_snapshot(self, draft['body'])
        baseline = self.latest('INT-001')
        baseline_values = self.refinements.values(baseline) if baseline else {}
        decisions = [self.store.read(Ref(r["id"],r["revision"]), {SCOPE}) for r in self.store.db.execute("SELECT id,revision FROM records WHERE kind='intent-decision' ORDER BY rowid DESC")]
        from .setup_governance import context as setup_context
        from .sponsor import QUESTIONS, FIELDS, LEGACY
        source_questions = [{"id": q["id"], "title": q["title"], "field": FIELDS[q["id"]], "legacy_field": LEGACY.get(q["id"])} for q in QUESTIONS]
        return {"source_questions": source_questions, "setup_governance": setup_context(self.store, draft["body"] if draft else None), "preflight": self.preflight_state(), "sections": SECTION_FIELDS, "value_checkpoint": self.value_checkpoint(draft["body"]) if draft and self.actor == "priya" else None, "refinements": refinements, "baseline_values": baseline_values, "has_draft": bool(draft), "draft": draft if self.actor == "priya" else None, "profile": profile, "scaffold_defaults": scaffold_defaults, "cases": cases, "published": published, "decisions": decisions, "gaps": self.gaps(draft["body"]) if draft and self.actor == "priya" else [], "scaffold_current": bool(draft and profile and draft["body"]["scaffold"] and draft["body"]["scaffold_signature"] == self.signature(draft["body"]["values"], profile)), "can_create_requirements": not draft or bool(published)}
