# Architecture overview

This overview summarizes the original specification, the Requirement Centered
Context Adaptation Engine (Draft 1.0, October 2026), and the accepted increments
that followed. The full text is kept in a private archive. Its
proposed sections remain proposals until a recorded decision resolves them.

## Proposition

Organizations lose the reasoning behind work as it passes between sponsors,
researchers, designers and delivery teams. Adaptive Cointelligence keeps business
intent, evidence, decisions and resulting work connected, so that when new
learning changes the picture, people can see what needs reconsideration and who
has authority to decide.

Adaptive intent means carrying the purpose forward while allowing the
organization to revise its understanding of the problem, its proposed solution
and, when necessary, the business thesis itself. The record persists; the intent
adapts.

This is a testable hypothesis, not a validated product. Three levels of value are
measured separately: context integrity (reasoning stays reconstructable), decision
intelligence (teams see what another domain's work assumes, enables or puts at
risk) and delivery impact (earlier alignment reduces late discovery and rework).

## How it works

1. **Intent originates the scaffold.** A sponsor's business intent, goals and
   measures generate candidate requirements in drawers. Candidates are not
   approved obligations.
2. **Domains do consequential work.** Research, Design and other configured
   domains interpret the project through their own expertise and produce
   deliverables. One deliverable can affect many requirements; one requirement
   can draw on many deliverables. Unattached discoveries are valid.
3. **AI supports the work in the domain.** A partner helps the expert explore,
   question and draft. A reviewer challenges interpretations against exact
   project expectations. Applying a suggestion creates a new draft version; a
   conversational answer is never approval.
4. **Preflight prepares sharing.** At the expert's request, a selected version,
   its evidence, implications, limits and open questions are packaged and shown
   exactly before release. Deferred advice does not block valid publication.
5. **Publication releases a contribution.** Publishing makes work available for
   cross-domain review. It does not approve requirements or change intent.
6. **The bridge surfaces consequence.** Shared review compares pertinent
   contributions and raises dependencies, contradictions, gaps and anticipatory
   information needs. Mere similarity creates no task; missing information
   becomes a question, not an invented fact.
7. **Humans decide.** An authorized person approves, revises, rejects, defers or
   requests evidence. The decision records evidence, alternatives and affected
   requirements.
8. **Change propagates selectively.** Approved changes create new requirement and
   intent versions and trigger bounded rechecks of affected neighbors. Findings
   can return to the sponsor and revise the business intent itself.

## Objects that stay distinct

| Object | Meaning |
| --- | --- |
| Project | Continuing intent, scope, desired outcome and evolving context |
| Requirement | Stable identity for a needed condition, with versioned approved meaning |
| Requirement drawer | Workspace category for emerging and approved requirements |
| Source | Version-addressable original material: a brief, interview, policy or observation |
| Contribution | A domain's attributed observation, interpretation and limits, with exact source references |
| Context packet | A purpose- and audience-bounded selection of exact versions |
| Domain profile | Versioned vocabulary, rules, knowledge, authority and acceptance criteria |
| Domain deliverable | Consequential output that can affect one or many requirements |
| Reconciliation issue | A gap, tension, dependency, disagreement or ambiguity to resolve |
| Decision | Authorized act that changes, confirms, rejects or defers a proposal |
| Execution view | A context-resolved specification for a particular builder or team |

A requirement is not a packet. A semantic match is not a dependency. A domain
interpretation is not approved meaning. Publication is not approval. An execution
view is not the source of truth. Downstream objects never gain certainty merely
because a model generated them.

## Invariants

- Stable requirement identity; append-only, versioned contributions; branching
  lineage; a dynamically assembled current view rather than one mutable blob.
- Every claim is sourced or explicitly inferred. Typed impacts (supports,
  challenges, refines, introduces, constrains, depends-on, conflicts-with,
  validates, supersedes) are separate from their review state.
- Identity establishes contact; context determines the relationship; consequence
  determines whether action is needed.
- Private material crosses into shared space only by explicit permitted release.
  Access is checked before retrieval and generation, and on historical replay.
- Stale evidence cannot authorize a new change. Historical views reproduce the
  exact permitted basis.
- Processing is incremental: duplicate events do not duplicate commitments,
  unrelated inputs do not trigger broad reprocessing, and rechecks terminate.

## Implementation

- **Storage:** SQLite owns records, exact revisions, packet manifests and
  relationships. A NetworkX dependency graph is a rebuildable projection.
- **Server:** a Python standard-library HTTP server (`workbench.web`) with local
  accounts, project membership and role-based views. Static UI in
  `src/workbench/static`.
- **AI:** narrow model adapters (OpenAI, Anthropic) configured by an
  administrator per project. Without a connection, the product runs offline and
  labels scripted examples as such.
- **Implemented:** sponsor intake and Business Intent, requirement drawers and
  candidates, the shared Research and Design workbench with private chats,
  working briefs, outcomes reports and knowledge cards, preflight and
  publication, issues in Decisions & Issues and requirement reviews, decision
  rights, bounded AI partner reviews, decision receipts, simulated delivery
  staging, Design prototypes created in Figma, Research user flows created in
  FigJam, and import from FigJam, Figma and Lucid through each user's own
  connections.
- **Not yet implemented:** general automatic bridge matching across domains,
  incremental section-level extraction and automatic downstream scheduling.
  Semantic quality with live models has not been independently validated.
