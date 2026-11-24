# Developer guide

For backend and full-stack engineers who will connect the AI pipeline, build the
agents that move and manage knowledge, and make Adaptive Cointelligence resilient
enough to run for real teams.

Read this before changing code. It explains what people need from the product,
why that matters to an enterprise, how knowledge adapts as it moves between
domains, what the code already guarantees, and what is left to build.

**How to read the status labels**

| Label | Meaning |
| --- | --- |
| **Built** | Works in the prototype, covered by tests |
| **Partial** | A working slice exists; the production version needs more |
| **To build** | Specified here; no implementation yet |

Companion documents: [architecture overview](architecture.md),
[decision records](decisions/README.md), [demo walkthrough](demo.md),
[decision and action log](log.md), [project rules](../CLAUDE.md).

---

## Contents

1. [Why this exists](#1-why-this-exists)
2. [The model: two spaces and one boundary](#2-the-model-two-spaces-and-one-boundary)
3. [Adaptation of knowledge: the critical facet](#3-adaptation-of-knowledge-the-critical-facet)
4. [One project, end to end](#4-one-project-end-to-end)
5. [The system today](#5-the-system-today)
6. [Rules you must not break](#6-rules-you-must-not-break)
7. [Connecting the AI pipeline](#7-connecting-the-ai-pipeline)
8. [The agent layer to build](#8-the-agent-layer-to-build)
9. [What exists and what is missing](#9-what-exists-and-what-is-missing)
10. [Build order and proof](#10-build-order-and-proof)
11. [Open product decisions](#11-open-product-decisions)
12. [Glossary](#12-glossary)

---

## 1. Why this exists

### The problem

Work passes from a sponsor to researchers, designers and delivery teams. At each
handoff the reasoning thins out. Decisions are made in meetings and not captured.
A finding that should have changed the brief arrives after the build has started.
The same word means different things to two teams and nobody notices until
something breaks. When a new project starts, the organization cannot tell what
an earlier one learned, under what conditions, or whether it still holds.

AI makes this worse if it is fed the wrong context, or too much of it. An agent
given a stale requirement, or another team's private draft, or a similarity
match presented as fact, will act confidently on the wrong basis.

### What the product does

Adaptive Cointelligence keeps business intent, evidence, decisions and the
resulting work connected while all of them change. A sponsor states intent.
Domain experts do their own consequential work and publish what matters.
Their contributions can challenge, refine or confirm the intent. Authorized
people decide what changes. **The purpose endures, the plan adapts, and the
record of why it changed is never lost.**

Three ideas shape everything:

- **A place of reconciliation, not a place of work.** People keep working in the
  tools they already use. They bring the results in, true them up against the
  project and the enterprise, and publish what is ready.
- **Co-intelligence.** The AI brings suggestions and its reasoning. People decide.
  Nothing consequential is decided by a model.
- **Agents are orchestrators, not experts.** Agents move, select and package
  context. The researchers, designers and decision owners are the experts, and
  their expertise is captured as governed domain knowledge, not baked into an
  agent.

### Who uses it and what they need

| Person | What they are trying to do | What they need from the system |
| --- | --- | --- |
| **Sponsor** (business or product owner) | State why the work matters and what outcome counts as success | Guided intake that turns their documents into a clear, testable frame; honest feedback on weak spots; control over their own words |
| **Domain expert** (research, design, later QA and others) | Do professional work, test it against the project, share what is consequential | A private workbench, an AI partner grounded in their domain's standards, a clear view of what upstream work assumes, and an explicit, previewed way to publish |
| **Decision owner** | Decide what changes, within their authority | The exact proposal, its evidence and limits, the alternatives, who reviewed it and what it affects |
| **Domain lead or steward** | Keep their team's vocabulary, standards and methods current | A way to edit domain knowledge, set the boundaries of a meaning and agree mappings with other teams |
| **Administrator / semantic services** | Configure connections, rights and shared meaning across the enterprise | Settings for model and tool connections, decision rights, and a governed path for shared concepts |
| **Delivery receiver** | Build the right thing | A handoff that carries approved requirements, rationale, acceptance criteria, open issues and exact versions |

### Value to the enterprise

The value is measured at three levels, kept separate on purpose:

1. **Context integrity.** The reasoning behind any requirement can be
   reconstructed: who said what, on what evidence, who decided, and what it
   replaced.
2. **Decision intelligence.** Teams see what another domain's work assumes,
   enables or puts at risk before they commit.
3. **Delivery impact.** Earlier alignment means less late discovery and rework.

Around these sit three practical benefits:

- **Speed with quality.** Expert validation happens inside the flow of the work
  instead of as a separate, slow gate. The activity timeline shows where a
  decision has waited, which puts the onus on people to show up for shared
  decisions.
- **Accountability without blocking.** A team may move ahead on low confidence.
  That choice is recorded with its basis, so the consequence can be traced later.
  Confidence and accountability are different things (see section 2).
- **Learning that compounds.** A reviewed lesson from one project reaches the next
  one with its scope and conditions attached, so it is not mistaken for universal
  truth.

This is a hypothesis under test, not a validated product. Treat the three value
levels as things to measure.

### What it is not

- Not a replacement for research, design or delivery tools.
- Not an autonomous agent swarm. Agents prepare; services enforce; people decide.
- Not a single "source of truth" blob. Current views are projections over
  versioned records.
- Not a universal ontology. Each domain keeps its own meanings; shared meaning is
  agreed explicitly and kept small.

---

## 2. The model: two spaces and one boundary

Every rule in the system hangs off this picture.

```
        PRIVATE WORKBENCHES                              SHARED SPACE
  ┌──────────────────────────────┐                ┌──────────────────────────────┐
  │ Business Intent (sponsor)    │                │ Shared requirements          │
  │ Research workbench           │  ─ publish ─▶  │ (read-only, evolving)        │
  │ Design workbench             │   (explicit,   │                              │
  │ ...any configured domain     │    previewed)  │ Decisions & Issues        │
  │                              │                │ (issues, reviews, decisions) │
  │ prepare work, reconcile it   │  ◀─ context ─  │                              │
  │ against project and          │   (decisions,  │ hone alignment, decide       │
  │ enterprise context           │    new versions│                              │
  └──────────────────────────────┘    flow back)  └──────────────────────────────┘
```

### The workbench (private)

Each person or team works in their own domain's workbench. It is where they
prepare their work and reconcile it against the project's and the enterprise's
context.

- Bring work in from any tool (upload, or import from FigJam, Figma or Lucid
  through the user's own connection).
- Talk it through with the AI partner, which is grounded in the domain's
  vocabulary, standards and methods and in the exact project basis.
- Shape it into a working brief, an outcomes report and knowledge cards (units of
  knowledge with their dependencies).
- The interface is a cockpit ([D010](decisions/D010-workbench-cockpit.md)): the
  conversation and the work stay dominant; next moves, suggestions, reviews and
  updates sit on a rail at hand. AI suggestions arrive quietly with replies and
  can be dismissed ([D011](decisions/D011-quiet-ai-suggestions.md)).

Rules inside the workbench:

- Nothing here is visible to other teams.
- The AI partner never overwrites the person's text. It suggests; the person
  applies, edits, sends back and edits again, as often as they like.
- A suggestion counts only after the person explicitly validates it
  ([D003](decisions/D003-suggestions-require-validation.md)).
- Exploration and review never publish anything and never modify the sharing
  draft.

### The boundary (publication)

The only way anything crosses from a workbench to the shared space is an explicit
publication by its owner:

1. **Preflight.** The owner asks to prepare sharing. The system pins the exact
   draft version, its evidence, the linked requirements and goals, and the
   author's statement of implications, downstream needs and open questions into a
   prepared context packet. Nothing is published yet.
2. **Preview.** The owner sees exactly what will leave, including any private
   source text that would be released.
3. **Publish.** On confirmation, the system re-checks that nothing changed since
   preflight, releases the selected sources and interpretations, and writes the
   published contribution into project scope.

Publishing makes work available for review. It does not approve a requirement
or change intent.

### The shared space

Everyone on the project sees the same interface, with content tailored to them.

- **Shared requirements** are the project's commandments: read-only and evolving.
  They start as candidates with low confidence and firm up as research and design
  contribute. Only ratified decisions change them.
- **Decisions & Issues** is where alignment is honed. Issues (challenge,
  conflict, gap, dependency, question) are raised against exact records, answered,
  and resolved through proposals, reviews and decisions. Each person sees what
  needs their attention: decisions that affect their work, what others published,
  who is working (people and agents).
- **Decisions** are explicit acts by an authorized person: approve, reject or
  defer, with rationale. Decision rights are configurable; a domain may require a
  formal approver or allow a pod to decide.

### The return path

A decision creates new versions (a requirement, sometimes the intent itself) and
new packet versions. Those flow back into every workbench as updated context.
Work that depended on the old version is flagged for reconsideration. Nobody's
work is rewritten silently.

### Confidence is not accountability

- **Confidence** is how well-supported something is. It is expected to be low
  early and to rise as evidence arrives. In the code this shows as evidence levels
  per requirement and area ([D004](decisions/D004-requirement-evidence-level.md)).
- **Accountability** is who decided what, on which basis. A team can proceed on low
  confidence; the readiness call records that choice, by whom and on what basis
  ([D008](decisions/D008-readiness-decision-record.md)).

Each requirement shows three signals together and never merged: the recorded
confidence rating, the computed evidence level, and which teams have published
work on the current version ([D012](decisions/D012-confidence-signals.md)).

Never derive one from the other. A high-confidence finding is not approved. An
approved requirement is not thereby well-evidenced.

---

## 3. Adaptation of knowledge: the critical facet

Storing knowledge is easy. Keeping it **correct while it changes, as it moves
between domains, toward a common end point** is the hard part, and it is what the
agent layer exists to do.

### The common end point

All domains converge on one thing: a handoff that a delivery team (or an
operating owner, for non-software outcomes) can trust. It carries ratified
requirements, the rationale, acceptance criteria, open issues and the exact
versions they rest on. Every adaptation along the way must keep that handoff
traceable to the intent that started it.

### Three kinds of change, three different responses

| Kind of change | Example (clinic project) | What the system does |
| --- | --- | --- |
| **Perspective** | The sponsor and the researcher look at the same requirement | Different explanation and emphasis. Facts, rights and versions unchanged. |
| **Applicability** | "Appointment" means a booked slot to Operations and a clinical encounter to Research | Select the valid meaning for this task and record which one was used. Both meanings can stay valid. |
| **Knowledge** | Research finds most missed visits are known in advance, not forgotten | Prepare a proposal against the exact version. Review it. Only an authorized decision creates a successor version. |

A view change never rewrites history. A retrieved claim never becomes accepted
knowledge by being retrieved.

### Meaning differs across domains, legitimately

Each domain has its own dialect. The same word can carry different meanings and
values. Domain knowledge records, per term:

- what it **includes** and **excludes**, and what it should **not be confused with**;
- its **reach**: this project, this team's domain, named domains, or the
  enterprise.

Leads can set reach up to their own domain. Wider reach needs a proposal and
approval: mapping a term between two teams needs both leads; sharing a term to the
enterprise needs a domain lead and a steward, as two different people. Semantic
services can facilitate but never decide
([D009](decisions/D009-meaning-governance.md)). Active boundaries are fed to the
AI partner as guidance, so it can say "you mean X; Operations means Y".

### Units of knowledge carry their dependencies

A finding on its own is a sentence. A finding with links to the users, product,
requirement and project it concerns is a unit of knowledge that can be found,
compared and trusted later. That is what lets a future query tell what happened in
one project from another, even when the same idea appears in both.

In the code:

- Every record has a stable identity and immutable revisions (`Ref(id, revision)`).
- Dependencies point from a revision to the exact revisions it rests on.
- Knowledge cards and need contexts (people, job, situation, triggers, pains,
  gains, boundaries, dependencies) structure what experts produce.
- Typed relationships (supports, challenges, refines, depends-on, constrains,
  measures, decision-needed) stay separate from their review state.

### How change travels

```
new evidence ─▶ proposal against exact version ─▶ review ─▶ decision
                                                              │
        ┌─────────────────────────────────────────────────────┘
        ▼
 new requirement / intent version + decision record + new packet version
        │
        ▼
 dependents of the OLD version are found (recorded dependencies only)
        │
        ▼
 flagged for their owners to reconsider ─▶ owners decide; nothing auto-rewritten
```

Packets pin exact versions. When resolved later, a packet reports which of its
references have newer versions (`changed_refs`), but never swaps them in.

### What "resilient" means here

The system is resilient when all of these survive:

| Threat | What must hold |
| --- | --- |
| Model fails, times out or returns junk | The person's message and files are kept; the failure is shown; nothing canned is substituted; nothing is saved as if the model answered |
| Two people edit the same record | The second write fails on the expected-revision check and must be redone against the current version |
| The basis changes while an agent is working | The result is rejected at save time and the person is asked to look again |
| An approval arrives for a version that has since changed | The decision is blocked (stale basis) |
| An event is delivered twice | No duplicate commitment (same publication or packet signature is refused) |
| A person leaves or a role changes | Every decision records who, with what authority, on which version |
| A meaning changes | Old decisions stay interpretable under the meaning they used; new work uses the new one |
| Access is revoked | Use is re-checked at read time; packets cannot grant access by declaring an audience |

Most of these already hold in the prototype (section 6). The agent layer must
keep them holding when work becomes asynchronous and distributed.

---

## 4. One project, end to end

The demo project is Riverbend Health, a synthetic clinic. Every person, source and
dialogue is invented. Run it with `python3 run_demo.py` and switch people from the
header menu. `python3 run_demo.py --check` replays it in disposable data using the
real services (`src/workbench/clinic_demo.py`).

| Step | What happens | Space | Commands and records involved |
| --- | --- | --- | --- |
| 1. Intent | Dana (sponsor) wants missed appointments cut from 18% to 10% and proposes an AI reminder assistant | Business Intent workbench | `intake-start`, `intake-save`, `goals-save`, `intake-preflight`, `intake-publish` → `intake-case`, `intent`, `goal`, `success-measure`, `requirement-drawer`, candidate `requirement` |
| 2. Research | Jordan maps the rescheduling journey and interviews patients and staff. Finding: most people who miss already knew; rescheduling needs a phone call in office hours | Research workbench, then publication | `domain-source`, `domain-chat-*`, `domain-prepare`, `domain-publish` → `domain-handoff`, prepared packet, `contribution`, released `source` |
| 3. Intent adapts | Jordan asks Dana to revise the problem statement, citing the finding. Dana adopts it and republishes. Intent moves to version 2; version 1 is kept | Shared space, then Business Intent | `intent-refine`, `intent-adopt`, `intake-publish` → `intent-refinement`, `intent` v2 |
| 4. Design | Mei generates three concepts into Figma, evaluates them, and raises a dependency: some visit types need staff | Design workbench, then publication | `domain-prototype-*`, `domain-submission-*`, `domain-publish`, `bridge-raise` |
| 5. Decisions & Issues | Mei asks Research for visit-type rules; Jordan answers; Mei publishes a revised concept with a staff handoff | Shared space | `bridge-respond`, `bridge-close` → `bridge-issue`, `bridge-issue-event` |
| 6. Decision | Sofia (requirement owner) proposes requirement v2; Research and Design review; Sofia approves | Shared space | `proposal`, `review`, `decision` → `decision-case`, `human-review`, `decision`, `requirement` v2, packet v+1 |

The point of the story is step 3: evidence from a domain changed the business
intent itself, through the sponsor's own decision, with both versions retained.

---

## 5. The system today

### Stack

| Part | Choice |
| --- | --- |
| Language | Python 3.12, standard library HTTP server |
| Storage | SQLite (one database per project, plus a separate enterprise store) |
| Graph | NetworkX, built on demand from recorded dependencies; rebuildable |
| UI | Vanilla JavaScript and CSS in `src/workbench/static`; strict CSP (no inline styles) |
| Models | Narrow adapters for OpenAI and Anthropic, configured by an administrator |
| Tools | Read-only MCP imports from FigJam, Figma and Lucid using each user's own credentials |

### Run and test

```sh
python3 run_demo.py                                  # serve the demo
python3 run_demo.py --check                          # launcher check: full workflow in disposable data
PYTHONPATH=src python3 -m unittest discover -s tests # Python suite
node --test tests/*.cjs                              # UI suite
```

All three must pass on every change. Then walk the core loop in the browser at
desktop, tablet and phone widths: sponsor intent, domain work, preflight and
publication, shared review, an authorized decision, the revised intent.

### Code map

| Area | Files |
| --- | --- |
| Record store, packets, dependency graph, impact worker | `core.py` |
| Browser command surface and project state | `workspace.py` (composes the services below; `Workspace.command` is the single entry point) |
| HTTP, accounts, sessions | `web.py`, `access.py`, `settings.py` |
| Business intent | `intake.py`, `intake_coach.py`, `sponsor.py`, `goals.py`, `scaffold.py`, `scaffold_tailoring.py`, `refinements.py`, `business_assessments.py` |
| Requirements | `requirement_assistant.py`, `requirement_assessments.py`, `requirement_evidence.py`, `resolution.py`, `readiness.py` |
| Domain workbenches | `domain.py`, `domain_chat.py`, `domain_brief.py`, `working_report.py`, `domain_submission.py`, `knowledge_cards.py`, `need_contexts.py`, `design_visual.py`, `prototype_workflow.py`, `flow_export.py`, `tool_imports.py` |
| Domain knowledge and meaning | `domain_knowledge.py`, `domain_interpretation.py`, `meaning.py`, `enterprise.py`, `adoption.py` |
| Publication and packets | `domain.py` (`prepare`, `publish`), `packet_preparation.py`, `need_contexts.py` |
| Decisions & Issues | `bridge.py`, `decisions.py`, `decision_rights.py`, `decision_review.py`, `decision_receipts.py`, `project_timeline.py`, `team_timeline.py` |
| Delivery | `delivery.py`, `developer_brief.py`, `demo_delivery.py` |
| AI boundary and agents | `model_provider.py`, `model_connection.py`, `agent_catalog.py`, `agent_runs.py`, `agent_quality.py`, `quiet_suggestions.py`, `config/agent_personas.json` |
| Integrity review (business intent and requirements) | `integrity*.py` |

### The store contract

`Store` (`core.py`) is the heart of the system. Learn it first.

```python
ref = store.put(id, kind, scope, body, expected_revision=0)  # append a revision
rec = store.read(Ref(id, revision), allowed_scopes)          # exact revision, scope-checked
rec = store.latest(id, allowed_scopes)                       # newest revision
store.depend(dependent_ref, basis_ref, allowed_scopes)       # record a dependency
g   = store.graph(allowed_scopes)                            # rebuild NetworkX projection
m   = store.packet(id, rev, purpose, refs, audience, requester_scopes)
r   = store.resolve_packet(id, rev, allowed_scopes)          # exact contents + changed_refs
with store.transaction(): ...                                # one command, one transaction
```

What it guarantees:

- **Append-only.** A revision is never updated or deleted.
- **Optimistic concurrency.** `put` fails with `StaleBasis` unless
  `expected_revision` equals the current revision. The check and insert are
  atomic (`BEGIN IMMEDIATE`).
- **Kind and scope are fixed.** A record cannot change kind or scope in a later
  revision; moving across a boundary is a separate, reviewed release that creates
  a record in the new scope.
- **No existence leaks.** Absent and inaccessible records raise the same error.
- **Packets cannot widen access.** The audience must be a subset of the
  requester's scopes, and every reference is read as the audience.

### Scopes

| Scope | Holds |
| --- | --- |
| `project:demo` (`SCOPE`) | Shared project records: published contributions, requirements, decisions, issues |
| `intake:sponsor` (`PRIVATE`) | The sponsor's private Business Intent drafts |
| `domain:research`, `domain:design`, ... | Each domain's private workbench records |

A workspace's scopes come from the signed-in person's role and domain
membership, never from the client.

### Record families

There are many record kinds. The important families:

| Family | Kinds (examples) | Scope |
| --- | --- | --- |
| Intent | `intake-case`, `intake-draft`, `intent`, `intent-refinement`, `goal`, `value-acceptance` | private, then project |
| Requirements | `requirement`, `requirement-drawer`, `requirement-assessment`, `readiness-decision` | project |
| Domain work | `domain-conversation`, `domain-chat-turn`, `domain-chat-review`, `contribution-draft`, `domain-submission`, `knowledge-card`, `need-context` | domain |
| Boundary | `domain-handoff`, prepared packets, `domain-publication`, released `source`, `contribution` | domain → project |
| Decisions & Issues | `bridge-issue`, `bridge-issue-event`, `decision-case`, `human-review`, `decision`, `decision-rights` | project |
| Meaning | `domain-knowledge`, `meaning-proposal`, `enterprise-concept`, `enterprise-proposal`, `enterprise-adoption` | domain, project, enterprise store |
| AI operations | `agent-execution`, `agent-quality-evaluation`, `suggestion-preferences` | the scope of the work |
| Delivery | `delivery-draft`, `developer-brief`, `demo-delivery-receipt` | project |

Keep findings, proposals, decisions, requirements, evidence strength, publication
and approval as distinct records. Never merge two of them into one status field.

### Commands

The browser posts an action name and data to `/api/state`; `Workspace.command`
dispatches to a service method. Consequential actions (decisions, decision-rights
actions, intent adoption and disposition, intake publication and close) run inside
one transaction with a Decisions & Issues guard before and a sync after.

To add a command: write the service method, take `expected` references for
anything it changes, validate input with `validation.py`, register it in the
action table, and test both the success path and the stale and unauthorized
paths.

### HTTP endpoints

`/api/state` (project state and commands), `/api/auth`, `/api/home`,
`/api/portfolio`, `/api/portfolio-access`, `/api/enterprise`,
`/api/decision-rights`, `/api/model-connections`, `/api/admin-integrations`,
`/api/admin-announcements`, `/api/project-agent-activity`, `/api/my-files` (and
related), `/api/design-page`.

Accounts are local and loopback-only. One account binds to one actor; membership
never follows a client-posted role. Enterprise identity (SSO) is to build.

---

## 6. Rules you must not break

These are the system's contracts. Each is enforced in code today. Your
production build, including any agent layer, must keep every one.

| # | Rule | Where it is enforced now |
| --- | --- | --- |
| 1 | Every consequential change preserves its predecessor and rationale | `Store.put` (append-only); decisions record `supersedes` and rationale |
| 2 | A write must name the version it changes | `expected_revision` on `Store.put`; `expected` references on commands |
| 3 | Private material crosses into shared space only by explicit, previewed, owner-confirmed release | `domain.py` `prepare` / `publish`; `confirm` and `release_sources` flags |
| 4 | Test the shared audience, not just the requester | `Store.packet` audience check; `resolve_packet` reads as the audience |
| 5 | Stale evidence cannot authorize a change | `DecisionLoop._fresh`; review `basis_fingerprint` must match the case basis |
| 6 | Human approval is explicit; never inferred from a model, a publication or silence | Decisions require a disposition and rationale; approval also requires `confirm`; deferral needs a named next owner and question |
| 7 | Decision rights are checked at decision time | `DecisionRights.authorize` inside the decision transaction |
| 8 | Models never own workflow state or permissions | Models only return output; services validate and write |
| 9 | No silent canned response when a live call fails | `domain_chat.py` records an error turn; `execution_mode` labels live, simulated, not connected |
| 10 | Never present mocked model behaviour as live AI | `agent_runs.execution_mode`: only real adapters count as live |
| 11 | Suggestions count only after explicit validation | Apply actions require `confirm`; suggestion states in the UI |
| 12 | The AI partner never overwrites a person's text | Suggestions are separate records; apply creates a new draft version |
| 13 | Packet membership does not establish dependency or approval | Packets hold references only; dependencies are separate rows |
| 14 | New evidence opens reconsideration; it does not replace requirements | Impact worker returns affected references with `pending-human-review` |
| 15 | Duplicate requests do not duplicate commitments | Publication and packet signatures; same signature is refused |
| 16 | Source content is data, never instructions | `GUARDRAILS` in `domain.py`; no tools or writes available to the model |
| 17 | Synthetic data only in this repository | Demo data is authored; no client material, credentials or partner code |

If a change you need would bend one of these, stop and raise it for a decision
record. Behaviour changes need explicit approval.

---

## 7. Connecting the AI pipeline

### The model boundary

All model access goes through one protocol (`model_provider.py`):

```python
class ModelProvider(Protocol):
    def status(self) -> dict: ...
    def generate(self, *, instructions: str, context: dict, schema: dict) -> dict: ...
```

- `instructions`: the agent's contract (for example `GUARDRAILS` in `domain.py`),
  plus task-specific additions.
- `context`: the exact, scope-checked basis the service assembled. The model gets
  nothing else: no browsing, no tools, no database.
- `schema`: the JSON shape the output must match.
- `generate` returns `{"output": ...}` or raises `ModelUnavailable` with a safe,
  user-facing message. Provider error bodies and credentials are never exposed.

Adapters: `OpenAIModel` (also `generate_visual` for page images),
`AnthropicModel`, `UnconfiguredModel`. Connections are managed per project by an
administrator (`model_connection.py`); keys stay server-side.

### The pattern every AI operation follows

```
service assembles context (exact refs, scope-checked)
   → AgentRun receipt opened (agent, version, skill, basis, config fingerprint, mode)
   → model.generate(instructions, context, schema)
   → service validates output against schema and context (IDs must exist, limits hold)
   → service re-checks the basis fingerprint; if it changed, reject
   → service saves output as a separate record, records dependencies
   → receipt completed (duration, usage, cost) or failed (error)
```

The domain AI partner (`DomainAgent` in `domain.py`, used by `domain_chat.py`) is
the reference implementation. Copy its shape.

### Output contract of the AI partner

Each reply returns a summary, at most two strengths and at most four
consequential suggestions. Each suggestion has one focused question and a
direction: **evidence** (quality and meaning within the domain), **intent**
(implications for intent or requirements) or **next-domain** (what another team
may need). Empty suggestions are valid. Only supplied requirement IDs may be
cited. These suggestions are what the cockpit's Suggest instrument surfaces.

### Failure behaviour

When the model is unavailable, times out, or returns output that fails
validation:

- the person's message and files are already saved;
- an error turn is recorded with a plain message;
- nothing is saved as if the model had answered;
- the UI shows that the AI partner is unavailable.

Do not add retries that hide failure from the person. A retry policy, if added,
belongs in the controller (section 8) with a budget and a visible outcome.

### Execution receipts and quality

Every model call writes an `agent-execution` record (`agent_runs.py`): agent and
version, skill, purpose, actor, basis, configuration and its fingerprint,
provider, model, mode, duration, usage, cost, output reference or error. Receipts
are operational facts, not quality scores. Expert-quality evaluation is separate
(`agent_quality.py`) and stays human-reviewed.

### Adding a provider

Implement `status` and `generate`, map provider errors to `ModelUnavailable` with
safe messages, honour the request timeout, return structured output that matches
the schema, and add the class to `execution_mode` only if it is a real adapter.
Never let a configuration flag turn a test double into "live".

---

## 8. The agent layer to build

This is the main engineering job: agents that orchestrate the **movement and
management of knowledge** across the two spaces, asynchronously and safely.

### Principles

- **Agents propose; services enforce; people decide.** An agent never commits,
  publishes, approves or grants access.
- **Deterministic work stays in services.** Routing, permission checks, version
  checks, dependency tracing and packet assembly are code, not prompts.
- **Every agent has an execution contract** (below). No contract, no run.
- **The controller owns run state.** Agents are stateless between invocations.
- **Start with the fewest agents the workflow needs.** Add one only when its work
  and its evaluation criteria are clear.

### The execution contract

Every agent is registered with:

| Field | Meaning |
| --- | --- |
| Trigger | The event that may start it (it requests evaluation; it never proves a change is valid) |
| Objective | What it is for, in one sentence |
| Input contract | The exact context it receives, assembled and scope-checked by a service |
| Permitted tools | An allowlist, checked by a service outside the model |
| Output contract | A JSON schema; outputs are proposals with citations and uncertainty |
| Limits | Maximum steps, time and cost; maximum repairs |
| Stop and escalation | When to stop, and which human owner receives the case |

The persona inventory in `config/agent_personas.json` already records trigger,
inputs, skills, output and boundaries for fourteen roles. `agent_catalog.py`
reports, in code, which are implemented. Extend that inventory; do not create a
parallel one.

### Agent roster

| ID | Role | Moves knowledge from → to | Status |
| --- | --- | --- | --- |
| P01 | Supervisor | Proposes a plan for a complex task; the controller enforces it | To build (routing is in code today) |
| P02 | Intake AI partner | Sponsor documents → a clear, testable business frame | **Partial**: live intake partner with seven skills and question-specific expertise |
| P03 | Context assistant | Enterprise and domain guidance → the sponsor's view | To build |
| P04 | Requirement assistant | Intent → candidate requirements, criteria, goals, measures | **Partial**: drafts and reviews; proposals need human review |
| P05 | Extraction worker | Raw sources → attributed passages | Partial (ordinary code extracts text; no model role) |
| P06 | Evidence AI partner | Research work ↔ evidence standards and project basis | **Partial**: shared domain-coach runtime |
| P07 | Domain context AI partner | Any domain's work ↔ its vocabulary, standards, methods | **Partial**: shared domain-coach runtime, configured per domain |
| P08 | Mapping assistant | One domain's meaning ↔ another's | To build (human mapping proposals exist, D009) |
| P09 | Reconciliation assistant | Published positions → a cited delta for Decisions & Issues | To build |
| P10 | Impact assistant | A proposed change → who and what is affected | Partial (code follows recorded dependencies; no model role) |
| P11 | Options assistant | Positions → an even-handed options comparison | To build |
| P12 | Artifact / fit assistant | Delivered artifact ↔ agreed requirements | **Partial**: design visual review of PDF pages |
| P13 | Change analyst | A changed basis → affected decisions and packets | To build |
| P14 | Ratification coordinator | Decision records, unambiguous | Code handles gates; no model role needed |

### Components to build around the agents

#### Controller (orchestrator) (To build)

Owns every run's lifecycle: queued → running → waiting for input or review →
resumed → completed, failed or cancelled. Checks identity, project, workflow
state and allowed actions before any run. Chooses the registered task pattern;
routine tasks skip AI planning. Enforces budgets, checkpoints, retries and
escalation. Records concise reasons, not hidden model reasoning.

`agent_runs.py` already writes durable receipts; extend it into run state rather
than starting over.

#### Event intake and outbox (To build)

Today a command's writes happen in one transaction, but there is no event
stream. Add:

- an **outbox table** written in the same transaction as the record change, so a
  commit and its event can never drift apart;
- an **event intake** that deduplicates by event ID and turns events into task
  requests for the controller;
- events for at least: intent published, contribution published, issue raised or
  answered, proposal submitted, decision recorded, domain knowledge changed,
  access changed.

#### Recipe compiler (To build)

Turns the current ingredients (intent version, open drawers, contributions,
questions, applicable domain knowledge, the task, the as-of time, the person's
permitted access) into a **recipe**: a versioned plan of queries, evidence
criteria, agent assignments, stop conditions and output schemas. The recipe is the
plan; the packet is what was actually assembled. Both are kept.

#### Governed retrieval API (Partial)

One read point for every agent and service:

1. exact record lookups by ID and version (Built: `Store.read`, `latest`);
2. recorded dependencies and typed links (Built: dependencies table, graph
   projection);
3. keyword search over permitted text (To build);
4. vector similarity over permitted passages (To build, optional at first);
5. eligible prior packets (Partial: `packet_manifests`).

Every result returns IDs, versions and source spans, and is re-checked against
the caller's scopes before use. Similarity ranks candidates; it is never
authority, truth or dependency. Three hits on one source are one source.

#### Reconciliation service (To build)

Inside the shared space, coordinated by the controller:

1. pair comparable claims (entity, predicate, value, unit, population, scope,
   effective time) using governed mappings;
2. run deterministic checks (IDs, versions, units, dates, current approval state,
   access);
3. ask P09 to analyse support, contradiction and alternative readings using both
   source spans;
4. classify each pair: **same / supporting**, **different scope or time** (both
   valid; keep qualifiers), or **conflict / unknown** (route to the decision
   owner);
5. persist the comparison with its basis, and raise an issue in Decisions & Issues
   when a decision is needed.

There is no automatic winner: newest, most similar, most repeated or
sponsor-approved does not by itself mean best supported.

#### Packet registry and change propagation (Partial)

Built: packets with purpose, audience and exact references; `resolve_packet`
reports `changed_refs`; requirement impacts are computed from the graph in
`Workspace.state`.

To build:

- a **reverse index** from each referenced record to the packets that use it;
- on a committed change, mark exactly those packets stale and enqueue a rebuild
  task for their owners;
- validity, expiry and the recipe that produced each packet;
- recheck of access at use time, not only at assembly.

#### Tool policy gate (Partial)

Built: read-only MCP imports per user (`tool_imports.py`); project context is
never sent to the tool server.

To build: a gate between any agent and any tool that checks the tool, its
parameters, the delegated scope and read/write class before the call; per-project
connector settings an administrator can switch on and off; receipts for every
call. MCP carries the exchange; it does not grant permission. A direct API adapter
is equally valid behind the same gate.

#### Learning service (To build)

Links outcomes to the intent, decision and action they came from; proposes a
scoped lesson with population, method, counterexamples and applicability limits;
routes it through the same review and decision path; makes it retrievable for the
next project, where the receiving owner adopts, adapts, declines or defers. Repeated
summaries of one source are not independent cases.

### Handoff states are not synonyms

Track these separately everywhere: prepared → submitted → accepted for processing
→ committed → delivered → acted on → outcome observed. A successful API call proves
a bounded write, not delivery, adoption or business value.

---

## 9. What exists and what is missing

| Capability | Today | Status | Next step |
| --- | --- | --- | --- |
| Versioned records, optimistic concurrency | `core.Store` | Built | Port the same contract to the production database |
| Scoped access, no existence leaks | `Store.read`, workspace scopes | Built | Map scopes to enterprise identity and groups |
| Business intent intake with AI partner | `intake*.py`, P02 | Partial | Retrieval of domain guidance (P03) |
| Requirement drawers, candidates, evidence levels, confidence signals | `requirement_*`, D004, D012 | Built | AI-drafted reassessment for the owner to confirm |
| Private domain workbenches, cockpit, quiet suggestions | `domain*.py`, D010, D011 | Built | Live-model evaluation with experts |
| Building blocks (families, per-team types), need contexts | `knowledge_cards.py`, `need_contexts.py`, D013 | Built | Type list reviewed by domain experts |
| Preflight and publication | `domain.prepare/publish`, `packet_preparation.py` | Built | Emit publication events (outbox) |
| Issues in Decisions & Issues | `bridge.py` | Built (human-raised) | Reconciliation service proposes issues |
| Proposals, reviews, decisions, decision rights | `decisions.py`, `decision_rights.py` | Built | Configurable approval models per domain at scale |
| Readiness call | `readiness.py`, D008 | Built | None for now |
| Meaning boundaries, reach, mappings, enterprise concepts | `meaning.py`, `enterprise.py`, `adoption.py`, D009 | Built | Decide whether adopted concepts reach the AI partner |
| Packets with exact references | `Store.packet`, `resolve_packet` | Built | Registry, reverse index, validity, recipes |
| Change impact | `ImpactWorker`, graph projection | Partial | Stale marking and owner tasks via events |
| Model boundary and receipts | `model_provider.py`, `agent_runs.py` | Built | Model gateway, budgets, central observability |
| Agent execution contracts | persona inventory, `agent_catalog.py` | Partial | Enforce contracts in a controller |
| Controller and run state | receipts only | To build | Section 8 |
| Event intake and outbox | none | To build | Section 8 |
| Recipe compiler | none | To build | Section 8 |
| Retrieval API (keyword, vector) | exact and graph only | Partial | Section 8 |
| Reconciliation service | none | To build | Section 8 |
| Tool policy gate, connector settings | read-only per-user imports | Partial | Section 8 |
| Learning service | none | To build | Section 8 |
| Delivery handoff | export only; never simulates external writes | Partial | Versioned contract with the delivery tool; receipts per item |
| Enterprise identity (SSO), hosting, operations | local accounts | To build | Platform decision |

---

## 10. Build order and proof

### Prove one complete loop before expanding

Build the durable foundation first; add integrations only when the loop works.

1. **Contracts in the prototype.** Small, testable pieces that fix the rules your
   production build must honour:
   - outbox written in the same transaction as each consequential change, plus
     reverse-dependency stale marking;
   - one enforced agent execution contract and run states, extending `agent_runs`;
   - a retrieval interface with exact lookup today and a labelled slot for keyword
     and vector search;
   - a behaviour test pack (below).
2. **Production foundation.** The same store contract on the chosen relational
   database, enterprise identity, model gateway, controller and event intake.
3. **First agent loop.** One sponsor brief → one evidence source → one attributed
   proposal → one authorized revision → one renewed packet, with the reviewer and a
   later recipient able to see what changed, why, who agreed and what remains
   uncertain.
4. **Reuse and operability.** A second task reuses the same contracts. Test stale
   context, denied access, missing evidence, a changed owner and failed delivery.
5. **Connect what earns its place.** Add the highest-value connector or delivery
   adapter only after support and correction ownership are agreed.

### Behaviour test pack (acceptance for any rebuild)

Each must pass on the prototype and on the production build:

- A domain draft is invisible to another domain and to the shared audience until
  published.
- Publishing requires the exact preflight; a changed draft forces a new preview.
- A private source is released only with explicit confirmation.
- A packet cannot be assembled for an audience the requester does not hold.
- Two writes against the same version: the second fails and nothing is lost.
- An approval against a changed basis is blocked.
- A review that does not cover the current basis cannot clear a decision.
- The same publication or event delivered twice creates one commitment.
- Two valid meanings of one term stay distinguishable in retrieval and in the AI
  partner's guidance.
- A failed model call saves the person's input, records an error and returns no
  invented content.
- A simulated model is never labelled live.
- A decision change marks exactly the dependent packets stale, and no others.
- A deferral without a named owner and question is refused.

### Measures to agree before testing

Time to an accepted handoff; missing or incorrect requirements found late;
clarification and review effort; reuse quality; packet traceability; access
failures; end-to-end latency and cost. Compare against the team's current method.

### Not yet

A universal ontology, every possible requirement drawer, a broad connector estate,
automatic ratification, autonomous consequential actions, or a dedicated graph
database before a proven need.

---

## 11. Open product decisions

These need the product owner, not engineering judgment. Do not settle them in
code.

- **Knowledge block types.** The families and types in
  [D013](decisions/D013-knowledge-block-families.md) are a starting point; research
  and design practitioners should review them.
- **Connector control.** Whether connectors are switched on and off by the project
  administrator only, or also by individual users.
- **Adopted meaning in the AI partner.** Whether adopted, shared and mapped
  concepts are fed to a team's AI partner.
- **"Needs your attention."** The call to action each item leads to.
- **Coach on read-only pages.** Whether the AI partner appears on the shared
  requirements page.
- **Bringing work in and pushing it out.** How import and export should feel for
  each tool.
- **Existing products.** How a product with history in other tools is onboarded
  without re-entering everything.
- **Explicit practice checks.** Whether the AI partner should be steered toward
  named good-practice checks (one source, no method, no counterexample). This
  changes its answers and needs a decision.

---

## 12. Glossary

| Term | Meaning |
| --- | --- |
| **Adaptive intent** | Business intent that keeps its purpose while its understanding of the problem, the solution or the thesis is revised through decisions |
| **Workbench** | A person's or team's private space to prepare work and reconcile it against project and enterprise context |
| **Shared space** | Shared requirements and Decisions & Issues, where alignment is honed and decisions are made |
| **Publication** | The explicit, previewed, owner-confirmed release of work from a workbench to the shared space |
| **Preflight** | Pinning the exact version and its basis into a prepared packet before publication |
| **Context packet** | A purpose- and audience-bounded set of exact record versions; a derived view, never a source of authority |
| **Recipe** | The plan for assembling the next packet; the packet records what was actually assembled |
| **Requirement drawer** | A category where candidate and approved requirements live |
| **Contribution** | A domain's published observation, interpretation and limits, with exact sources |
| **Knowledge card** | A unit of knowledge produced in a workbench, with its dependencies |
| **Need context** | A situated claim about people, job, situation, triggers, pains, gains, boundaries and dependencies |
| **Decisions & Issues** | The shared board of issues, reviews and decisions |
| **Issue** | A challenge, conflict, gap, dependency or question raised against exact records |
| **Decision** | An authorized approve, reject or defer, with rationale, on an exact basis |
| **Readiness call** | A recorded decision on whether the project is ready to hand off, and on what basis |
| **Reach** | How far a domain meaning applies: project, domain, named domains, enterprise |
| **Domain knowledge** | A domain's versioned vocabulary, categories, relationships, standards and methods |
| **AI partner** | The model-assisted coach in a workbench; suggests, never decides or overwrites |
| **Controller** | The service that owns agent run state, limits and escalation (to build) |
| **Outbox** | Events written in the same transaction as the change they describe (to build) |
| **Stale** | A record, review or packet whose basis has a newer version |
