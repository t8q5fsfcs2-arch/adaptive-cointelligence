# Adaptive Cointelligence: project instructions for Claude

## What this product does

Adaptive Cointelligence creates **adaptive intent through multiple people's
consequential work**. A sponsor states business intent. Research, Design and other
domains do their own professional work and publish consequential contributions.
Those contributions can challenge, refine or confirm the intent. Authorized people
decide what changes. The purpose endures while the plan adapts, and the record of
why it changed is never lost.

## Rule one: preserve function

The backend defines how the product works. UI, language and visual changes alter
how things look and read, never what the system does.

- Do not change record types, versioning, privacy boundaries, publication,
  decision rights or approval guards as a side effect of presentation work.
- A behavior change needs explicit approval from the user and a decision record.
- Every change must keep the full test suite and the launcher check passing:
  `python -m unittest discover -s tests`, `node --test tests/*.cjs` and
  `python run_demo.py --check`.
- Before reporting a phase complete, walk the core loop in the browser: sponsor
  intent, then domain work, then preflight and publication, then shared review,
  then an authorized decision, then the revised intent.

## Core principles (from the architecture)

- Business intake originates the requirement scaffold.
- Requirements provide continuity across the project lifecycle.
- Domain intelligence enters through consequential deliverables.
- Domain preflight precedes cross-domain reconciliation.
- The bridge identifies dependencies, contradictions, gaps and anticipatory
  information needs.
- AI proposes interpretations and changes; humans govern consequential decisions.
- Context packets preserve evidence, identity, relationships and lineage.
- Current views are selective projections, not destructive summaries.
- Processing is incremental, selective and computationally efficient.
- Knowledge is one system (D014): sources, a fixed set of components, building
  blocks as recipes of components, typed revision-pinned links, packets, and
  requirement categories. Teams vary block types, never components.
- Traceability comes from identifier matches; translation across groups comes
  from comparing their dependencies on the same identifier. Services detect
  differences; reviewers judge their meaning; decision owners settle consequences.
- Mappings locate related knowledge; their type, direction and conditions decide
  what may be reused. A claim needs a basis that fits its reach.
- A block is eligible to count toward a requirement category only when it carries
  the components, relation and family the category accepts; a person validates.
- Evidence coverage counts shared work; it is not quality. The AI proposes a scoped
  assessment with reasons; the owner records the official confidence judgment.
- Low confidence alone does not block progress; actions stay within permissions,
  mandatory constraints and authorized limits. Check current access and basis
  immediately before execution.

Read [the architecture overview](docs/architecture.md) before structural work.
The original full specification and earlier decision records are kept in a
private archive.

## Scope

The core demonstration is one project with business intake, Research and Design,
plus the configurable domain chassis and approved extensions recorded in earlier decisions. Do not add domains, agent networks or enterprise graph infrastructure
without explicit approval. The enterprise meaning layer approved in
[D009](docs/decisions/D009-meaning-governance.md) is in scope; it stays in SQLite. Before implementing, name the relevant architecture
sections, explain the fit, flag conflicts or scope expansion, make the smallest
viable change and test the affected invariants.

## Working agreement

- Synthetic data only. Do not import client material, credentials or partner code
  without explicit authorization.
- SQLite owns durable records, exact revisions, packet manifests and relationships.
  NetworkX is a rebuildable projection.
- Keep findings, proposals, decisions, requirements, evidence strength,
  publication and approval distinct.
- Human approval is explicit. Never infer it from a model response, a publication
  or a lack of objection.
- Models implement narrow interfaces and never own workflow state or permissions.
  No silent canned response when a live call fails. Never present mocked model
  behavior as live AI.
- Every consequential change preserves its predecessor and rationale. New evidence
  opens reconsideration; it does not silently replace requirements.
- Agents have a trigger, objective, input contract, permitted tools, output
  contract, limits and escalation condition. Deterministic work stays in services.
- Private domain material crosses into shared space only through an explicit
  permitted release. Test the shared audience, not just the requesting user.
- Research context: preserve the actor, job and situation, source basis,
  conditions and typed relationships that give a claim meaning. Packet membership
  does not establish dependency or approval.
- Keep runtime databases, uploaded sources and secrets out of Git.

## Git workflow

- This repository, `adaptive-cointelligence`, is the only home of this product. `main`
  is the lead branch and always holds the latest work.
- Work only in this repository and its local clone (`~/Developer/adaptive-cointelligence`).
  Never read from, write to, branch from or push to any other repository or folder,
  including earlier prototype repositories. If a task seems to need one, stop and ask.
- Commit in the user's local clone. Push to GitHub only when the user says so.
- Keep [the decision and action log](docs/log.md) current: add what was decided and
  what was done, with commits, in every round of work, newest first.

## Design approach

UI work starts from the user's task, then the information hierarchy, then the
simplest interaction. Distinguish group headings, item titles, content and quiet
metadata. Keep system mechanics (state machines, packets, versions) behind the
experience unless they change the user's next decision. Show expert detail
progressively. Domain work uses one shared interaction chassis, configured through
domain knowledge, vocabulary, criteria and authority. The AI partner supports
exploration; the reviewer assesses work against exact project expectations.
Ordinary exploration and review never modify the sharing draft or publish private
work, and they never become a mandatory form. Suggested content is universal and
follows [D003](docs/decisions/D003-suggestions-require-validation.md): visibly
suggested with its origin, fully editable, and counted only after the person
explicitly validates it. Anything a person works on in a workbench or in Business
Intent stays editable: they can edit, send it back to the AI partner and edit again,
repeatedly, and the AI partner never overwrites their text. Preserve existing features, data and accessibility while reducing
the effort to find, understand and act. Visually inspect the actual page at
desktop, tablet and phone widths before reporting completion; automated checks
do not establish visual quality.

## Decisions

Record approved product and architecture decisions in
[docs/decisions](docs/decisions/README.md). Propose architectural revisions for
human review before treating them as authoritative.
