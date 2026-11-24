# D014: One knowledge system: components, chained packets, dependency difference and confidence (revision 2)

Status: **accepted by the owner, 26 November 2026; revision 2 accepted the same day**
after a review of the decision shortcuts in revision 1 (see Revision history). These
are the governing rules for how knowledge is composed, moved, compared and assessed.
**Built** on `claude/thesis-board` on 26 November 2026, with the owner's go-ahead for all
build steps. See "What was built" below for exactly what exists and its limits.

Visual reference: the whiteboard "Unified knowledge system and confidence"
(claude.ai, private to the owner). Evidence: [the wave test](../evaluations/wave-test.md).

## Principle

Traceability and translation of meaning come from two things working together:

1. **Identifier matches.** When two groups' packets refer to the same block, at a
   pinned revision, they are talking about the same thing.
2. **Dependency difference.** What a block means to a group is shown by what that
   group links it to, how, under which conditions and at which revision. Comparing
   two groups' dependencies around one identifier makes their interpretations visible.

Packets chain when a later packet uses a block an earlier packet pinned. The chain of
pinned identifiers and typed links is the trace from source to decision.

## Rule 1: six layers, one chain

| Layer | What it is | Status |
| --- | --- | --- |
| 1 Sources | Interviews, documents, tests, logs, decisions. Kept whole, never replaced by a summary. | Built |
| 2 Components | A fixed set of parts every block is made of (Rule 2) | Built (configuration) |
| 3 Building blocks | Typed units of knowledge in four families (D013) | Built, with recipes |
| 4 Typed links | Relation, target, pinned revision, conditions, use, reason | Built (typed table) |
| 5 Packets | One reader, one task; pins revisions and reports what changed | Built; packet types previewable |
| 6 Requirement categories | The requirement areas and subcategories, reconciled in Decisions & Issues | Built, with the feeds rule |

## Rule 2: a fixed set of components

Every block is composed from the same parts, in every team and vertical. Teams vary
block types and vocabulary, never components. Changing the set needs a decision record.

| Component | Holds |
| --- | --- |
| Actor | Who it is about |
| Situation | When or where it applies |
| Claim | What is said |
| Basis | The source it came from |
| Strength | How sure |
| Time | When it was true |
| Rationale | Why |
| Alternatives | What else was considered |
| Criterion | What good looks like |
| Measure | How you would know |
| Owner | Who is responsible |
| Status | Open, resolved, approved |

Actor and Situation carry scope, which is where meaning drifts between groups. The AI
partner proposes them most often, as suggestions (Rule 8).

**A claim needs a basis that fits its reach.** One observation supports an
observation, not a prevalence claim. "The office answers nine to five" (observation)
leads to "these hours may make rescheduling hard for shift workers" (hypothesis) and
"who is affected, how often, and what happens?" (open question). A finding such as
"most who missed knew in advance" stands only when more evidence supports both
prevalence and its scope: in the clinic example, 9 of 12 interviews, shift workers only.

## Rule 3: block types are recipes of components

A block type is its required components, optional components and family. Starting
recipes, for practitioner review:

| Block type | Required | Optional | Family |
| --- | --- | --- | --- |
| Observation | Actor, Situation, Claim, Basis, Time | | Evidence |
| Finding | Actor, Situation, Claim, Basis, Strength, Time | Alternatives | Evidence |
| User flow | Actor, Situation, Claim (steps), Basis | Criterion | Evidence |
| Design decision | Claim, Rationale, Alternatives, Owner, Status | Criterion | Direction |
| Evaluation result | Actor, Claim, Basis, Strength, Criterion, Measure | Time | Evidence |
| Dependency | Claim, Owner, Status | Time | Open |
| Lesson | Claim, Situation, Basis, Strength | Actor, Time | Outputs |

## Rule 4: a block feeds a requirement category when it qualifies

A block is **eligible to count** toward a category when all three hold:

- it carries every component the category needs;
- it uses a relation the category accepts;
- its family is one the category accepts.

Eligible is not counted: a person still validates (D003, D004).

Configured per requirement area (`config/knowledge_components.json`). Relations are
read from the block's side of the link.

| Area | Needs | Accepts relations | Accepts families |
| --- | --- | --- | --- |
| Customer and user needs | Actor, Situation, Claim, Strength | supports, informs | Evidence |
| Experience and usability | Actor, Criterion, Measure | supports, informs, measures | Evidence, Outputs |
| Operations and support | Claim, Situation, Owner | supports, informs, constrains, depends on | Evidence, Direction, Open |
| Policy, access and boundaries | Claim, Situation, Basis | constrains, informs, supports | Evidence, Direction, Open |
| Outcomes and measurement | Measure, Time, Owner | measures, supports | Evidence, Direction |
| Technology and integration | Claim, Criterion, Owner | depends on, constrains, informs, supports | Direction, Open |

Missing components become coaching with a reason ("add who this applies to and it
will count toward User groups and needs"), never a mandatory form.

## Rule 5: links and packets are defined, not improvised

- **A link** is relation, target, target revision, conditions, use and reason.
- **A packet type** is an anchor, the relation types it follows, a depth, an audience
  scope and a revision policy (pinned or latest). Its contents are: follow those
  relations from the anchor to that depth, keep what the audience may see, apply the
  revision policy.
- **Membership is not dependency.** Being in the same packet never establishes a
  dependency. Chains run only through typed links and pinned references.

## Rule 6: services detect differences; reviewers judge them

- **Signature.** For block X and group G: every (relation, target revision,
  conditions, use) that G's published blocks and packets hold around X.
- **Detection (service, no model).** For groups sharing X, the service reports
  differences by kind, never by meaning: scope broadened, scope narrowed, different
  relation, different use, revision skew. Example: "Scope broadened: Design applies
  FIND-1 to all patients; Research scoped it to shift workers. Check applicability."
- **Judgment (reviewer).** The AI reviewer proposes whether a difference is
  compatible, unsupported or contradictory, with reasons; a person confirms. A broader
  use can be an unsupported expansion rather than a conflict.
- **Consequence (decision owner).** Material consequences go to the appropriate
  decision owner in Decisions & Issues. Nothing is resolved automatically.
- **Revision skew counts.** Two packets citing X at different revisions are not in
  agreement until someone reviews the newer one.
- **Mappings locate; they do not equate.** Identical identifiers match. Mapped
  identifiers (D009) locate related knowledge, and the mapping's type, direction and
  conditions decide permissible reuse:
  - *same as*: reuse within the mapping's conditions;
  - *narrower to broader*: evidence about the narrower concept is an instance of the
    broader one, never a generalisation (night-shift nurses are not all staff);
  - *broader to narrower*: reuse only where the broader claim's conditions hold;
  - *related*: locates only; transfers nothing.
- **Interpretations are records.** Adopting, narrowing or widening another group's
  block is saved as a typed link with its reason and conditions.
- Signatures and detected differences are computed by a service, not a model, so
  the same inputs always give the same result. Meaning is judged by reviewers.

## Rule 7: how the AI discerns and evaluates a packet

| Step | Who | What | Status |
| --- | --- | --- | --- |
| 1 Discern | AI proposes | Sorts new material into block types, fills components and link conditions, flags missing ones. Saved provisionally (Rule 8). | To build |
| 2 Check the structure | Service, no model | Components each category needs; packets pinned to old revisions; detected differences between groups; what an open challenge reaches. | To build (changed refs and bridge Built) |
| 3 Evidence coverage | Service | Counts contributions, teams, version, recency and open issues (D004, D012), and shows those facts and what would raise coverage. It measures coverage, not quality. Independent origins and applicability To build. | Built (counting); facts shown |
| 4 AI review | AI assesses | Assesses evidence quality against the claim and intended use: does each claim match its basis, does the basis reach the claimed scope, do texts contradict. Proposes a scoped assessment with reasons and how confident it is in its recommendation. | Partly built (reviewer); scope and basis checks To build |
| 5 People decide | Owner | Records the official confidence rating for a named use; new work prompts reassessment; readiness is a recorded human call. | Built |
| 6 Check before acting | Service | Immediately before any execution or delivery: the actor's current access and the current basis (pinned revisions still current, no new challenge). | Partly built (changed refs, access checks); one gate To build |

Signals are shown separately, never merged (D012): **confidence rating** (owner),
**evidence coverage** (counted) and **contributions from** (teams with published work
on the current version; publication is not validation).

**AI proposes a scoped assessment with reasons; the owner records the official
judgment.** Neither act makes unsupported evidence true.

**Low confidence alone does not block progress.** The contemplated action must stay
within its permissions, mandatory constraints and authorized limits.

## Rule 8: suggestions are provisional; confirmation where it matters

- AI suggestions (block types, components, link conditions) save provisionally,
  visibly marked with their origin and fully editable (D003). No click per suggestion.
- Confirmation is required when an interpretation materially changes scope,
  published meaning or a consequential commitment.
- Provisional suggestions never count toward coverage or feed a category. Publication
  is the validation point: before publishing, the person sees the suggestions their
  work contains and accepts them together (To build).

## What was built (26 November 2026)

| Step | What exists | Where | Limits |
| --- | --- | --- | --- |
| 1 Components and recipes | Fixed component set, recipes for all 16 block types, category needs for all six areas; validated on load | `config/knowledge_components.json`, `knowledge_components.py` | Starting tables for practitioner review. Owner is the author unless the type has an accountable-owner field |
| 2 Typed relationships | `relationships` table written in the same transaction as the record; idempotent backfill | `core.py`, `relationships.py` | Covers block links and contribution references to requirements; other body fields are not yet indexed. The NetworkX graph still uses `dependencies` |
| 3 Conditions on links | Every link stores its use (from the block's family); the editor offers the block's own Applies to as a suggested condition | `relationships.py`, `knowledge-cards.js` | The suggestion comes from the block's fields, not a model |
| 4 Difference detection | Signatures per group and differences by kind: scope differs, scope stated by one group, relation, use, revision skew | `knowledge_structure.py` | Groups are domains of shared blocks; meaning-layer mappings are not yet compared |
| 5 Feeds rule | Eligibility and coaching per block link; shown in the block editor and as items to look after in the block overview | `knowledge_components.py`, `knowledge-system.js` | Advisory; it does not change coverage |
| 6 Packet types and structure check | Three packet types with read-only preview (`packet-type-preview`); System checks in Decisions & Issues: differences, challenge reach, stale pins, category gaps | `knowledge_structure.py`, `bridge.js` | Packet types preview contents; issuing typed packets is not built |
| 7 AI review | The submission reviewer is told to check scope and basis and may return an optional scoped assessment, validated when present | `domain_submission.py` | Needs a live model connection; the UI does not yet display the scoped assessment |
| 8 Coverage origins | Low when current work cites no source; High needs 2 independent sources; facts show the count | `requirement_evidence.py` | An origin is a distinct released source that bears on the requirement: cited by a shared block linked to it, or by a contribution without blocks. A developer brief adds none. Quality is still judged by people |
| 9 Publication as validation | Suggested blocks can be selected; sharing lists them and requires acceptance; publishing marks them saved with who and when | `knowledge_cards.py`, `domain.py`, `domains.js` | Dismissed blocks still cannot be selected |
| 10 Check before acting | Delivery export rechecks the actor's permission and pinned versions; open challenges need an acknowledgment | `execution_gate.py`, `delivery.py`, `delivery.js` | Wired into delivery export only |

## Build order (as approved)

Done with revision 2 (presentation only): the signals are labelled "Evidence
coverage" and "Contributions from" in the prototype. All ten steps below were then
built on 26 November 2026; see the table above.

1. Components and recipes as configuration, reviewed by practitioners.
2. Typed relationships table, written in the same transaction as the record, and
   backfilled from existing body fields (changes how records are saved).
3. Conditions captured on links: AI-proposed, saved provisionally (Rule 8).
4. The deterministic difference-detection service, feeding the bridge.
5. Feeds rule and coaching on missing components.
6. Packet types and the structure check in step 2 of Rule 7.
7. AI review: scope, basis and quality against the claim and use, with a scoped
   assessment.
8. Coverage counts independent origins and applicable evidence (changes the D004
   calculation).
9. Publication as the validation point for provisional suggestions (Rule 8).
10. One check-before-acting gate for access and basis (Rule 7, step 6).

## Compatibility

No existing record type, field, publication rule, privacy boundary, decision right or
approval guard changes until a build step is approved. Existing typed links in block
bodies remain the source for the backfill.

## Revision history

- **Revision 1 (accepted 26 November 2026).** The original seven rules.
- **Revision 2 (accepted 26 November 2026).** Changed after review, because
  revision 1 let computations and matches stand in for judgment:
  1. The worked example moved from one quote straight to a prevalence finding; claims
     now need a basis that fits their reach (Rule 2).
  2. "Evidence level" overstated what counting establishes; renamed evidence
     coverage, with quality assessed against the claim and use. "Validated by"
     renamed contributions from, since publication is the only recorded event.
  3. The service classified conflicts; it now detects differences and reviewers
     judge them (Rule 6).
  4. Mapped matches were treated like shared ids; mappings now locate, and their
     type, direction and conditions decide reuse (Rule 6).
  5. "The AI never sets confidence" became: the AI proposes a scoped assessment; the
     owner records the official judgment (Rule 7).
  6. "Low confidence never blocks" gained an action boundary (Rule 7).
  7. "A person confirms every suggestion" became provisional suggestions, with
     confirmation for material changes and publication as validation (Rule 8).
  8. Added a current-access and current-basis check before execution (Rule 7).

## Open questions for the owner

Prepared with recommendations in [D014 owner questions](D014-owner-questions.md).

- Which relation types are required for a signature, and which are optional?
- Should complements be shown at all, or only conflicts?
- Who resolves a conflict between two groups: either lead, both, or the sponsor?
- Is revision skew a conflict or a lighter "needs review" state?
