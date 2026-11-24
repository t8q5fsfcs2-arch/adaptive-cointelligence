# Adaptive Cointelligence developer manual

For product engineers, backend and full-stack developers, platform owners,
domain leads and service operators.

25 November 2026 · Builder review draft 1 · Based on the repository at the code in this
repository.

This manual explains how to build Adaptive Cointelligence into a dependable
system. It is a place where a cross-functional team builds a **complete,
handoff-ready solution** while its members work largely **asynchronously**,
each in their own workbench and on their own schedule. Underneath sits a
knowledge system that behaves less like a lake and more like a **brain**: it
remembers with meaning, attends to what the current task needs, learns from
what happens, coaches people at the moment of work, and turns proven practice
into shared standards.

The recommendation is to keep the current product as the human experience and
to harden the record, packet, learning, coaching and execution services
beneath it. Prove one complete loop (intent, domain work, publication,
decision, revised intent, handoff) with real people working apart, then add
domains, connectors and agents through the same contracts.

This is a reference design and builder manual. It separates what the code does
today from what is proposed. It does not claim a production installation, a
live model evaluation or enterprise integration.

## How to use this manual

Read sections 1 to 3 for the strategy: why asynchronous work, what a complete
solution is, and what the knowledge brain is for. Sections 4 to 7 define the
knowledge model and the three things the brain does (learn, coach,
standardize). Section 8 shows how human, unstructured work is distilled into
structured knowledge, and how that becomes a corpus and a property graph that
ladder up to enterprise questions. Sections 9 to 16 are the implementation
contracts. Sections 17 to 21 cover operations, proof, the build sequence and open
decisions. The appendices hold example
payloads, the command surface, a quickstart and code map, a glossary and the
evidence behind each claim.

Every section opens with a status line. Inside sections the same labels mark
individual claims.

| Label | Meaning |
| --- | --- |
| **Built** | Code in this repository implements it and tests cover it |
| **Partial** | A working slice exists; the production version needs more |
| **To build** | Recommended behaviour and acceptance condition; not implemented |
| **Owner decision** | An accountable product, domain or platform owner must choose |

All examples use the synthetic Riverbend Health clinic project that ships with
the demo. Every person, source and dialogue in it is invented.

## Contents

1. [Purpose and design strategy](#1-purpose-and-design-strategy)
2. [Working asynchronously](#2-working-asynchronously)
3. [The complete solution](#3-the-complete-solution)
4. [Knowledge objects and their state](#4-knowledge-objects-and-their-state)
5. [How the brain learns](#5-how-the-brain-learns)
6. [How the brain coaches](#6-how-the-brain-coaches)
7. [How the brain standardizes](#7-how-the-brain-standardizes)
8. [Distillation: from human work to structured, adaptive knowledge](#8-distillation-from-human-work-to-structured-adaptive-knowledge)
9. [Context packets and the execution basis](#9-context-packets-and-the-execution-basis)
10. [Assessment and honest uncertainty](#10-assessment-and-honest-uncertainty)
11. [Change propagation and selective reuse](#11-change-propagation-and-selective-reuse)
12. [Sources and connectors](#12-sources-and-connectors)
13. [Bounded AI skills and the agent layer](#13-bounded-ai-skills-and-the-agent-layer)
14. [Durable workflow, events and commands](#14-durable-workflow-events-and-commands)
15. [Identity, authority and governed release](#15-identity-authority-and-governed-release)
16. [Delivery and outcome feedback](#16-delivery-and-outcome-feedback)
17. [Operations, observability and model cost](#17-operations-observability-and-model-cost)
18. [Platform, migration and recovery](#18-platform-migration-and-recovery)
19. [Evaluation and the acceptance pack](#19-evaluation-and-the-acceptance-pack)
20. [Build sequence, owners and experience standards](#20-build-sequence-owners-and-experience-standards)
21. [Open decisions](#21-open-decisions)
- [Appendix A Example payloads](#appendix-a-example-payloads)
- [Appendix B Command surface](#appendix-b-command-surface)
- [Appendix C Quickstart and code map](#appendix-c-quickstart-and-code-map)
- [Appendix D Glossary](#appendix-d-glossary)
- [Appendix E Sources and evidence boundaries](#appendix-e-sources-and-evidence-boundaries)

---

## 1 Purpose and design strategy

*Status: strategy settled; foundation Built; learning and orchestration services To build.*

### What the product is for

Work passes from a sponsor to researchers, designers and delivery teams. At
each handoff the reasoning thins out. Decisions are made in meetings and not
captured. A finding that should have changed the brief arrives after the build
has started. The same word means different things to two teams. When a new
project starts, nobody can tell what an earlier one learned, under what
conditions, or whether it still holds. AI makes this worse when it is fed stale,
excessive or unauthorized context.

Adaptive Cointelligence keeps business intent, evidence, decisions and the
resulting solution connected while all of them change. A sponsor states intent.
Domain experts do their own professional work and publish what is
consequential. Their contributions can challenge, refine or confirm the intent.
Authorized people decide what changes. **The purpose endures, the plan adapts,
and the record of why it changed is never lost.**

### Three design commitments

**1. Asynchronous by default, synchronous by exception.** A team rarely sits
together. A sponsor frames intent on Monday; Research interviews patients on
Wednesday; Design iterates on Thursday night; the requirement owner decides on
Friday from her phone. The system must carry the context between people who are
not present at the same time, so that nobody has to reconstruct what happened
or wait for a meeting to continue. Meetings remain useful for hard
conversations. They are not required for the work to move.

**2. The product builds a complete solution, not only a context feed.** The
end point is a handoff a delivery team (or an operating owner, for a
non-software outcome) can trust: a validated problem, a validated solution,
ratified requirements with acceptance criteria, the rationale behind each, the
open issues and the exact versions they rest on. The product is where that
package is assembled, reconciled and decided. It is not a thin interface over a
knowledge store that other platforms consume.

**3. Knowledge is a brain, not a lake.** A lake stores everything and leaves
interpretation to whoever fishes in it. A brain does five more things, and the
architecture has to supply each one explicitly:

| A brain... | In this system | Mechanism |
| --- | --- | --- |
| **Remembers with meaning** | Typed, versioned records that keep who said what, on what evidence, under what conditions | Append-only store, exact references, building block types (section 4) |
| **Attends** | Selects what the current task, person and moment need, and nothing they may not see | Context packets, scopes, the working brief handover (section 9) |
| **Learns** | Revises its understanding when evidence, outcomes or decisions change, and keeps the history | Proposals, decisions, successor versions, lessons, adoption (section 5) |
| **Coaches** | Guides each person at the moment of work according to their domain's practice | AI partner grounded in domain knowledge, quiet suggestions, assessments (section 6) |
| **Standardizes** | Turns proven practice into shared standards and shared meaning, with explicit reach | Domain knowledge, meaning governance, assessment profiles (section 7) |
| **Forgets responsibly** | Supersedes and retires what no longer holds, without erasing why it once did | Supersession, retirement, retention policy (section 5) |

### Where the metaphor stops

The brain metaphor guides design; it does not license autonomy. In this system:

- **Learning is governed revision, not model training.** The system learns by
  creating reviewed successor versions of intent, requirements, lessons,
  standards and meanings. No user content trains model weights.
- **The brain does not decide.** It proposes, prepares and reminds. Authorized
  people decide anything consequential. Human approval is never inferred from a
  model response, a publication or silence.
- **Memory is selective by permission, not by salience alone.** What a person
  or model may see is decided by scope and release rules first. Relevance ranks
  only what is already permitted.
- **Similarity is not recall.** A matching term or a high retrieval score is a
  candidate connection, never evidence that two things mean the same.

### Logical services

Separate these responsibilities logically. They do not each need a separate
deployment, database or agent.

| Service | Responsibility | Trust boundary | Status |
| --- | --- | --- | --- |
| **Record store** | Durable records keyed by identity and revision; exact dependencies; packet manifests | Append-only; optimistic concurrency; scope checked on every read | Built (`core.Store`) |
| **Workbench services** | Private domain work: conversation, brief, building blocks, reports, prototypes | Domain scope; nothing crosses without publication | Built |
| **Publication service** | Preflight, preview and release of selected work to the shared space | Owner confirmation; exact basis; audience checked | Built (`domain.prepare`, `domain.publish`) |
| **Shared space services** | Issues, proposals, reviews, decisions, decision rights, readiness | Decisions only by authorized people on a fresh basis | Built |
| **Domain knowledge (memory of practice)** | Vocabulary, categories, standards, practices, meaning boundaries and reach | Edited by the team lead; wider reach needs approval | Built (`domain_knowledge.py`, D005, D009) |
| **Coaching services** | AI partner, intake coach, requirement assistant, integrity and design review | Advisory only; output saved as separate records | Partial |
| **Context resolver (attention)** | Select exact eligible versions for a named task and audience | Access and applicability checked before model use | Partial (`Store.packet`) |
| **Change and learning services** | Trace impact, mark stale work, route reconsideration, propose lessons | Proposals only; owners decide | Partial (`ImpactWorker`) |
| **Workflow controller** | Durable run state, events, bounded agent runs, retries, escalation | Code owns state and tool capability | To build |
| **Projections** | Graph, timelines, case board, evidence coverage, search | Derived; never rewrite their sources; rebuildable | Partial |

### Prove the value

Value is measured at three levels, reported separately:

1. **Context integrity.** Anyone authorized can reconstruct why a requirement
   exists, what evidence supported it, who decided and what it replaced.
2. **Decision intelligence.** Teams see what another domain's work assumes,
   enables or puts at risk before they commit.
3. **Delivery impact.** Earlier alignment produces fewer late surprises and
   less rework.

For the asynchronous strategy add three working measures: **time to continue**
(how long a person needs to pick up work someone else left), **waiting time**
(how long consequential items sit with a named person), and **reconstruction
effort** (how often someone has to ask a colleague what happened). Measure a
baseline with the team's current method before the pilot. More cards, more agent
runs and faster generation are activity, not value.

---

## 2 Working asynchronously

*Status: two spaces, publication boundary, waiting items and quiet signals Built;
event-driven notifications and time-bound escalation To build.*

### Two spaces and one boundary

Every rule in the system hangs off this picture.

```
        PRIVATE WORKBENCHES                              SHARED SPACE
  ┌──────────────────────────────┐                ┌──────────────────────────────┐
  │ Business Intent (sponsor)    │                │ Requirements                 │
  │ Research workbench           │  ─ publish ─▶  │ (read-only, evolving)        │
  │ Design workbench             │   explicit,    │                              │
  │ ...any configured domain     │   previewed    │ Decisions & Issues           │
  │                              │                │ (issues, reviews, decisions) │
  │ prepare work and reconcile   │  ◀─ context ─  │                              │
  │ it against project and       │   decisions,   │ hone alignment and decide    │
  │ enterprise context           │   new versions │                              │
  └──────────────────────────────┘                └──────────────────────────────┘
```

- **The workbench** is each person's or team's private place to prepare work
  and reconcile it against the project's and the enterprise's context. Its
  interface is a cockpit ([D010](decisions/D010-workbench-cockpit.md)): the
  conversation and the work stay dominant, with next moves, suggestions,
  reviews, the brief, building blocks and updates on a rail at hand.
- **The boundary** is publication: an explicit, previewed, owner-confirmed
  release of selected work. Nothing else crosses.
- **The shared space** is where alignment is honed and decisions are made. In
  the product it is called **Requirements** (what the project must achieve) and
  **Decisions & Issues** (what is being worked out).
- **The return path** carries decisions and new versions back into every
  workbench as updated context.

### Why asynchronous work needs this shape

Asynchronous collaboration fails in predictable ways: people work from stale
information, one person's absence blocks everyone, private thinking leaks or is
lost, changes arrive as interruptions, and nobody can tell what is waiting on
whom. The two-space model answers each one structurally.

| Failure in asynchronous work | Structural answer | Status |
| --- | --- | --- |
| Working from a stale version | Every write names the version it changes; stale writes fail. Briefs and reviews show a changed basis | Built |
| Someone's absence blocks the team | Domains work in parallel in private. Only a named decision waits on a named person | Built |
| A handoff loses its reasoning | Publication pins the exact basis into a packet; the receiving workbench opens with "What was handed over" | Built |
| Private thinking leaks | Workbench scope is private; release needs preflight, preview and confirmation | Built |
| Changes interrupt focus | Updates arrive on the rail and as quiet suggestions with replies; nothing pops up ([D011](decisions/D011-quiet-ai-suggestions.md)) | Built |
| Nobody knows what is waiting | Home leads with "Waiting on you"; each item opens the exact record. The activity timeline shows how long items have waited | Built |
| A decision is made in a meeting and lost | Decisions are records with basis, rationale and authority, not minutes | Built |
| A waiting item stalls for days | Named next responder, agreed response window and escalation path | To build |
| A change happens while someone is away | Event-driven notification to the owners of dependent work, batched as a digest | To build |

### Principles for asynchronous design

1. **Every handoff is self-contained.** A person picking up work must be able
   to continue from what the system shows, without asking the author. The
   packet, the handover block and the decision record carry the reasoning.
2. **State is visible without asking.** What is waiting on me, what changed
   since I was last here, and who holds each open item are always one glance
   away.
3. **Only decisions wait on people.** Investigation, drafting and preparation
   never block on another person's availability. A named decision may.
4. **Work in progress stays private until its owner chooses.** Asynchronous
   does not mean ambient. Nobody sees half-formed work by accident.
5. **Changes arrive as review signals, not rewrites.** When something upstream
   changes, dependent work is flagged for its owner. It is never silently
   rewritten.
6. **Decisions can be made asynchronously, on an exact basis.** A decision
   owner reviews the proposal, the reviews and the evidence when she can. The
   system checks that the basis has not changed since the reviews were given.
7. **Silence is never consent.** A missing response is a stalled item with an
   owner, not an approval.
8. **Interruptions are earned.** Only items that need a person's decision or
   response claim attention. Everything else waits quietly on the rail.

### Responsibilities at each moment

| Moment | Human responsibility | AI contribution | Application responsibility |
| --- | --- | --- | --- |
| Frame intent | Sponsor states value, affected people, scope, goals and measures | Intake coach challenges unclear language and suggests missing context, per question | Saves versions; keeps the sponsor's words separate from suggestions |
| Share intent | Sponsor chooses what to publish and when | Assessment exposes weak spots before sharing | Summary before sharing; exact preflight; creates requirement scaffold |
| Receive work | Domain practitioner reads what was handed over and sets a plan | AI partner explains what the intent assumes and where evidence is thin | Working brief opens with the handover; pins the intent version used |
| Investigate | Practitioner plans and performs the work, in any tool | AI partner coaches method, interpretation and alternatives | Private records with provenance; imports keep source identity |
| Publish outcomes | Practitioner releases selected findings and implications | AI helps state consequences, limits and what the next team needs | Exact publication, released sources, packet, contribution |
| Align | Any participant raises a challenge, gap, conflict, dependency or question | Suggests where a contribution may affect intent or another domain | Issue against exact records; tracks responses and stalls |
| Decide | Authorized owner approves, rejects or defers with rationale | Compares positions and options | Checks authority and fresh basis; commits successor versions |
| Hand off | Readiness owner makes the readiness call; receiver accepts | Prepares the developer brief draft | Records readiness basis; stages exact delivery payload |
| Learn | Owners review outcomes and lessons | Relates outcomes to expectations; proposes lessons | Versions the lesson; routes adoption; keeps reach explicit |

### The work products people use

- **Business Intent:** the opportunity, value, affected people, boundaries,
  goals and success measures. Versioned. The sponsor's words stay hers.
- **Working brief:** a domain's private, editable plan. It opens with what was
  handed over: the question for the team, the intent version, the requirements
  with their evidence coverage, what other teams shared and where evidence is
  thin.
- **Building blocks:** typed units of knowledge produced in a workbench
  (section 4). Not a compulsory form; a way to keep knowledge findable.
- **Outcomes report:** selected results, evidence, limits and implications,
  released for others.
- **Requirements:** the shared view of what the project must achieve, why, and
  how sure we are. Read-only; changed only by decisions.
- **Decisions & Issues:** the shared space for consequential questions, gaps,
  conflicts and proposed changes.
- **Developer brief and delivery staging:** the handoff package and the exact
  payload for the work tracker.

### Illustrative clinic sequence, worked asynchronously

Monday: Dana (sponsor) frames the problem: missed appointments run at 18% and
she wants an AI reminder assistant to cut them to 10%. She shares intent
version 1. The system creates the requirement scaffold.

Tuesday to Thursday, in parallel: Jordan (Research) opens his workbench, reads
what was handed over and interviews patients and front-desk staff. Mei (Design)
starts concepts from the same intent version. Neither waits for the other.

Thursday: Jordan publishes a finding: most people who miss already knew in
advance; rescheduling needs a phone call during office hours. He proposes a
change to the problem statement.

Friday: Dana sees the proposal in "Waiting on you", reads the finding and its
limits on her phone, and adopts the revision. Intent becomes version 2; version
1 is kept. Mei's workbench now shows that its basis changed, with the
difference, as a quiet signal. She revises her concept to include a staff
handoff for visit types that need one and raises a dependency for Research.

The following week: Jordan answers the dependency. Sofia (requirement owner)
proposes requirement version 2; Research and Design review it when they can;
Sofia approves. The readiness call records that Design's evaluation is still
small and that the project proceeds to a bounded pilot under that condition.

At no point did the work require a meeting, and at every point a new
participant could have reconstructed why.

---

## 3 The complete solution

*Status: requirement areas, evidence coverage, readiness call, developer brief and
delivery staging Built; real work-tracker writes and outcome return To build.*

### What "complete" means

A complete solution is a handoff package that a receiving team can act on
without reconstructing the reasoning. It contains:

| Part | What it carries | Where it comes from | Status |
| --- | --- | --- | --- |
| **Validated problem** | The problem as revised by evidence, the people and situations affected, what is known and unknown | Intent versions, research contributions, need contexts | Built |
| **Validated solution** | The chosen concept, its evaluation, design decisions and their alternatives | Design contributions, prototype workflow, evaluation results | Built |
| **Ratified requirements** | Each requirement's current version, acceptance criteria, rationale and owner | Requirements, proposals, decisions | Built |
| **Confidence picture** | For each requirement: confidence rating, evidence coverage, contributions from ([D012](decisions/D012-confidence-signals.md)) | Assessments, evidence calculation | Built |
| **Open issues and limits** | What is unresolved, what was deferred and to whom, what conditions apply | Decisions & Issues, deferrals, readiness conditions | Built |
| **Readiness call** | Who decided the project is ready, for what use, with what conditions ([D008](decisions/D008-readiness-decision-record.md)) | Readiness record | Built |
| **Exact basis** | The versions every part rests on, so later changes can be traced | Packets, dependencies | Built |
| **Delivery payload** | Work items with criteria and references, staged for the receiving tool | Developer brief, delivery staging | Partial (export only) |

### Convergence

The project converges as requirement areas fill with evidence. The case board on
Home ([D007](decisions/D007-c2-tracker-design-system.md)) shows mission, win
conditions, case strength by area, and the problem and solution sides. An area
is only as strong as its weakest part: an area reads High only when every
included requirement is High. The readiness call turns that picture into an
accountable decision.

### Several valid paths to a complete solution

The system does not impose one sequence.

- **Full validation.** Intent, then problem validation, then solution
  validation, then handoff. Highest confidence, longest path.
- **Early prototype.** A team prototypes straight after Business Intent. That
  is allowed. Requirements show no contributions and Low coverage, so the
  confidence picture is honest. The readiness call records the choice and its
  conditions.
- **Brownfield change.** A small change to an existing product may need little
  new research. Known needs can flow straight into requirements and the
  handoff, with their basis recorded.
- **Non-software outcome.** The end point is a process change or a decision not
  to build. The same package goes to an operating owner instead of a delivery
  team.

### Completeness is not certainty

A complete solution can carry Low confidence in places, as long as that is
visible, owned and accepted in the readiness call. A solution can also be
abandoned or narrowed when evidence shows the original thesis was wrong. The
system must treat "we learned not to build this" as a successful outcome of the
process, not a failure to reach the end.

---

## 4 Knowledge objects and their state

*Status: records, building blocks, families and separate state dimensions Built;
enterprise knowledge envelope To build.*

### Give each object one job

| Object | Job | Record kinds (examples) | Scope |
| --- | --- | --- | --- |
| **Source** | Material that was observed or received, with identity and version | `domain-source`, released `source` | domain, then project when released |
| **Building block** | One bounded unit of authored understanding (observation, finding, lesson...) | `domain-implication` with a typed card body; released `knowledge-card` | domain, then project |
| **Need context** | A situated claim about people, job, situation, triggers, pains, gains, boundaries, dependencies | `need-context` | domain |
| **Intent** | What the organization is trying to achieve and why | `intake-case`, `intake-draft`, `intent`, `intent-refinement` | private, then project |
| **Goal and measure** | Outcomes and how they will be measured | `goal`, `success-measure` | project |
| **Requirement** | What the solution must do, in a drawer (area) | `requirement-drawer`, `requirement` | project |
| **Contribution** | A domain's deliberately published position | `domain-handoff`, `domain-publication`, `contribution` | project |
| **Issue** | A challenge, conflict, gap, dependency or question against exact records | `bridge-issue`, `bridge-issue-event` | project |
| **Proposal, review, decision** | A proposed change, its reviews and the authorized act | `decision-case`, `human-review`, `decision` | project |
| **Readiness decision** | Whether the project may proceed, for what use | `readiness-decision` | project |
| **Packet** | The exact basis assembled for a purpose and audience | packet manifests | follows audience |
| **Domain knowledge** | A domain's vocabulary, categories, relationships, standards, practices | `domain-knowledge` | domain |
| **Meaning governance** | Proposals and concepts that widen a meaning's reach | `meaning-proposal`, `enterprise-proposal`, `enterprise-concept`, `enterprise-adoption` | project, enterprise store |
| **Assessment** | A recorded judgment for a named use | `requirement-assessment` | project |
| **Execution receipt** | What a model run did, on what basis | `agent-execution`, `agent-quality-evaluation` | the scope of the work |
| **Preference** | A person's private settings for quiet suggestions | `suggestion-preferences` | domain |

A building block is the unit of knowledge. A card is how the interface shows it.
The same block can appear as a card, in a report, in an evidence view and in a
handoff, and can be included in many packets. One packet usually includes many
blocks.

### Families and types

Building blocks are organised in four families
([D013](decisions/D013-knowledge-block-families.md)):

| Family | Types | What the family does not establish |
| --- | --- | --- |
| **Evidence** | Observation, finding, user situation, user flow, evaluation result | A label does not prove representativeness, accuracy or validation |
| **Direction** | Implication, user story, design decision, performance goal, lesson | A recommendation or local choice is not a ratified project obligation |
| **Open** | Hypothesis, challenge, dependency, open question | An open item may stay unresolved; it is not defective data |
| **Outputs** | Artifact, working note | An artifact's existence does not show it works or meets a requirement |

Each team's types lead in its workbench; the others stay available under "More
types". Every type carries a "Where this applies" footer: people or role,
situation, time or period, and how sure. Observation and finding are separate
types on purpose: a future project must be able to tell what was seen from what
was concluded.

### The knowledge envelope

*Today (Built):* every record has a stable ID, an immutable revision, a kind and
a scope fixed at creation, a body, and recorded dependencies on exact
revisions. Building blocks add type, title, statement, type-specific fields,
source links and typed links (supports, challenges, refines, depends on,
constrains, measures, decision needed).

*Target (To build):* every enterprise knowledge unit should also carry:

- a namespaced identity (tenant, project, domain) and a type-schema version;
- owner and author, separately from who last edited;
- **origin of the wording**: person, model suggestion, source extraction or
  external system, with acceptance recorded as a separate receipt;
- created time, effective time and recorded time;
- privacy and permitted audience;
- source references with exact spans or retained artifacts;
- applicability: people, job, situation, environment, system version and period;
- review state and reach.

Fields that do not apply are marked "not applicable"; missing fields stay
unknown. A saved model answer is provenance for an interpretation, never
independent evidence about the world.

### Keep state dimensions separate

| Dimension | Question it answers | Where it lives |
| --- | --- | --- |
| Completeness | Are the material parts specified? | Intake answers, drawer coverage |
| Evidence coverage | How much shared work references it, on the current version? (Coverage, not quality) | Counted ([D004](decisions/D004-requirement-evidence-level.md)) |
| Confidence rating | How sure is the owner, for a named use, and why? | Recorded assessment |
| Contributions from | Which teams have published on the current version? (Publication is not validation) | Calculated from contributions |
| Review and publication state | Draft, prepared, published? | Domain and publication records |
| Governing authority | Who may commit the organization to it? | Decisions, decision rights |
| Currency | Is its basis still current? | Stale checks, `changed_refs` |
| Applicability | Where, when and for whom does it hold? | Block footer, need context |
| Reach | How far does a meaning apply? | Domain knowledge, meaning governance |

Never merge two of these into one status. A well-written hypothesis can be
complete and low-confidence. A ratified requirement can be weakly evidenced.
Filling a form, publishing a report or counting teams never raises confidence
automatically.

### Minimum logical data model

| Record family | Minimum durable relationship |
| --- | --- |
| Source and span | Native identity and revision, permitted original or excerpt, locator |
| Knowledge revision | Typed payload, author, origin of wording, source basis, applicability, predecessor |
| Relationship | Typed link between exact revisions, with rationale, review state and reach |
| Assessment | Frozen conditions, evidence, standard and version, judgments, limits, intended use |
| Packet and recipe | Issued exact manifest, audience, purpose, and the plan that produced it |
| Publication | Selected released work, audience, basis and release receipt |
| Proposal and decision | Exact change, authority, disposition, rationale, affected versions |
| Execution and outcome | Attempt, payload, receipt, observed result and learning link |

Implement stable identities and immutable revisions under a tenant boundary, with
a uniqueness constraint on identity plus revision. Store relationships against
exact revisions, never an unqualified latest. Keep graph, search and vector
views rebuildable from the authoritative records. Apply governed retention and
deletion: append-only history does not override a required disposal.

---

## 5 How the brain learns

*Status: within-project learning (intent adaptation, requirement revision) Built;
lesson type, enterprise concepts and adoption Built; learning service and outcome
return To build.*

A lake grows by accumulation. A brain improves by revising what it believes when
something happens, and by keeping track of why. Learning in this system is
always a reviewed change of a versioned record. It happens at three timescales.

### Three learning loops

| Loop | Timescale | What changes | Example (clinic) | Status |
| --- | --- | --- | --- | --- |
| **Within a project** | Days to weeks | Intent, requirements, the working brief, the plan | Research's finding moves intent from "remind people" to "make rescheduling easy"; intent v2 | Built |
| **Across projects** | Months | Lessons, reusable findings, adopted meanings | A later project asks which lessons about rescheduling apply to its own patients | Partial |
| **In practice** | Quarters | Domain standards, methods, assessment profiles, block types | Research adds a practice: "separate what people knew in advance from what they forgot" | Partial |

### How a project learns (Built)

1. A domain publishes a contribution that bears on intent or a requirement.
2. Anyone raises an issue or proposes a change against the exact version.
3. The owner reviews the proposal, its evidence and the reviews, and decides.
4. The decision creates successor versions and records what they replaced.
5. Every workbench that used the old version sees that its basis changed.
6. Accepted intent changes update the places that mirror intent
   ([D006](decisions/D006-accepted-intent-changes-update-mirrors.md)).

Commands: `intent-refine`, `intent-adopt`, `intent-dispose`, `proposal`,
`review`, `decision`. Records: `intent-refinement`, `intent` successor,
`decision-case`, `human-review`, `decision`, `requirement` successor.

### How the enterprise learns (Partial)

Learning across projects moves along a deliberate ladder. Each step needs
evidence and review; nothing is promoted automatically.

```
observation ─▶ finding ─▶ lesson ─▶ candidate standard ─▶ domain standard
   (seen)     (concluded)  (scoped,    (proposed by a      (approved by the
                            reusable)   practitioner)        domain lead)
```

- **Observation and finding** are separate building block types. A finding
  records its interpretation, the conditions it depends on, alternatives and
  limits.
- **A lesson** is a block type with population, conditions where it held,
  counterexamples, how another project could use it, and where it should not be
  applied. Built as a type; the review path for wider use is To build.
- **A candidate standard** is proposed into domain knowledge as a standard or
  practice. The team lead edits domain knowledge
  ([D005](decisions/D005-knowledge-edited-by-team-lead.md)). The proposal and
  review path from a lesson is To build.
- **Shared meaning** widens through meaning governance
  ([D009](decisions/D009-meaning-governance.md)): mapping between two teams
  needs both leads; enterprise reach needs a lead and a steward as two different
  people. A team adopts a pinned version of an enterprise concept.

### Rules for learning

- **Repetition is a signal, not proof.** Ten documents repeating one unsupported
  claim are one origin. Count evidence lineages, not mentions.
- **Keep counterexamples.** A lesson without its exceptions will be applied
  where it fails. Record where a rule stopped working.
- **Transfer is judged, not assumed.** A lesson from one clinic becomes a
  hypothesis for another until the receiving owner adopts, adapts, declines or
  defers it.
- **Private work never teaches the enterprise.** Only published, reviewed
  knowledge can be promoted. Retrieval, embedding or frequent use does not move
  anything to a wider scope.
- **Outcomes can overturn learning.** An observed result that contradicts a
  lesson opens a review of the lesson. It does not silently edit it.
- **Models do not learn from users.** No content is used to train model weights.
  Learning lives in records.

### Learning from outcomes (To build)

The loop closes when delivered work produces an observed outcome:

1. A read-only adapter brings back an outcome: what happened, measured how,
   over what period, for which population.
2. The learning service links it to the intent, requirement and decision it
   tested.
3. It compares the outcome with the success measures set in Business Intent.
4. It proposes: confirm the lesson, narrow it, reopen the requirement, or
   reopen the intent.
5. The owner decides. A "done" status in a work tracker is evidence of a
   workflow state, not of adoption or benefit.

### Forgetting responsibly

A brain that never forgets becomes noise. This one forgets by **supersession
and retirement**, never by deletion of history:

- A successor version supersedes its predecessor; the predecessor stays
  interpretable for decisions that used it.
- A lesson or standard can be retired with a reason and a date; packets that
  used it keep their exact references.
- Old knowledge loses priority in retrieval only after authority and
  applicability checks, using effective dates first. An old policy can still
  govern; a new opinion can still be provisional.
- Retention and deletion rules are honoured even when they make an old packet
  unresolvable. The system then reports the unavailable basis instead of
  reconstructing it.

---

## 6 How the brain coaches

*Status: intake coach, domain AI partner, requirement assistant, integrity review,
design visual review, quiet suggestions Built (live model required);
practice checks and coaching from lessons To build or Owner decision.*

Coaching is how domain knowledge reaches people at the moment they work. The
goal is better professional work, faster, with the expert still in control.

### Where coaching happens

| Coach | Where | What it draws on | Output | Status |
| --- | --- | --- | --- | --- |
| **Intake coach** | Business Intent, per question | Question-specific expertise (`config/field_guidance.json`), intake profile, seven skills | Challenges, missing context, suggested wording, per question | Built |
| **Business Intent assessment** | Before sharing intent | Evidence reasoning framework (`config/evidence_reasoning.v1.json`) | Saved assessment with confidence and weak spots | Built |
| **Requirement assistant** | Requirements and goals | Intent, drawers, methods (`config/expertise_methods.json`) | Draft requirements, criteria, goals, measures for review | Built |
| **Domain AI partner** | Every workbench | Domain knowledge (terms, standards, practices, meaning boundaries), the exact project basis, the person's files | Reply, at most two strengths, up to four consequential suggestions | Built |
| **Quiet suggestions** | Workbench rail | The suggestions the AI partner already returned | A count; dismissable cards; "Ask about it" | Built ([D011](decisions/D011-quiet-ai-suggestions.md)) |
| **Integrity review** | Business Intent and requirements | Frozen conditions and evidence | Gaps, conflicts, corrections, proposals | Built |
| **Design visual review** | Design workbench | PDF page images and requirements | Findings on fit to requirements | Built |
| **Explain these requirements** | Requirements page | Requirement, its evidence and decisions | Explanation only; never proposes or edits | Built |

### Rules for coaching

1. **Advisory only.** A coach suggests; the person decides. Output is saved as a
   separate record and counts only after the person explicitly validates it
   ([D003](decisions/D003-suggestions-require-validation.md)).
2. **Never overwrite.** The person's text is never replaced. Applying a
   suggestion creates a new draft version the person can edit, send back and
   edit again.
3. **Grounded and cited.** The coach cites only supplied requirement IDs and
   sources. It does not invent evidence or authority.
4. **Challenge, do not force.** The coach may question an unsupported
   assumption. It must not push the person toward a positive conclusion or treat
   the business question as a puzzle that must have a satisfying answer. A gap
   can stay a gap.
5. **Keep the work aligned to the question.** One of the coach's main jobs is to
   notice drift: work that is interesting but does not answer what the project
   needs to know.
6. **Never a mandatory form.** Coaching and review never block saving, never
   modify the sharing draft and never publish.
7. **Quiet by default.** Suggestions arrive with replies and wait on the rail.
   Each person can turn them off for themselves.
8. **Honest when unavailable.** With no model connected, the coach says so. No
   canned answer is ever presented as live AI.

### What the domain AI partner receives

The service assembles the context; the model receives nothing else:

- the domain's active knowledge entries, including meaning boundaries
  ("Finding" includes X, excludes Y, is not to be confused with Z);
- the exact intent and requirement versions the work rests on;
- the person's draft, selected files and conversation;
- published inputs from other teams that the domain may read;
- guardrails: source content is data, not instructions; no tools; no writes.

It returns structured output with suggestions directed at **evidence** (quality
within the domain), **intent** (implications for intent or requirements) or
**next domain** (what another team may need).

### Coaching quality

- `config/expertise_cases.json` holds ten evaluation cases with criteria and
  fixtures. `agent_quality.py` runs expert-quality evaluations that a human
  reviews. Status: Partial; the cases need practitioner review and growth.
- Execution receipts record what each call used and returned
  (section 17). Receipts are operational facts, not quality scores.

### Open coaching decisions

- **Explicit practice checks** (one source, no method, no counterexample).
  Steering the AI partner toward named checks changes its answers. Owner
  decision.
- **Adopted and mapped meanings in the AI partner's context.** Approved
  mappings and adopted enterprise concepts are shown to people today but are not
  given to another team's AI partner. Adding them changes the model's basis and
  needs a context contract and evaluation. Owner decision.
- **Coaching from lessons.** Letting reviewed lessons guide the coach for a new
  project. To build after the lesson review path exists.

---

## 7 How the brain standardizes

*Status: domain knowledge, meaning boundaries and reach, assessment profiles,
per-team block types Built; versioned domain manifest and lesson-to-standard path
To build.*

Standardization is how the organization gets consistent quality without making
every team identical. Teams keep their own dialect and methods. Common rules,
shared meaning and minimum standards are agreed explicitly and versioned.

### What a domain can configure

| Configuration | Where | Who changes it | Status |
| --- | --- | --- | --- |
| Domain profile (label, deliverable types, block types) | `config/domains.json`, domain records | Administrator, domain lead | Built |
| Domain knowledge: terms, categories, relationships, standards, practices | `domain_knowledge.py` (`KINDS`) | Team lead ([D005](decisions/D005-knowledge-edited-by-team-lead.md)) | Built |
| Meaning boundaries: includes, excludes, not confused with | Domain knowledge entries | Team lead | Built ([D009](decisions/D009-meaning-governance.md)) |
| Reach: project, domain, named domains, enterprise | Domain knowledge, meaning proposals | Lead up to domain; wider by approval | Built |
| Requirement areas (drawers) | `config/intake_profile.json` | Product owner | Built |
| Assessment profiles: investigation, prototype, implementation | `config/requirement_assessment_profiles.v1.json` | Standards owner | Built |
| Evidence reasoning framework | `config/evidence_reasoning.v1.json` | Standards owner | Built |
| Decision rights | `decision_rights.py` | Project administrator | Built |
| Tool connections per user | `tool_imports.py` | The user | Built |

### Invariants no domain can turn off

Local configuration may specialize terms, methods, block fields, tools and
required evidence. It must never disable:

- permission checks and scope boundaries;
- exact provenance and version pinning;
- the separation of evidence and interpretation;
- preservation of uncertainty and counterevidence;
- explicit human authority for consequential commitments;
- idempotent external writes;
- visible failure and cost handling.

These are enforced in services, not prompts. A domain's prompt text or
configuration cannot weaken them.

### From practice to standard

```
practice used ─▶ lesson recorded ─▶ standard proposed ─▶ lead approves
      ▲                                                       │
      │                                                       ▼
 outcomes may revise ◀── new work coached by it ◀── standard versioned
```

1. A practitioner records a lesson with its conditions and counterexamples.
2. Someone proposes it as a standard or practice in domain knowledge.
3. The team lead reviews and approves, with a reason and an effective date.
4. The new version becomes active guidance for the AI partner in that domain.
5. New work is coached by it; outcomes can show where it fails.
6. A failing standard is revised or retired through the same path.

Steps 1, 3, 4 and 6 work today through domain knowledge editing. The linked
proposal from a lesson (step 2) and the outcome review (step 5) are To build.

### Shared meaning across domains

The same word can carry different meanings legitimately. "Appointment" is a
booked slot to Operations and a clinical encounter to Research. The system keeps
both and makes the difference visible:

- **Map** two teams' terms when both leads agree (types: same as, broader,
  narrower, related, distinct from).
- **Share** a term to named domains or the enterprise through a proposal.
- **Adopt** an enterprise concept at a pinned version into a project. A later
  enterprise revision is a review opportunity for the project, never an automatic
  rewrite.
- **Semantic services** may facilitate sessions and draft proposals. They never
  decide.

### Versioned domain manifest (To build)

Bind each model run and each assessment to an immutable domain-manifest version:
domain ID, schema version, vocabulary version, block type schemas, assessment
profile references, method references, source-authority rules, freshness
triggers, retrieval policy, decision-right references, tool allowlist,
publication destinations and evaluation pack. Record owner, effective date,
rationale and predecessor. Validate schema, policy checks and a small regression
pack before activating a new manifest. A cosmetic label change should not
invalidate unrelated reasoning; a changed method or meaning should open review.


---

## 8 Distillation: from human work to structured, adaptive knowledge

*Status: building block types and families, requirement areas and subcategories,
need contexts, typed block links and exact dependencies Built; the context-area
taxonomy linking blocks to requirement subcategories, a typed relationships
table, the corpus and the property graph To build; the taxonomy's content Owner
decision with practitioners.*

This is the process at the heart of the product: turning human, unstructured
work (interviews, transcripts, files, whiteboards, conversations) into
organized, distilled, adaptive structured knowledge that stays traceable to the
people and evidence it came from. Sections 4 to 7 describe the pieces. This
section shows how they fit into one taxonomy and one pipeline, and how the
result climbs from a single workbench to enterprise questions.

### The distillation pipeline

Each step adds structure and keeps a link to the step before. A person
validates every promotion; nothing climbs automatically.

| Step | What it is | What the step adds | Where it lives | Status |
| --- | --- | --- | --- | --- |
| 1 Raw material | Uploaded files, transcripts, tool imports, conversation | Source identity, version, hash | Private `source`, `domain-chat-turn`, `user_uploads` | Built |
| 2 Candidate | A passage selected, or a block suggested by the AI partner | Locator; origin of wording (person or model) | Chat selection, suggestion | Built |
| 3 Building block | A typed unit: observation, finding, user flow, gap... | Type, family, fields, "Where this applies", typed links, source spans | Private building block records | Built |
| 4 Contribution | Selected blocks and interpretation released by their owner | Audience, exact basis, limits, implications | `contribution`, released `knowledge-card`, packet | Built |
| 5 Reconciled | Compared with intent and other teams' work | Supports, challenges, conflicts, gaps as issues | Decisions & Issues | Built |
| 6 Ratified | A requirement, intent or decision changed by an authorized person | Authority, rationale, successor version | `requirement`, `intent`, `decision` | Built |
| 7 Lesson | Scoped learning for another project | Population, conditions, counterexamples, reuse limits | `lesson` block | Partial |
| 8 Standard or shared concept | A practice or meaning the domain or enterprise adopts | Reach, owner, effective date, version | Domain knowledge, enterprise concepts | Partial |

The lineage runs both ways. Any ratified requirement can be traced down to the
observations beneath it; any observation can be traced up to the decisions it
influenced.

### One taxonomy, three expressions

The common meaningful areas of context (user groups, user flows, unmet needs,
ownership, measures, gaps and so on) should be **one taxonomy** that appears in
three places:

| Expression | Question it answers | Example for "User groups and jobs" |
| --- | --- | --- |
| **Requirement subcategory** | What must be true? | "Patients who cannot reschedule by phone have a self-service route" |
| **Building block types** | What do we know, and how sure? | User situation blocks, observations and findings about who misses and why |
| **Packet section** | What moves to the next person or task? | The "people and jobs" part of a design review packet, with its blocks and gaps |

Because the three share the taxonomy, a block knows which requirements it can
inform, a requirement knows which kinds of evidence would strengthen it, and a
packet is organized in the same areas the receiver already thinks in.

**Keep the identities separate.** The taxonomy is shared; the objects are not
merged. A building block is the unit of knowledge. A packet is a task-specific
selection of many units, organized by area. One block can serve many areas and
many packets: the finding "people who miss usually knew in advance" informs both
"Unmet needs" and "Continuity across steps". Merging block and packet would
duplicate evidence, hide shared dependencies and break selective updates
(section 11 explains why that matters).

### Starting taxonomy: today's areas mapped to block types

The requirement areas and subcategories already exist in
`config/intake_profile.json`. The proposed mapping to block types and need
context fields is a starting point for practitioner review.

| Area | Subcategories (Built) | Building blocks that supply it (proposed) |
| --- | --- | --- |
| Customer and user needs | User groups and jobs; unmet needs and required support; need priority and value | User situation, observation, finding, need context (people, job, situation, pains, gains) |
| Experience and usability | Accessibility; ease of use and learnability; error prevention and recovery; content and interaction clarity; continuity across steps and handoffs | User flow, evaluation result, design decision, artifact, challenge |
| Operations and support | Ownership and escalation; capacity and service levels; support and operational recovery | Dependency, observation, finding, open question |
| Policy, access and boundaries | Applicable obligations; access and data boundaries; decision authority and auditability | Challenge, dependency, need context (boundaries) |
| Outcomes and measurement | Outcome and KPI definition; measurement and learning plan | Performance goal, evaluation result, lesson |
| Technology and integration | System behavior and interfaces; reliability and performance; data integrity and integration | Dependency, artifact, user story, hypothesis |

"Gaps" are not a separate area: every area can hold open blocks (hypothesis,
challenge, dependency, open question). A gap is an area whose requirements have
open blocks and thin evidence, which is exactly what the confidence signals and
the case board show.

### Building blocks as dependent data types

To make blocks behave like data types rather than notes, each type declares a
contract. Today each type has fields, a hint and a family. Add (To build):

| Contract element | Purpose | Example (finding) |
| --- | --- | --- |
| Context areas | Which subcategories it can inform | Unmet needs; continuity across steps |
| Required fields | What a complete block holds | Interpretation, conditions, alternatives, limits |
| Applies to | Where it holds | Adult patients; clinic scheduling; 2026 |
| Allowed relations | Which types it may link to, and how | Supported by observation; challenges hypothesis; informs requirement |
| Evidence contribution | What it can count toward | Evidence coverage of the requirements it informs, once published and validated |
| Promotion path | What it can become | Lesson, then candidate standard |

Typed links already exist on blocks: applies to, supported by, supports,
challenges, refines, depends on, constrains, informs, measures. The contract
says which of these are valid between which types, so the structure is checked by
code, not left to convention.

### Components, recipes and the feeds rule (Built)

[D014](decisions/D014-chained-packets-and-dependency-difference.md) makes the type
contract concrete. Under every block type sits a **fixed set of components**:
Actor, Situation, Claim, Basis, Strength, Time, Rationale, Alternatives, Criterion,
Measure, Owner, Status. Teams vary block types and vocabulary, never components.

- **A block type is a recipe:** required components, optional components and a
  family. A finding needs Actor, Situation, Claim, Basis, Strength and Time.
- **A requirement category declares what it needs:** components, accepted relations
  and accepted families. User groups and needs needs Actor, Situation, Claim and
  Strength, through *supported by*, from the Evidence family.
- **The feeds rule:** a block is eligible to count toward a category when it carries
  the components, relation and family the category accepts. Eligible is not counted;
  a person validates.
- **Coaching follows from the gap.** A finding without an Actor is told what to add
  and which category it would then count toward.

Actor and Situation carry scope, so they decide whether two groups mean the same
thing (section 9). The full tables are in D014.

*Built:* `config/knowledge_components.json` holds the components, recipes and
category needs; `knowledge_components.py` derives a block's components from its
fields (`components_of`), reports recipe gaps, and computes `eligibility` with a
coaching sentence. The block editor shows it under "How this block counts".

**A claim needs a basis that fits its reach.** One observation ("the office answers
nine to five") supports a hypothesis ("these hours may make rescheduling hard for
shift workers") and an open question ("who is affected, how often?"), not a
prevalence finding. "Most who missed knew in advance" stands only with evidence for
both prevalence and scope.

### Mold and move

A unit of knowledge must be able to **mold** to its receiver and **move**
between people, teams and projects without losing its identity.

- **Mold.** The same block is explained differently to a sponsor and to a
  designer, filtered by applicability, and refined through successor versions.
  The facts, rights and versions stay the same; only emphasis changes.
- **Move.** Every move is a recorded edge:

| Move | Mechanism | Edge recorded | Status |
| --- | --- | --- | --- |
| Private to shared | Publication | `RELEASED_AS` from the private version to the published one | Built |
| Into a task | Packet assembly | `CONTAINS` with purpose and audience | Built |
| Across domains | Meaning mapping | `MAPS_TO` with relation type | Built |
| Across projects | Lesson reuse and adoption | `ADOPTED_FROM` with the receiver's decision | Partial |
| Up to the enterprise | Promotion by lead and steward | `PROMOTED_TO` with reach | Partial |

### A traceable unit of knowledge

When the contract is complete, every unit carries: identity and revision; author
and origin of wording; source spans; context areas; where it applies; typed
links; the separate state signals (evidence, confidence, publication, authority,
currency); and reach. That is what makes it reusable best practice within any
vertical: a vertical is a domain configuration (its block types, fields,
vocabulary, standards and coaching) on the same chassis, not a fork of the code.

### Corpus and property graph

Two derived layers make the distilled knowledge searchable and traversable. Both
are built from the SQLite records and rebuildable from them; neither is a source
of truth.

- **Corpus:** meaningful text fields split into passages for retrieval. Each
  passage carries its record ID, revision, field, kind, block type, context area,
  scope and state.
- **Property graph:** a node for every record revision; a typed edge for every
  exact reference; the state signals as properties.

A search hit in the corpus leads into the graph; the graph leads back to the
exact record.

**What is saved today.** Each project database holds `records` (kind, scope,
JSON body), `dependencies` (untyped "depends on" between exact revisions),
`packets` and `user_uploads`. The enterprise store holds the same three record
tables. Separate stores hold the project catalog, file preferences and private AI
partner threads. The demo project has 224 record revisions across 47 kinds, 995
dependency rows and 16 packets. The typed meaning ("challenges", "produced",
"supersedes") sits inside the JSON bodies, in about 40 different reference
fields. A property graph needs those extracted as typed edges.

**Four tiers.**

*Tier 1: corpus and graph (shared, governed knowledge, project scope).*

| Record kinds | Text for the corpus | Typed edges for the graph |
| --- | --- | --- |
| `intent`, `intent-refinement`, `intent-decision` | Brief answers, proposed and published values, rationale | `SUPERSEDES`, `HAS_GOAL`, `INFORMED_BY` (`finding_basis`), `PROPOSES_CHANGE_TO`, `RESULTED_IN` |
| `goal`, `success-measure` | Rationale, beneficiary, definition, population, guardrail | `MEASURED_BY`, `DERIVED_FROM` (`source_case`), `SUPERSEDES` |
| `requirement`, `requirement-drawer` | Text, acceptance criteria, conditions, rationale; area questions and criteria | `IN_AREA`, `SERVES_GOAL`, `MEASURED_BY`, `SUPERSEDES` |
| `contribution`, `domain-publication`, released `knowledge-card` | Observation, interpretation, limitation, implications, downstream needs, open questions | `ADDRESSES` (`requirement_refs`), `CITES` (`source_refs`), `BUILDS_ON` (`input_refs`), typed `links[]` with rationale |
| Released `source` | Source text, split by passage with locator | `VERSION_OF`; the hash is a property, never text |
| `bridge-issue`, `bridge-issue-event` | Question, consequence, next question, notes | `TARGETS`, `CONCERNS`, `BASED_ON`, `ON_ISSUE` |
| `decision-case`, `human-review`, `decision`, `readiness-decision` | Proposal text, criteria, conditions, rationale | `DECIDES`, `REVIEWED_BY`, `PRODUCED` (`result_requirement`), `BASED_ON` |
| `domain-knowledge`, `meaning-proposal`, enterprise concepts | Definitions, includes, excludes, not confused with | Term nodes; `MAPS_TO` (same as, broader, narrower, related, distinct from), `SHARED_TO`, `ADOPTS` |
| `project-design-brief`, `project-developer-brief`, `policy`, `project-context` | Brief sections, constraints, assumptions | `BASED_ON`, `ADDRESSES`, `SUPERSEDES` |

*Tier 2: graph only (structure and provenance; the text duplicates or adds
nothing).*

| Source | Why graph only | Edges |
| --- | --- | --- |
| `dependencies` table | Already edges | `DEPENDS_ON` between exact revisions |
| `packets`, `packet-release` | A packet is a selection, not new text | `CONTAINS` (with audience), `RELEASED_AS` |
| `intake-case`, `sponsor-preflight` | Snapshots of goals and drafts; indexing them would count text twice | `SNAPSHOT_OF`, `PREPARED` |
| `agent-execution` | Provenance; its context repeats other records and may hold private text | `USED_BASIS`; model, mode and usage as properties |
| `goal-proposal`, `success-measure-proposal`, `value-acceptance`, `design-brief-change` | The accepted text lives on the target record | `PROPOSES`, `ACCEPTS` |
| `delivery-draft`, `demo-delivery-preview` | Staging; the text belongs to the requirement | `STAGES` |
| `user_uploads` | File metadata only; never index the stored file directly | File node (name, hash) linked to its `source` |

*Tier 3: private partitions (each domain or the sponsor indexes only its own).*
`contribution-draft`, `domain-chat-turn`, `domain-conversation`,
`domain-handoff`, `domain-work-plan`, `domain-prototype-plan`,
`domain-user-flow`, private `source`, private building blocks, need contexts,
`developer-brief`, `intake-draft`, `goal-draft`, `success-measure-draft`. These
can feed a per-domain corpus and graph that only that workbench's search and AI
partner query. They never enter the shared corpus. The only bridge into the
shared graph is publication, through the `RELEASED_AS` edge that `packet-release`
already records. This is the two-space boundary applied to retrieval.

*Tier 4: kept out.* Private AI partner threads in the separate thought-partner
store (unless separately decided), file preferences and upload attempts, demo
fixture records (`demo-package`, `demo-scenario`), and signatures, fingerprints
and hashes, which become properties, never text.

**Graph model.**

- **Nodes:** an entity node per stable ID (kind, scope, context areas) and a
  revision node per version (revision, time, author, origin of wording). Edges
  connect revisions, never "the latest". A `CURRENT` pointer marks the newest.
- **Properties:** evidence coverage, confidence rating and contributions from;
  publication and review state; reach, audience and scope; effective and
  recorded time. Never merged.
- **Typical traversals:** "what does this requirement rest on?" walks back along
  `BASED_ON`, `CITES` and `INFORMED_BY`; "what does this change affect?" walks
  forward along `DEPENDS_ON` and `CONTAINS`; "where did this lesson come from and
  where was it reused?"; "which terms differ between Research and Design?".

**Corpus rules.**

- One passage per meaningful field, never a whole JSON body.
- Current revisions are searchable by default; older revisions sit in a history
  partition for replay questions ("what did we believe in October?").
- Index each fact once. Snapshots and context copies are not re-indexed, so
  repeated copies cannot look like corroboration.
- Filter by the reader's access at query time. SQLite scope is the authority;
  the index only filters.
- Keyword search first. Add vectors when tests show keyword search missing useful
  context.

**A typed relationships table (Built).** Add a
`relationships` table to SQLite (from revision, to revision, type, properties,
review state, context area), written in the same transaction as the record.
The graph then becomes a straight projection instead of parsing about 40 body
fields. *Built:* `Store.put` writes the `relationships` table in the same transaction,
through extractors registered in `relationships.py`; `Store.backfill_relationships`
indexes older revisions and is idempotent; `Store.relationships(scopes)` reads
current links by scope. It covers block links and contribution references to
requirements; the NetworkX projection still reads `dependencies`. Existing body fields stay as they are; a one-time backfill fills the table
from them and is checked against the current `dependencies` rows.

### Laddering up to enterprise intelligence

The same structure answers questions at four levels. Each level sees only what
has crossed the boundary into it.

| Level | Sees | Example question |
| --- | --- | --- |
| Workbench | My private blocks and sources | "Which of my observations support this finding?" |
| Project | Published contributions, requirements, decisions | "Which requirements still have no evidence from Design?" |
| Domain | Published knowledge across the domain's projects | "What has Research learned about rescheduling across clinics?" |
| Enterprise | Promoted lessons, standards and adopted concepts | "Where do our teams disagree about what 'appointment' means, and what did each decide?" |

An enterprise query follows the same path every time:

1. Find candidates in the corpus, filtered by the asker's access and the
   knowledge's reach.
2. Walk the graph from each candidate to its sources, applicability, decisions,
   outcomes and counterexamples.
3. Apply the reuse gates (section 11): purpose, scope, current basis, authority,
   no unresolved challenge.
4. Answer with lineage and limits: which projects, which populations, how sure,
   what contradicts it.

Rules: only published or promoted knowledge answers enterprise questions;
repetition across projects is a signal to review, not proof; an answer always
shows where it came from and where it may not apply.

### Build order

Steps 1 to 7 follow [D014](decisions/D014-chained-packets-and-dependency-difference.md)
and were built on 26 November 2026 (see "What was built" there for limits).

1. Components and block recipes as configuration, reviewed by practitioners.
2. The typed relationships table, written in the same transaction as the record,
   backfilled from body fields (changes how records are saved).
3. Conditions captured on links: AI-proposed, person-confirmed.
4. The deterministic signature and difference service, feeding the bridge.
5. The feeds rule and coaching on missing components.
6. Packet types and the structure check.
7. AI review checks for scope and basis.
8. The corpus projection with keyword search and access filtering.
9. The property graph projection with the traversals above.
10. An enterprise query surface over promoted knowledge.
11. Vector search only when retrieval tests justify it.

---

## 9 Context packets and the execution basis

*Status: minimal manifest with audience check and exact resolution Built; recipe,
registry, reverse index and coverage record To build.*

### Why packets matter more when work is asynchronous

When people are rarely together, the packet is how the reasoning travels. It is
the exact basis a person or model used for a task, frozen so that someone who
arrives later can see precisely what was known, what was assumed and what was
open.

### The packet is an issued basis

A packet records what was assembled for a particular use. Once issued, its
selected versions never silently change. A **recipe** is the versioned plan for
producing a packet: required knowledge types, retrieval queries, evidence
criteria, policy and domain-manifest versions, scope, budgets and stop
conditions. Running the same recipe later can produce a new packet if inputs
changed. Keep both.

*Built today:*

```python
m = store.packet(id, rev, purpose, refs, audience, requester_scopes)
r = store.resolve_packet(id, rev, allowed_scopes)  # exact contents + changed_refs
```

The manifest holds identity, revision, purpose, audience scopes and exact
references. The audience must be a subset of the requester's scopes, and every
reference is read as the audience. Resolution returns the issued versions and
separately reports which have newer versions. It never fetches external links,
substitutes current content, infers support or grants access by naming an
audience.

Publication creates a prepared packet at preflight (`packet_preparation.py`)
pinning the draft version, evidence, linked requirements and goals, and the
author's statement of implications, downstream needs and open questions.

### Packet types and chains (Built: detection and preview)

Under [D014](decisions/D014-chained-packets-and-dependency-difference.md) a packet
type is defined by five things: an **anchor**, the **relation types** it follows, a
**depth**, an **audience scope** and a **revision policy** (pinned or latest). Its
contents are computed: follow those relations from the anchor to that depth, keep
what the audience may see, apply the policy. A Design review follows *informed by*
and *evaluated by*; a sponsor update follows *rests on* and *changed by*.

- **Chains are the trace.** A later packet that uses a block an earlier packet
  pinned links the two. Membership alone is never a dependency.
- **Services detect differences; reviewers judge them.** For a block shared by two
  groups, the signature is each group's relations, pinned revision, conditions and
  use around it. A service reports differences by kind (scope broadened or narrowed,
  different relation or use, revision skew), never by meaning. The AI reviewer
  proposes whether a difference is compatible, unsupported or contradictory; a
  person confirms; material consequences go to the decision owner.
- **Mappings locate; they do not equate.** A mapped concept's type, direction and
  conditions decide reuse. Evidence about a narrower concept is an instance of the
  broader one, never a generalisation.
- **Evidence.** In [the wave test](evaluations/wave-test.md), rolling model
  summaries lost facts and invented dependencies, while the computed report found
  every planted difference in scope, mapping and pinned revision.

*Built:* `knowledge_structure.py` provides `differences` (by kind),
`packet_contents` (three configured packet types, read-only through the
`packet-type-preview` command) and `structure_check`, shown as System checks in
Decisions & Issues. Issuing typed packets and comparing meaning-layer mappings are
To build.

### Assemble task context in a controlled order (To build as one service)

1. Resolve the person's identity, project membership, role, permitted purpose
   and current workflow state before any retrieval.
2. Read governing facts directly: exact intent, requirements, decision rights,
   active decisions, scope exclusions. Never ask a model to rediscover what the
   application owns.
3. Select the recipe and the assessment standard for the intended use.
4. Resolve explicit dependencies and exact source revisions. Search may nominate
   more candidates; they enter as candidates with provenance.
5. Check applicability against the person, job, situation, environment, system
   version and time. A shared tag is only a possible connection.
6. Include open questions, material counterevidence, competing interpretations
   and the boundaries of prior decisions.
7. Apply the receiving audience's access policy to every object and excerpt.
   A person who can read a private draft cannot thereby release it.
8. Resolve the accepted set into a packet, record omissions and coverage,
   validate schema and freshness, and compute the fingerprint on the server.
9. Send only this basis and the registered instructions to the model. Persist
   its structured output, references, uncertainty and reasons as a new
   attributed record.
10. Validate the output and route any consequential proposal to the authorized
    person. Publication, requirement revision and external writes remain
    separate transactions.

### Historical replay and current review

Replay resolves the packet as issued, subject to current access. A current
review builds a new packet against today's basis. Keep these visible as two
modes. Never combine an old judgment with new evidence and present it as the
original.

### Coverage and budgets

A packet does not copy the truth of what it selects. It records a bounded basis.
When material cannot fit the model's budget, narrow the question or split it,
keeping the frozen condition inventory and a coverage manifest across batches.
Reassemble by condition and reject missing, duplicated or inconsistent
judgments. A shortened answer must still name every unresolved material gap.

### What "at execution" means

Immediately before a model call, the application resolves the acting identity,
destination, exact context and current read authority. Immediately before
committing a result or writing externally, it rechecks decision rights, expected
revisions, current basis and the exact approved payload. A check made when work
was assigned is not enough. This matters most in asynchronous work, where hours
or days can pass between assignment and execution.

---

## 10 Assessment and honest uncertainty

*Status: condition inventory and human-recorded assessments, evidence coverage,
confidence signals Built; semantic review and AI-proposed scoped assessment To build.*

### Three signals, never merged

Each requirement shows ([D012](decisions/D012-confidence-signals.md)):

- **Confidence rating:** the requirement owner's recorded judgment for a named
  use: Not rated, Low, Moderate, High.
- **Evidence coverage:** counted from shared work: Empty, Low, Moderate, High
  ([D004](decisions/D004-requirement-evidence-level.md)). It measures coverage, not
  quality: two contributions can repeat one weak source, and recent work can be
  irrelevant. Quality is assessed against the claim and intended use (below).
- **Contributions from:** which teams have published work on the current version.
  Publication is not validation.

Labels follow [D014 revision 2](decisions/D014-chained-packets-and-dependency-difference.md);
they were "Evidence level" and "Validated by". The coverage calculation (`requirement_evidence.py`) uses explicit, testable
thresholds. High needs at least 2 contributions on the current version, from at
least 2 teams, the newest within 90 days, and no open gaps. Evidence older than
180 days caps at Low. An open contradiction caps it at Low, as does having no shared work on the current version. The result
includes `raise_to`: the next level and exactly what it needs.

Rules:

- Confidence rises only through reassessment, never automatically. A changed
  basis, or newer shared work, marks a rating "Needs reassessment"; the rating
  stays as recorded until the owner reassesses.
- Roll-up takes the weakest part.
- Levels, not percentages. No universal source count defines a rating.
- Low confidence alone does not block progress. The contemplated action must stay
  within its permissions, mandatory constraints and authorized limits. Proceeding is
  a recorded readiness decision.

### How the AI discerns and evaluates a packet (D014)

1. **Discern (partly Built):** sort new material into block types, fill
   components and link conditions, flag missing ones. Suggestions save
   provisionally; confirmation is needed only when they materially change scope,
   published meaning or a commitment; they count only once validated, and
   publication is the validation point.
2. **Check the structure (service, Built):** components each category needs,
   packets pinned to old revisions, detected differences between groups, what an
   open challenge reaches. `changed_refs` and the bridge already cover part of this.
3. **Evidence coverage (service, Built):** the thresholds above, with `raise_to`
   and the underlying facts, including independent sources. High needs 2
   independent sources; current work that cites no source is Low. Applicability
   is judged by reviewers.
4. **AI review (partly Built):** the reviewer checks work against project
   expectations, is told to check scope and basis, and may return an optional
   scoped assessment (scope check, basis check, contradictions, assessment, its
   confidence in the recommendation, reasons). Displaying it is To build.
5. **People decide (Built):** the owner records the official rating for a named
   use; new work prompts reassessment; readiness is a recorded human call.
6. **Check before acting (Built for delivery export):** `execution_gate.py`
   rechecks the actor's permission and pinned versions; open challenges on the
   basis need an acknowledgment.

AI proposes a scoped assessment with reasons; the owner records the official
judgment. Neither act makes unsupported evidence true.

### Freeze the question before grading

An assessment names its intended use (investigation, prototype or
implementation, from `config/requirement_assessment_profiles.v1.json`). Each
profile lists checks with their required evidence level and whether "not
applicable" is allowed. The condition inventory is frozen
(`requirement-inventory-freeze`) before grading, so repeated runs compare
against the same conditions and nobody can quietly drop a hard clause.

| Judgment | Meaning |
| --- | --- |
| Met | Every material part is directly supported at the required level |
| Partial | Name the supported parts and the outstanding parts |
| Missing | Required support is absent within the reviewed boundary |
| Uncertain | Material exists but meaning, applicability or sufficiency is unresolved |
| Contradicted | Applicable opposing evidence is cited and the conflict explained |
| Not assessed | Unfinished; never counts as passing |
| Not applicable | Grounded scope reason tied to this condition |

Missing must never become not applicable. Uncertain must never become missing
just because no direct quote exists. A valid quote can still be irrelevant:
structural validation does not prove that a passage supports a claim.

### Judge evidence and argument

Evidence identifies the exact source revision, span and quote, who observed or
asserted it, method, setting, population, date and limits. Judge method by
fitness to the question. A small study can establish that a failure happens
without proving how often. Copies of one origin are one lineage; repeated model
summaries are not corroboration.

A sound business argument connects an observed problem, the people and situation
affected, the cost, a plausible mechanism of improvement, alternatives,
measurable outcomes and constraints. A polished value statement and many
agreeing stakeholders do not replace evidence that the mechanism works.

### Confidence interpretation (proposed starting standard)

| Rating | Interpretation for a named use |
| --- | --- |
| Low | Important premises rest on assertion, indirect support or material unresolved limits. Useful as a hunch or a bounded inquiry |
| Moderate | Applicable direct support exists, with material limits in coverage, method, independence or transfer that stay visible |
| High | Strong applicable support and sound inference cover the material conditions; known alternatives and counterevidence addressed |
| Not rated | No valid recorded assessment; show the absence, never invent a rating |

These are starting definitions for domain review, not calibrated probabilities.

### Distinct receipts, distinct questions

A schema check verifies shape. A citation check verifies that a quote exists. A
semantic review judges whether it supports the claim for this situation. An
empirical evaluation tests whether the claim holds in use. A decision records
who accepted a consequence. Store these separately; none replaces another.

### Give a useful next step

Every assessment ends with the supported conclusions, every unresolved material
gap, a proportionate next action and the role accountable for it. A hunch stays
an attributed lead with a revisit trigger. The reviewer can say a thesis may be
wrong and recommend a bounded path without lowering the standard.

---

## 11 Change propagation and selective reuse

*Status: recorded dependency tracing, stale checks and basis-change signals Built;
reuse gates, review frontier and event-driven stale marking To build.*

Adaptation is only trustworthy if a change reaches exactly the work it affects,
and nothing else. In asynchronous work this is the mechanism that replaces "did
you hear what changed in the meeting?".

### How change travels

```
new evidence ─▶ proposal against exact version ─▶ reviews ─▶ decision
                                                               │
        ┌──────────────────────────────────────────────────────┘
        ▼
 successor version + decision record + new packet version   (one transaction)
        │
        ▼
 dependents of the OLD version found (recorded dependencies first)
        │
        ▼
 each dependent flagged for its owner ─▶ owner decides; nothing auto-rewritten
```

*Built:* dependencies between exact revisions (`Store.depend`); a NetworkX
projection rebuilt on demand (`Store.graph`); `ImpactWorker` returns affected
references with `pending-human-review`; requirement impacts in project state;
workbenches show a changed basis; reviews whose basis fingerprint no longer
matches cannot clear a decision.

*To build:* emit a change event in the same transaction as the decision
(section 14); a reverse index from each record to the packets and assessments
that used it; mark exactly those stale; enqueue a task for each owner; notify
asynchronously as a digest.

### Decide what happens after related knowledge is found

Retrieval starts judgment; it does not end it. After reaching a related record,
resolve its exact wording and sources, check who may use it, compare its
applicability with the current task, inspect its assessment standard and
decision boundary, and identify material changes since the last judgment. The
outcome is one of: reuse, reuse with a stated qualification, targeted
reassessment, clarification request, or exclusion with a reason.

Carry accepted interpretation forward while its basis and use remain valid. Do
not re-interpret the same evidence on every screen. Persist the judgment with an
input fingerprint covering the claim and evidence references, material
conditions, intended use, criteria and policy versions, domain manifest and
mapping versions, accepted clarifications, the assessment contract version and
the access basis. A new chat message or a cosmetic edit does not invalidate it.
A model change triggers regression evaluation, not a rewrite of human
decisions.

### Use hard gates before ranking

A reusable judgment must pass every gate: current access permitted; purpose
compatible; scope and conditions apply; basis current or explicitly historical;
standard still valid; authority sufficient for the contemplated action; no
unresolved material challenge. An unknown gate is recorded and resolved with the
smallest review needed. A high similarity score never compensates for a failed
gate.

```python
eligible = all([access, purpose_fit, scope_fit, basis_valid,
                standard_valid, authority_fit, no_material_challenge])
# Rank only eligible optional candidates with a named, versioned policy.
# A score cannot override a failed gate or prove truth.
```

Ranking weights (task fit, situation fit, source quality, applicability, change
relevance, recency) must be named, versioned and tested on labelled examples.
They are prioritization heuristics, not probabilities of truth.

### Traverse until the relevant basis is reached

A change travels backward to the premise that gives a challenged claim its
meaning, and forward to recorded consumers. Stop backward at a still-valid
assessment that already establishes the premise for the same use. Continue
when the premise itself is challenged, evidence is missing, a mapping changed or
the previous assessment cannot explain its basis.

```text
queue   := changed exact references
visited := empty set
while queue has work and review budget remains:
    item := pop(queue)
    skip if (item revision, review reason) in visited
    add (item revision, review reason) to visited
    resolve permitted evidence and recorded consumers
    for each relevant relationship:
        if the current judgment passes the reuse gates: keep it
        else: enqueue only the affected premise or consumer
record reviewed nodes, exclusions, open questions and the remaining frontier
```

Classify the change first. A label edit leaves reasoning intact. A changed
evidence span, scope exclusion, method, permission, accepted clarification or
policy can affect specific consumers. Bound discretionary search by time, cost
and node count, and record the **review frontier**: the connected work not yet
examined. A budget stop means incomplete coverage. It is never reported as "no
impact".

### Asynchronous adaptation in practice

When intent moved to version 2 in the clinic project, three things happened:

- Mei's design workbench showed "basis changed" with the difference. Her
  in-progress concept stayed hers; she chose how to respond.
- The requirement that depended on the old problem statement was flagged for
  Sofia. It was not rewritten.
- Research's published finding, already on version 2, needed nothing.

That selective, owner-respecting response is the target for every change, at
any scale.

---

## 12 Sources and connectors

*Status: file upload with text extraction, read-only FigJam, Figma and Lucid imports
per user, source release at publication Built; enterprise connectors, source
receipts and change tracking To build.*

### Start with a bounded collection

Begin with the material one project actually needs. Ask what is being
investigated, which teams and systems are in scope, which period matters and who
may receive the result. Connect selected files and folders before considering
broad mailbox or chat ingestion. Breadth does not make the brain smarter; it
makes it noisier.

### What exists

- **Upload:** files attached to a workbench conversation are stored privately in
  the domain with their text extracted (`domain-chat-attach`, `domain-source`).
- **Tool imports** (`tool_imports.py`): read-only MCP imports from FigJam,
  Figma and Lucid, using each person's own connection. Project context is never
  sent to the tool server. Imported content becomes a private source.
- **Release:** at publication, the owner chooses which private sources are
  released with the contribution. Release is explicit and previewed.
- **Design PDF pages:** page images attached for visual review
  (`design-pdf-attach`).

### Register original material separately from knowledge (To build)

Each source receipt should carry: provider and tenant, native item ID, revision
or change token, retrieval time, source date, content hash, exact permitted
excerpt or file version, locator scheme, access and sharing scope, retention
category, and extraction method and quality. Label generated summaries and
meeting recaps as generated, never as verbatim records. A derived summary keeps
its links to what it summarizes.

### Extraction is a candidate, not a fact

Normalize text, tables and images without discarding their form. Missing pages,
low OCR confidence and unreadable diagrams are extraction limits; show them to
the reviewer when they could change a judgment. A source can contain
instructions as quoted text; they never authorize tools, publication or state
changes. Every extracted item stays a candidate until a person reviews it.

### Access is checked for the audience, not only the reader

A connector that trims results to what the requesting person may read protects
that person's access. The system must still check whether selected material may
be released to the packet's receiving audience. The sponsor's access to a
private document does not grant Research access. Recheck at retrieval, preview,
release, model dispatch and replay. When policy prevents keeping an original,
keep only what is permitted and record the resulting limit on reconstruction.

### Connector checklist (To build)

- Validate any filter or scope expression before a query runs; a malformed
  filter must fail closed, never fall back to an unscoped search.
- Persist provider continuation tokens; handle expiry, deletions and lost
  subscriptions.
- Cache extraction and reviewed knowledge by exact source revision; re-run only
  what changed.
- Add semantic (vector) indexing only when tests show that IDs, metadata and
  keyword search miss valuable context. Embedding everything is not a
  prerequisite and solves neither permissions nor evidence quality.
- Measure retrieval latency separately from the time people spend judging
  results.

---

## 13 Bounded AI skills and the agent layer

*Status: model adapters, execution receipts and four active reasoning patterns
Built; workflow controller and additional agents To build.*

### Agents move knowledge; experts own it

Agents are orchestrators, not experts. They move, select, compare and package
context across the two spaces. The researchers, designers and decision owners
are the experts, and their expertise lives in domain knowledge, not in an agent.
In an asynchronous system agents do one more thing: they **keep work moving
while people are away**, by preparing what each person will need when they
return, never by deciding for them.

### The model boundary (Built)

```python
class ModelProvider(Protocol):
    def status(self) -> dict: ...
    def generate(self, *, instructions: str, context: dict, schema: dict) -> dict: ...
```

- `instructions`: the registered contract for the operation.
- `context`: the exact, scope-checked basis the service assembled. No browsing,
  no tools, no database.
- `schema`: the JSON shape the output must match.
- Returns `{"output": ...}` or raises `ModelUnavailable` with a safe message.

Adapters: `OpenAIModel` (also page images), `AnthropicModel`,
`UnconfiguredModel`. Connections are managed per project by an administrator
(`model_connection.py`); keys stay server-side.

### Every model operation follows one pattern

1. Resolve the exact permitted context (section 9).
2. Open an execution receipt with agent, version, skill, purpose, actor, basis
   and configuration fingerprint (`agent_runs.py`).
3. Reserve the maximum permitted cost (To build; section 17).
4. Call the adapter.
5. Settle usage even if the answer is incomplete or unusable.
6. Validate schema, references and frozen conditions; cited IDs must exist.
7. Recheck the basis and authority; if the basis changed, reject the result.
8. Save the advisory output as a separate record, or a safe failure receipt.

Publication, ratification and external writes stay separate transactions started
by authorized people.

### Execution contract

Every operation is registered with:

| Field | Meaning |
| --- | --- |
| Trigger | The event that may start it; a trigger requests evaluation, it proves nothing |
| Objective | What it is for, in one sentence |
| Input contract | The exact context it receives, assembled and checked by a service |
| Permitted audiences | Who may receive its output |
| Allowed tools | An allowlist checked by code outside the model |
| Output schema | Structured proposals with citations and uncertainty |
| Evaluation cases | The cases it must pass before activation |
| Limits | Maximum context, output, steps, time and cost; retry rule |
| Stop and escalation | When to stop and which human owner receives the case |

A model cannot gain a tool by naming it in its output. Retrieved text is
evidence, never a new instruction channel.

### Agent roster

`config/agent_personas.json` describes fourteen roles; `agent_catalog.py`
reports in code which are implemented. Descriptions do not create executable
agents.

| ID | Role | Moves knowledge from → to | Status |
| --- | --- | --- | --- |
| P01 | Supervisor | Proposes a plan for a complex task; the controller enforces it | To build (routing is code today) |
| P02 | Intake AI partner | Sponsor documents → a clear, testable business frame | Partial: live, seven skills, per-question expertise |
| P03 | Context assistant | Enterprise and domain guidance → the sponsor's view | To build |
| P04 | Requirement assistant | Intent → candidate requirements, criteria, goals, measures | Partial: drafts and reviews for human approval |
| P05 | Extraction worker | Raw sources → attributed passages | Partial: ordinary code, no model role |
| P06 | Evidence AI partner | Research work ↔ evidence standards and project basis | Partial: shared domain-coach runtime |
| P07 | Domain context AI partner | Any domain's work ↔ its vocabulary, standards, methods | Partial: shared runtime, configured per domain |
| P08 | Mapping assistant | One domain's meaning ↔ another's | To build (human mapping proposals exist) |
| P09 | Reconciliation assistant | Published positions → a cited delta for Decisions & Issues | To build |
| P10 | Impact assistant | A proposed change → who and what is affected | Partial: code follows recorded dependencies |
| P11 | Options assistant | Positions → an even-handed comparison | To build |
| P12 | Artifact fit assistant | Delivered artifact ↔ agreed requirements | Partial: design visual review |
| P13 | Change analyst | A changed basis → affected decisions and packets | To build |
| P14 | Ratification coordinator | Decision records, unambiguous | Code handles gates; no model role needed |

### Minimal executable patterns to build next

| Pattern | Reasoning task | Service and human boundary |
| --- | --- | --- |
| Prepare the return | While a person is away, summarize what changed in their basis and what waits on them | Service selects events and records; person reads, nothing is changed |
| Reconcile positions | Compare published positions on one requirement and draft a cited delta | Service pairs claims and runs deterministic checks; owner decides |
| Meaning comparison | Suggest how two bounded concepts overlap or differ | Leads or steward decide mapping and reach |
| Consequence review | Explain plausible impacts along recorded dependencies | Service traverses; owners judge materiality |
| Propose a lesson | Draft a scoped lesson from an outcome or a closed issue | Steward reviews; receiving owner adopts or declines |
| Delivery preparation | Draft a work item update from a decision | Service previews the exact payload and rechecks authority before any write |

### The controller (To build)

A deterministic controller owns every run: queued, running, waiting for input or
review, resumed, completed, failed, cancelled. It checks identity, project,
workflow state and allowed actions before a run, picks the registered pattern,
enforces budgets and checkpoints, and escalates on its stop conditions. Agents
are stateless between calls. A supervisory model is unnecessary until a measured
task needs one. Extend `agent_runs.py` into run state rather than starting over.

### Review language before acting

For an ambiguous request, identify the action, affected people, conditions,
authority and intended outcome. Offer a precise interpretation and ask one
focused clarification when the ambiguity would change the action. Save an
accepted clarification as a versioned decision that later packets carry. Do not
reopen an unchanged clarification on every screen.

---

## 14 Durable workflow, events and commands

*Status: single-entry command surface, transactions and optimistic concurrency
Built; outbox, event intake, idempotency keys and durable run state To build.*

The prototype's in-process transactions and locks are a sound local foundation.
They are not a distributed job system. Asynchronous work across days needs
durable state so that a restart, a duplicate event or an interrupted review never
loses work or repeats a commitment.

### Commands today (Built)

The browser posts an action name and data to `/api/state`. `Workspace.command`
is the single entry point and dispatches to about 170 service methods
(Appendix B). Consequential actions (decisions, decision-rights actions, intent
adoption and disposition, intake publication and close) run inside one
transaction with a Decisions & Issues guard before and a sync after.

To add a command: write the service method; take `expected` references for
anything it changes; validate input with `validation.py`; register it in the
action table; test the success path, the stale path and the unauthorized path.

### The transactional outbox (To build)

When a person publishes, decides or adopts, write the new records and an
**outbox event** in the same database transaction. A dispatcher publishes
committed events to the queue. A consumer records the event ID and an operation
key before producing any consequential effect. Expect retries and duplicate
delivery; make the business effect idempotent regardless of what the queue
promises.

Minimum events: intent published, contribution published, issue raised or
answered, proposal submitted, review given, decision recorded, readiness
decided, domain knowledge changed, meaning adopted, access changed.

### One command, one intended effect

- Carry a durable **command ID** across every retry and an **event ID** for
  transport deduplication.
- Derive an **operation key** from event ID, tenant and project, exact target,
  operation and skill version, basis fingerprint and audience. Never deduplicate
  by prompt text: the same words with different authority or basis are a
  different task.
- Enforce a unique business-effect constraint. A reused key with a different
  payload is a conflict. An identical retry returns the original receipt.
- Persist claim status, attempts, lease expiry, next attempt, outcome, cost
  reservation and reconciliation state.

Today, publication and packet signatures already refuse an identical duplicate.
Extend that guarantee to every consequential command.

### Transaction boundaries

Inside one transaction: verify expected versions and current authority, apply
the transition, append revisions, save the receipt, write the outbox event. Do
remote work after commit through a durable attempt. Never hold a database
transaction open across a network call. Reconcile an uncertain provider outcome
before retrying it.

### Messages carry references, not content

Queue messages hold record references and minimum routing data. Workers resolve
protected content through the context service at execution time. A job
scheduled while a person had access must fail safely if access or authority has
since changed, recording a stopped or stale result. It must never substitute
newer sources into an old packet.

### Retries

Deterministic reads and projections retry under a bounded policy. Model retries
need their own cost reservation and respect the run ceiling. An ambiguous
external write is reconciled before any further attempt. A repair may correct
the invalid part of a model result under a strict allowance, keeping the
original. Exhausting a budget yields an incomplete review, never a fabricated
completion.

### Service interface rules (To build)

All mutations use a server-resolved principal, a target scope, an expected
revision or exact expected basis, and an idempotency key. Never trust an actor,
role or approval supplied in a request body. Return a receipt with command ID,
principal, operation, previous and new references, basis references, time, state
and trace ID. External writes add destination, external ID and version, and a
confirmed result or an explicit unknown outcome.

---

## 15 Identity, authority and governed release

*Status: local accounts bound to one actor, scope-derived access, decision rights,
readiness and meaning authority Built; enterprise identity To build.*

### People, roles and authority are separate

The same person can work in several domains; a role can be held by several
people. The prototype's actors (sponsor, Research lead, Design lead,
requirement owner, administrator) are scenario identities, not a workforce
model. Local accounts are loopback-only and bind one account to one actor;
membership never follows a client-posted role. A production identity adapter must
resolve the authenticated principal to current project membership, domain
access, professional responsibilities and specific decision rights.

For OpenID Connect, validate issuer, audience, signature and token lifetime;
map a stable issuer and subject, never a display name. Keep authentication
separate from the application's decisions about reading a source, releasing it
to an audience or ratifying a proposal. The identity provider does not know what
a project decision means.

### Recheck at every boundary

Recheck access at discovery, retrieval, packet assembly, model dispatch,
publication, replay and external write. A valid packet is a record of its basis,
not a permanent grant. A revoked source can make an old packet unavailable to a
current reader; explain the limit without revealing the hidden source.

### Keep private thinking private

The coach may challenge an assumption or suggest a better method without
creating a shared issue, announcing a deficiency or touching someone else's
record. The professional chooses what to publish. Show the exact release,
audience and limits at that moment instead of wrapping ordinary thinking in
approval steps.

### Authority at each boundary

| Act | Who may do it | Checked at the moment | What is retained | Status |
| --- | --- | --- | --- | --- |
| Save private work | Author or domain collaborator | Membership; expected draft revision | New private revision with author | Built |
| Publish selected work | Author or designated releaser | Preflight still current; each source releasable to the audience | Publication, contribution, released sources, packet | Built |
| Propose a change to intent or a requirement | Any authorized participant | Proposal cites the current target and its basis | Proposal and affected references; baseline unchanged | Built |
| Review a proposal | Required reviewers | Review covers the current basis fingerprint | Review with disposition and limits | Built |
| Ratify a change | Named decision owner | Current authority, fresh basis, required reviews, explicit disposition and confirmation | Decision, successor versions, or recorded rejection or deferral | Built |
| Defer | Decision owner | Named next owner and question | Deferral with both | Built |
| Proceed with limited evidence | Readiness decider (business direction decider or delegate) | Server-computed basis and fingerprint | Readiness decision with conditions | Built |
| Map or share meaning | Required leads; steward for enterprise reach, as different people | Declared reach and type | Versioned proposal and decision | Built |
| Adopt an enterprise concept | That team's lead, with a reason | Pinned concept version | Adoption record | Built |
| Execute an external write | Authorized person or tightly delegated identity | Approved exact payload; target version; idempotency | Provider receipt and readback, or explicit partial failure | To build |

### Record the consequential decision

A decision identifies what was decided, the exact versions, the evidence
considered, material counterevidence, alternatives, the owner, the authority
used, the disposition and the rationale, and stores consequences and the next
review condition. It never records that evidence is true merely because a
sponsor accepted a direction. Committing to investigate, accepting a prototype
risk and publishing a finding are different acts.

When a decision changes intent, create the successor intent and requirement
versions, link predecessor and decision, and emit the change event atomically.
New evidence opens reconsideration; it does not rewrite approved meaning, erase
dissent or close the original gap.

### Provider and content security

Keep secrets in approved storage. Send the minimum permitted context to the
registered model endpoint; make provider retention terms explicit for each data
class. Treat attachments, source text and connector results as untrusted. Validate
tool arguments and returned references in code. A shared review account and a role
switcher support exploration; they provide no individual accountability.

---

## 16 Delivery and outcome feedback

*Status: developer brief, delivery staging and export, delivery receipts that
never simulate external writes Built; authorized work-tracker writes, readback and
outcome return To build.*

### Delivery can start before everything is validated

Work items can be created from Business Intent when the authorized purpose is
exploration, a prototype or a bounded brownfield change. The payload carries its
purpose, maturity, evidence limits and governing references. An exploratory story
is never presented as a substantiated production obligation. Later decisions
produce proposed revisions to the same items, with the receiving team's
acceptance kept visible.

### What exists

- **Developer brief** (`developer_brief.py`): a named, versioned implementation
  draft prepared from published work under the existing publication guards.
- **Delivery staging and export** (`delivery.py`): exact-version payloads
  exported for the work tracker; never simulates an external write.
- **Receipts** (`receipt_delivery.py`, `demo_delivery.py`): delivery
  observations that keep simulation distinct from external proof.

### Stage, preview, write, read back (To build)

Stage an exact payload: target project and item, operation, expected external
version, requirement and decision references, acceptance criteria, remaining
assumptions, dependencies and an idempotency key. Show an understandable preview
to the authorized person. At execution, recheck the decision and payload
version, connector scopes and target version.

After a write, keep the provider item ID, returned revision, operation receipt
and a readback of the fields that matter. For partial success, show succeeded
and failed items separately and retry only unresolved items under the same key.
If someone changed the external item, show the difference and ask for
reconciliation instead of overwriting. The work tracker remains the authority
for execution state; this system keeps why that state and its requirements
exist.

### Handoff states are not synonyms

| State | Evidence required | Still unproved |
| --- | --- | --- |
| Prepared | Exact staged payload and permitted target | No external change yet |
| Accepted for processing | Queue or provider acknowledgement | Item may not be committed |
| Committed | Provider item ID and revision | Receiver may not have accepted it |
| Delivered | Readback or agreed receipt | Execution and adoption |
| Acted on | Attributable delivery or operating event | The intended outcome |
| Outcome observed | Defined measure, period, population and provenance | Transfer to another setting |

### Bring outcomes home

Return observed outcomes through a read-only adapter first. Link each to the
intended result, requirement, decision, measurement method, period and
population. This is the input to the learning loop in section 5: an outcome can
confirm a lesson, narrow it, or reopen a requirement or the intent itself.

---

## 17 Operations, observability and model cost

*Status: execution receipts with usage Built; cost ledger, spend limits,
alerting and dashboards To build.*

### Receipts that explain what happened

Every important operation needs a receipt that explains it without keeping
hidden model reasoning. Today `agent-execution` records hold agent and version,
skill, purpose, actor, basis, configuration and fingerprint, provider, model,
mode (live, simulated, not connected), duration, usage, output reference or
error. **Cost is not yet recorded** (`cost` is empty). To build: correlation and
command IDs, authorization result, input and output contract versions, cost
reservation and settlement, a link from each retry to its predecessor. Keep raw
source text and secrets out of ordinary logs.

### Watch system health and knowledge health

| System health | Knowledge health |
| --- | --- |
| Availability, error rates, retries | Unresolved material gaps by project |
| Queue age and backlog | Stale or revoked bases still in use |
| Backup age and restore results | Rate of unsupported links or citations rejected |
| Model latency and failures | Reconsiderations opened and closed |
| Capacity | Share of reuse that needed correction |
| | **Waiting time** on consequential items, by role |

A busy agent or a large graph is not success. Dashboards help the accountable
person decide the next action and must never become surveillance of private
thinking. Waiting time is reported per item and role so stalls can be resolved,
not ranked per person.

### Incidents leave work recoverable

- A permission failure stops disclosure.
- A failed model call keeps the person's input and records an error turn.
- A changed basis makes a stale result ineligible for a new consequential action.
- An unknown external write enters reconciliation before any retry.
- An uncertain cost keeps its reservation and pauses further spend in that pool.

Show people a plain outcome and who owns it; keep diagnostics for support.

| Signal | Responding owner | Next action |
| --- | --- | --- |
| Denied or mis-scoped retrieval | Identity or source owner | Check the grant and audience; never broaden permissions to make a test pass |
| Unsupported interpretation or omitted condition | Domain reviewer and model-quality owner | Keep source and output; adjudicate; fix the contract before a targeted rerun |
| Changed governing basis | Record owner and affected domain lead | Review the bounded impact set; keep accepted history |
| Stalled publication or decision | Named next responder or decision owner | Clarify the missing input or authority; use the agreed escalation |
| Duplicate or uncertain external operation | Connector owner | Idempotency and readback; reconcile before another write |
| Cost or usage uncertainty | Budget owner | Keep the reservation, pause spend, reconcile with provider accounting |
| Storage or recovery failure | Service owner | Quiesce writes, preserve evidence, run the tested recovery plan |

### Enforce spending outside the model (To build)

Keep a durable spending ledger outside the model's reach. Before a call,
estimate conservatively from the actual payload and the maximum permitted output
and reserve that amount atomically against every applicable pool (operation,
project, service). Concurrent workers reserve from the same ledger. A prompt,
model response, agent plan or failed retry can never raise a limit. Settle
reported usage before parsing the answer: incomplete and refused responses can
still cost money. If the outcome or usage is unknown, keep the hold and stop the
pool until reconciled. Forecast an evaluation from expected call counts and
token distributions at the current approved rates, with the rate source and date
shown.

### Status helps people act

Run receipts, model versions and spend diagnostics belong in settings and support
views. Ordinary screens show an understandable outcome, what needs attention and
who responds next. The safeguards apply even when their details stay out of
sight.

---

## 18 Platform, migration and recovery

*Status: single-process server with SQLite per project and a separate enterprise
store Built; production platform, backup procedure and recovery objectives Owner
decision and To build.*

### Keep the architecture portable

Choose the production platform against explicit contracts, not impressions:
durable versions and transactions, identity and access, lineage, retrieval,
queues, model access, connectors, observability, recovery and operating
ownership. Reuse a platform service when it preserves the contract; record a
gap and an owner when it does not.

Prefer one owned application with clear internal services before splitting
roles into separately deployed agents. Deterministic services own record writes,
permissions, packet resolution, dependency traversal and state changes. Add
background workers where latency or reliability needs them. A queue, graph
database or orchestration framework is an implementation choice; the required
behaviour is explicit task state, bounded execution, recoverable handoffs and
reconstructable decisions. If a managed workflow engine is chosen, its execution
guarantee still does not remove the need for idempotent external actions and
application-level receipts.

| Platform proof | Required demonstration | Decision owner |
| --- | --- | --- |
| Identity | Named principal and group mapping; revoked access takes effect during an active workflow | Identity and application owners |
| Data and residency | Approved data classes, storage locations, retention and model destinations | Data, security and privacy owners |
| Records and events | Atomic versioned write plus outbox; idempotent replay; selective change propagation | Application architecture |
| Model access | Approved gateway, no secrets in clients, metering and spend stop | AI platform and budget owners |
| Source connector | Exact source and revision retrieval with audience permissions | Source and connector owners |
| Delivery adapter | Preview, authorized write, conflict handling, readback | Work-tracker and application owners |
| Operations | Observed recovery, alert routing, rollback, on-call path | Service owner |

### Install through witnessed stage exits

An installation is complete only when the approved environment carries a real
bounded workflow under its intended identity, data and operating controls. A
green health check proves only that a process answers. Keep a release evidence
folder: deployed commit, configuration and schema versions, identity
registrations, connector scopes, migration results, test records, recovery
evidence and named owners. Use separate identities, secrets, data stores and
spending pools for development, test and production. Before running more than
one instance, replace process-local sessions, locks and jobs with tested shared
coordination.

### Back up the whole working system

Back up project catalogs, every project database, the enterprise store,
uploaded files, private conversations, accounts and memberships, domain and
model configuration, event and job state, connector checkpoints and the cost
ledger once it exists. For SQLite, quiesce requests and use the backup interface
or a quiesced full snapshot. Check integrity, row counts, logical digests and
file hashes. Restore into a separate environment before trusting a backup.

### Migrate without inventing history

Prefer additive schema changes, a versioned migration manifest and a feature
switch. Prove old and new readers over representative records before switching.
Rebuild graph and search projections from records. Never infer missing confidence
ratings, links or authors during migration: store absence as absence and flag
what needs reassessment.

### Recovery

Set recovery time and point objectives with the service and business owners. A
code rollback and a data rollback are different decisions. Restoring an old
enterprise store can discard later concept adoptions; restoring an old ledger can
erase real spend. Preserve current data and reconcile outstanding external
operations first. After recovery, prove sign-in, revocation, private boundaries,
exact historical packets, idempotent jobs and remaining budget.

---

## 19 Evaluation and the acceptance pack

*Status: over 1,100 Python and 800 UI tests, the launcher check and ten expertise
cases Built; semantic evaluation, asynchronous team observation and a bounded
pilot To build.*

### Four evaluation layers, reported separately

1. **Mechanical:** persistence, permissions, revisions, packet resolution,
   events, state enforcement. Covered today by the test suites and
   `run_demo.py --check`.
2. **Semantic:** is an interpretation supported, and does it cover the material
   conditions? Needs prepared cases and qualified adjudication.
3. **Team workflow:** can another person understand and continue the work from
   what the system shows, without the author?
4. **Operating pilot:** does the work improve coordination and decisions
   compared with the team's current method?

Passing one layer is not evidence for another.

### Prepare semantic cases before running a model

Freeze sources, material conditions, evidence level, domain configuration and
expected authority. Define admissible conclusions and legitimate uncertainty
instead of one exact sentence. Have a qualified reviewer adjudicate. Keep
original outputs, corrections, references and fingerprints. Repeated identical
outputs can repeat the same mistake. A rejected fabrication shows the safeguard
worked; it is still a model defect to count.

### Test the asynchronous loop with real separation

The founder can play every role to find broken mechanics, but that hides missing
handoff context, because one person remembers everything. Run the bounded case
again with independent people in separate roles, working at different times,
with no meeting. Observe what each can do from the system alone. Measure time
to continue, waiting time, clarification requests, corrections, decision
reversals and time to an accepted handoff. Get consent before recording people or
sending project material to an external model.

### First release gate

Zero observed unauthorized disclosures, unauthorized commitments, silent
historical overwrites, unmetered paid calls or fabricated evidence accepted in
the acceptance pack. These are control failures. An honest uncertain judgment is
not a failure. Semantic, effort and time targets are agreed for the pilot's
actual risk, with denominators and case mix reported.

### One integrated acceptance pack

| Case | Required behaviour | Fails if |
| --- | --- | --- |
| A private draft exists | Invisible to other domains and to the shared audience until published | Any other audience can read or infer it |
| A draft changes after preflight | Publication refuses; a new preview is required | The old preview publishes changed content |
| A private source is selected for release | Released only with explicit confirmation | Released implicitly with a contribution |
| A packet is requested for a wider audience | Refused unless the requester holds that audience | The packet widens access |
| Two people edit the same version | Second write fails; nothing is lost | Last write wins silently |
| An approval arrives after the basis changed | Decision blocked as stale | Decision commits on an old basis |
| A review does not cover the current basis | Cannot clear the decision | Old review counts |
| The same publication or event arrives twice | One commitment, traceable duplicate | Two decisions, releases or work items |
| A term differs between domains | Both meanings stay distinct in retrieval and in the AI partner | Shared label treated as equivalence |
| A sponsor claim has no evidence | Kept as an attributed, uncertain claim with a next step | Presented as fact |
| One requirement has several material conditions | Each condition judged against exact passages | Whole clause marked met from one condition |
| Two studies disagree | Population, method, scope, time and independence compared; disagreement kept | Newest or loudest wins |
| A prototype proceeds on low confidence | Readiness records purpose, limits, owner and trigger | Low confidence blocks all progress, or is presented as production-ready |
| Intent changes while Design is mid-work | Design sees "basis changed" with the difference; nothing rewritten | Design's work silently changed or not flagged |
| A decision owner is away for a week | Item stays waiting with owner and age visible; escalation per agreement | Treated as approved, or invisible |
| A model call fails | Input kept, error recorded, no invented content | Canned answer or lost input |
| A simulated model runs | Labelled simulated | Labelled live |
| A governing record changes | Exactly the dependent packets marked stale | All or none flagged |
| A traversal hits its budget | Unreviewed frontier recorded | "No impact" reported |
| Access is revoked mid-run | Further reads, releases and writes denied; audit kept | Cached packet bypasses access |
| A delivery write partly succeeds | Per-item results; reconcile before retry | Whole batch retried or all claimed done |
| A lesson is reused in another project | Original setting and limits shown; receiver adopts, adapts, declines or defers | Local pattern becomes universal truth |
| A packet is replayed after a source revision | Issued versions resolved; changes shown separately | Current content substituted |
| A deferral lacks an owner or question | Refused | Accepted |

---

## 20 Build sequence, owners and experience standards

*Status: recommended order; owners to be named.*

### Prove one complete asynchronous loop first

The first increment proves one sponsor-to-domains-to-decision-to-handoff loop
with real people working apart, one approved source collection and one material
change. Each later increment must let the next domain reuse the same contracts.
The founder owns product intent and consequential product decisions, and should
not become the default operator, connector owner, support desk or sole judge of
domain evidence.

Use stage exits, not calendar promises.

**Exit 1: Contracts in the prototype.** Outbox plus reverse-dependency stale
marking; one enforced agent execution contract with run states; a retrieval
interface with exact lookup and a labelled slot for keyword and vector search;
the acceptance pack in section 19 as automated tests where possible. Each with a
decision record.

**Exit 2: Durable foundation.** The store contract on the chosen relational
database; enterprise identity; model gateway with metering and spend limits;
controller and event intake; backup and restore rehearsed.

**Exit 3: Connected asynchronous workflow.** One approved source and named
identities. One finding carried through publication to an authorized revision
and a successor packet, with participants working at different times. A new
participant reconstructs the rationale from the system alone.

**Exit 4: Bounded intelligence.** One approved model configuration under a hard
ceiling. Semantic cases adjudicated; unresolved gaps preserved; selective
reconsideration shown after a material change. Actual usage and cost receipts.

**Exit 5: The brain learns.** One authorized, idempotent work-tracker write with
readback; one observed outcome linked back to its intent and decision; one lesson
reviewed and tested in a second project; one standard revised from a lesson.

Expand domains or connectors only when reuse has earned it.

### Accountable roles

| Workstream | Owner role | Responsibility |
| --- | --- | --- |
| Business purpose and pilot value | Business sponsor | Outcome, scope, baseline, acceptable experiment |
| Product and method | Product owner | The adaptive-intent contract and the smallest useful loop |
| Domain expertise | Domain lead | Block types, methods, evidence standards, domain knowledge |
| Shared meaning | Enterprise steward with affected leads | Reach, mappings, concept versions |
| Application architecture | Technical lead | Object, packet, command, event and agent contracts |
| Identity and data access | Identity and source owners | Grants, groups, source authority, revocation |
| Platform and operations | Service owner | Deploy, monitor, back up, recover, incidents |
| AI quality | Evaluation lead with independent domain reviewers | Cases, adjudication, approved model configurations |
| Delivery integration | Work-tracker owner | Staging, writes, idempotency, conflicts, feedback |
| Budget | Budget owner | Ceilings, forecasts, reconciliation |

### Experience standards

The product's visual system is set by [D007](decisions/D007-c2-tracker-design-system.md)
(light and dark themes, tokens in `theme.css`, strict CSP with no inline
styles). For behaviour:

- **Lead with what waits on the person.** Home starts with "Waiting on you";
  each item opens the exact record.
- **Make arrival easy.** A workbench opens with what was handed over until the
  person has a plan.
- **Keep the conversation dominant.** Tools sit on the cockpit rail, one panel
  at a time.
- **Quiet signals.** Counts on the rail, never pop-ups, for suggestions and
  updates.
- **Name actions by outcome.** "Prepare to share", "Ask for a review"; no two
  buttons with the same label.
- **Keep mechanics behind the experience.** IDs and internal versions belong in
  detail and audit views. The intent version is the only version a first-time
  person needs.
- **Never show a number that seems to contradict another.** Label every count by
  what it counts.
- **Separate signals stay separate.** Confidence, evidence and validated-by sit
  together and are never merged.
- **Keep the question field open** in every AI partner panel and preserve typed
  text across changes of context.
- **Show what is whose.** What the person wrote, what the model suggested, and
  what was saved or published are always distinguishable.
- **Check real pages.** Inspect populated pages at desktop, tablet and phone,
  light and dark, with independent users. Passing tests do not establish
  scannability.

---

## 21 Open decisions

| Decision | Needed from |
| --- | --- |
| Service owner and production platform | Product owner and platform leadership |
| Pilot workflow, baseline and participants | Business sponsor and domain leads |
| Enterprise identity and groups | Identity owner |
| Data classes, retention and model destinations | Data, security and privacy owners |
| Source collections and connector grants | Source owners |
| Evidence and confidence standards, assessment profiles | Domain leads and evaluation lead |
| Building block types (D013 is a starting point) | Research and design practitioners |
| Component recipes and category needs (D014 starting tables) | Research and design practitioners |
| D014 open questions: required relations, showing complements, who resolves conflicts, revision skew | Product owner |
| Practitioner review of the D014 starting tables now in configuration | Research and design practitioners |
| Response windows and escalation for waiting items | Product owner and sponsor |
| Notification and digest policy for asynchronous change | Product owner |
| Explicit practice checks in the AI partner | Product owner |
| Adopted and mapped meanings in the AI partner's context | Product owner and enterprise steward |
| Who may switch connectors on and off (administrator, user, both) | Product owner |
| Lesson review and promotion path to standards | Domain leads and steward |
| Delivery writes and outcome feedback | Work-tracker and receiving owners |
| Model and operation budgets | Budget owner |
| Recovery objectives and support coverage | Service owner and sponsor |

### The first next move

Name the business sponsor, technical lead and service owner for one valuable
workflow. Agree the source collection, domain standards, decision rights,
response windows and acceptance pack. Build the Exit 1 contracts behind the
current experience, then witness one complete asynchronous handoff with one
material change. Expand only after the team can show continuity,
recoverability, useful coaching and one real act of learning.

---

## Appendix A Example payloads

Synthetic values from the clinic demo. Proposed shapes are marked; they grant no
authority and are not current APIs unless stated.

### Current packet manifest (Built)

```json
{
  "id": "PKT-RESEARCH-PUB-1",
  "revision": 1,
  "purpose": "Publish Research finding on rescheduling",
  "audience_scopes": ["project:demo"],
  "refs": [
    {"id": "DRAFT-RESEARCH-1", "revision": 3},
    {"id": "INTENT-1", "revision": 2},
    {"id": "REQ-EASE", "revision": 1},
    {"id": "SRC-INTERVIEWS", "revision": 1}
  ]
}
```

### Proposed context packet envelope (To build)

```json
{
  "schema_version": "context-packet/1",
  "packet_ref": {"namespace": "riverbend", "id": "pkt-handoff-review", "revision": 2},
  "purpose": "review a proposed staff handoff requirement",
  "task_type": "requirement-review",
  "scope": {"tenant": "riverbend", "project": "ai-appointment-assistant", "domain": "design"},
  "audience": {"policy_ref": "access-policy:3", "recipient_roles": ["required-reviewer"]},
  "as_of": "2026-11-25T18:00:00Z",
  "recipe_ref": "requirement-review-recipe:1",
  "basis": {
    "intent_refs": ["intent:2"],
    "requirement_refs": ["req-staff-handoff:1"],
    "knowledge_refs": ["observation-known-in-advance:1", "finding-phone-only:2"],
    "source_refs": ["src-interviews:1"],
    "criteria_refs": ["assessment-profile-prototype:1"],
    "decision_refs": ["decision-intent-v2:1"]
  },
  "unresolved_refs": ["question-visit-types:1"],
  "authority": {"use": "advisory review", "ratification_permitted": false},
  "producer": {"service_version": "packet-builder/1", "run_ref": "run-0042"},
  "validity": {"recheck_on": ["basis-change", "access-change", "policy-change"]},
  "coverage": {"status": "bounded", "omissions": ["No scheduling system logs supplied"]},
  "integrity": {"manifest_hash": "computed by the application"}
}
```

### Proposed domain manifest (To build)

```json
{
  "domain_id": "research",
  "manifest_revision": 3,
  "block_types": ["observation@1", "finding@2", "user-situation@1", "lesson@1"],
  "assessment_profiles": ["investigation@1", "prototype@1"],
  "knowledge_version": "research-knowledge:7",
  "methods": ["expertise-methods:1"],
  "rights_policy": "project-rights:2",
  "tools": ["figjam-readonly@1", "lucid-readonly@1"],
  "evaluation_pack": "research-cases@1"
}
```

### Proposed committed event (To build)

```json
{
  "event_id": "evt-0107",
  "event_type": "contribution.published",
  "project_id": "ai-appointment-assistant",
  "subject": {"id": "CONTRIB-RESEARCH-1", "revision": 1},
  "basis_packet": {"id": "PKT-RESEARCH-PUB-1", "revision": 1},
  "domain_manifest": "research:3",
  "audience_policy_ref": "access-policy:3",
  "actor_ref": "principal-jordan",
  "command_id": "cmd-0091",
  "correlation_id": "change-intent-v2",
  "schema_version": 1
}
```

### Proposed return digest for an absent person (To build)

```json
{
  "for": "principal-mei",
  "since": "2026-11-21T17:00:00Z",
  "waiting_on_you": [{"kind": "review", "ref": "case-staff-handoff:1", "waiting_days": 2}],
  "your_basis_changed": [{"from": "intent:1", "to": "intent:2", "decision": "decision-intent-v2:1"}],
  "published_by_others": [{"ref": "contrib-research-1:1", "domain": "research"}],
  "nothing_changed_in": ["req-reminders:1"]
}
```

---

## Appendix B Command surface

### Current commands (Built)

All post to `/api/state` and dispatch through `Workspace.command`. Grouped:

- **Business Intent:** `intake-start`, `intake-save`, `intake-source`,
  `intake-build`, `intake-drawers`, `intake-configure`, `intake-coach`,
  `intake-coach-apply`, `intake-coach-fill-empty`, `intake-accept-value`,
  `intake-preflight`, `intake-request`, `intake-review`, `intake-publish`,
  `intake-close`, `intake-change-assess`, `intake-change-resolve`,
  `sponsor-save`, `sponsor-coach`, `sponsor-apply-advice`, `goals-save`,
  `goals-prepare`, `goals-apply`, `scaffold-tailor`, `scaffold-tailor-apply`.
- **Intent change:** `intent-refine`, `intent-adopt`, `intent-dispose`,
  `bridge-intent-propose`.
- **Requirements and assessment:** `requirement`, `requirement-agent-run`,
  `requirement-agent-apply`, `requirement-agent-settings`,
  `requirement-inventory-freeze`, `requirement-assessment-record`,
  `requirement-assessment-read`, `readiness-decide`, `field-coach`,
  `field-coach-check`, `field-coach-concern-prepare`, `field-coach-concern-publish`.
- **Integrity review:** `integrity-*` (assess, preflight, reconcile, propose,
  correct, gaps, options, promote and related).
- **Workbench:** `domain-chat-start`, `domain-chat-send`, `domain-chat-attach`,
  `domain-chat-context`, `domain-chat-focus`, `domain-chat-apply`,
  `domain-chat-recover`, `domain-brief-*`, `domain-objectives-*`,
  `domain-report-*`, `domain-findings-*`, `domain-submission-*`,
  `domain-prototype-*`, `domain-flow-*`, `domain-tool-*`, `design-pdf-attach`,
  `design-visual-review`, `knowledge-card-*`, `need-context-save`,
  `need-context-packet`, `suggestions-toggle`, `suggestions-dismiss`.
- **Publication:** `domain-prepare`, `domain-review`, `domain-disposition`,
  `domain-publish`, `publish`, `contribution`.
- **Decisions & Issues:** `bridge-raise`, `bridge-respond`, `bridge-refresh`,
  `bridge-propose`, `bridge-link-review`, `bridge-close`, `proposal`, `review`,
  `decision`, `decision-rights-save`, `decision-rights-action`,
  `decision-integrity-*`, `project-timeline`.
- **Domain knowledge and meaning:** `domain-knowledge-save`,
  `domain-interpretation-assess`, `domain-interpretation-bridge`,
  `meaning-propose`, `meaning-decide`, `meaning-close`, `enterprise-adopt`,
  `enterprise-adoption-drop`. Enterprise actions go to `/api/enterprise`.
- **Delivery:** `developer-brief-*`, `delivery-prepare`, `delivery-export`,
  `demo-delivery-prepare`, `demo-delivery-commit`.
- **Configuration and AI quality:** `domain-add`, `domain-update`,
  `domain-configure`, `coach-settings-*`, `agent-descriptor-save`,
  `agent-method-save`, `agent-quality-run`, `agent-quality-review`,
  `integration-settings-save`, `setup`, `setup-governance-enable`.

### Proposed service interfaces (To build)

Illustrative names, not current routes.

| Endpoint | Authority | Version condition | Result |
| --- | --- | --- | --- |
| `POST /v1/sources/register` | Importer with upstream read and project ingest rights | Create-only or expected source revision; upstream version or hash pinned | Source ref, access provenance, extraction status; does not endorse content |
| `POST /v1/blocks/propose` | Domain author or bounded preparation agent | Expected block revision; exact source spans | Private block with typed assertions and links; no publication |
| `POST /v1/packets/assemble` | Assembler acting for the requester and audience | Exact selected and configuration revisions; retrieval policy | Immutable manifest, inclusions, omissions, conflicts, coverage |
| `POST /v1/assessments/record` | Assessor allowed for the intended use | Frozen inventory, evidence set and standard versions; expected revision | One judgment per condition, next action, readiness recommendation |
| `POST /v1/publications/commit` | Authorized publisher, confirming selection and audience | Expected draft and prepared-release basis | Published revision and release receipt |
| `POST /v1/decisions/record` | Decision owner for this scope | Expected case version; exact proposal and review basis | Decision, successor versions and change event in one transaction |
| `POST /v1/lessons/propose` | Practitioner or learning agent | Exact outcome or issue references | Draft lesson for steward review |
| `POST /v1/delivery/execute` | Connector identity within an approved scope | Payload hash, approval reference, destination version | Queued attempt, then confirmed receipt or explicit unknown |
| `POST /v1/reassessments/request` | Owner or change worker | Changed references and dependency trace | Bounded review task with recorded frontier |
| `GET /v1/return-digest` | The person themselves | Since timestamp | What waits, what changed in their basis, what others published |

### Errors and retries

401 for absent authentication; 403 for a denied action; the same not-found
response for absent and inaccessible records; 409 for a stale revision, changed
basis or conflicting idempotency payload; 422 for an invalid contract; 429 for
quota; 503 with a stable reason for an unavailable model or dependency. 202 means
accepted, never completed. A failed command leaves no partial change. An identical
retry returns the original receipt.

### Handler order

1. Resolve the principal and memberships from the trusted session.
2. Validate the schema; bind project, operation and policy.
3. Check access to the target; look up the idempotency key; return the original
   receipt or reject a conflicting payload. A retry never bypasses revoked
   access.
4. In one transaction: verify authority and expected revisions, apply the
   transition, append the receipt, write the outbox event.
5. For remote effects, a fenced worker rechecks the payload and authority before
   sending, then records the result or the uncertainty.
6. Return a safe outcome; keep failures; reconcile unknown cost or write
   outcomes before any retry.

---

## Appendix C Quickstart and code map

### Run and test

Python 3.12 or newer; Node for UI tests.

```sh
python3 run_demo.py                                   # serve the demo on port 8770
python3 run_demo.py --port 8771 --reload              # serve and reload on code changes
python3 run_demo.py --check                           # full workflow in disposable data
PYTHONPATH=src python3 -m unittest discover -s tests  # Python suite (over 1,100 tests)
node --test tests/*.cjs                               # UI suite (over 800 tests)
```

All three checks must pass on every change. Then walk the core loop in the
browser at desktop, tablet and phone widths, light and dark: sponsor intent,
domain work, preflight and publication, shared review, an authorized decision,
the revised intent. No model credentials are needed; with none connected, the AI
partner says it is unavailable.

### Code map

| Area | Files |
| --- | --- |
| Record store, packets, dependency graph, impact | `core.py` |
| Command surface and project state | `workspace.py` (`Workspace.command`) |
| HTTP, accounts, sessions | `web.py`, `access.py`, `settings.py` |
| Business Intent | `intake.py`, `intake_coach.py`, `sponsor.py`, `goals.py`, `scaffold.py`, `scaffold_tailoring.py`, `refinements.py`, `business_assessments.py` |
| Requirements and confidence | `requirement_assistant.py`, `requirement_assessments.py`, `requirement_evidence.py`, `resolution.py`, `readiness.py` |
| Workbenches | `domain.py`, `domain_chat.py`, `domain_brief.py`, `working_report.py`, `domain_submission.py`, `knowledge_cards.py`, `need_contexts.py`, `design_visual.py`, `prototype_workflow.py`, `flow_export.py`, `tool_imports.py` |
| Domain knowledge and meaning | `domain_knowledge.py`, `domain_interpretation.py`, `meaning.py`, `enterprise.py`, `adoption.py` |
| Publication and packets | `domain.py` (`prepare`, `publish`), `packet_preparation.py` |
| Decisions & Issues | `bridge.py`, `decisions.py`, `decision_rights.py`, `decision_review.py`, `decision_receipts.py`, `project_timeline.py`, `team_timeline.py` |
| Delivery | `delivery.py`, `developer_brief.py`, `receipt_delivery.py`, `demo_delivery.py` |
| AI boundary and agents | `model_provider.py`, `model_connection.py`, `agent_catalog.py`, `agent_runs.py`, `agent_quality.py`, `quiet_suggestions.py` |
| Integrity review | `integrity*.py` |
| Configuration | `config/*.json` (domains, intake profile, field guidance, methods, cases, evidence reasoning, assessment profiles, bridges, agent personas) |
| UI | `static/*.js`, `static/theme.css` (tokens; loaded last), `static/index.html` |

### The store contract in brief

```python
ref = store.put(id, kind, scope, body, expected_revision=0)  # append; StaleBasis if not current
rec = store.read(Ref(id, revision), allowed_scopes)          # exact, scope-checked
rec = store.latest(id, allowed_scopes)
store.depend(dependent_ref, basis_ref, allowed_scopes)
g   = store.graph(allowed_scopes)                            # NetworkX projection
with store.transaction(): ...
```

Append-only; kind and scope fixed at creation; absent and inaccessible records
raise the same error; packets cannot widen access.

### Scopes

| Scope | Holds |
| --- | --- |
| `project:demo` | Shared records: contributions, requirements, decisions, issues |
| `intake:sponsor` | The sponsor's private Business Intent drafts |
| `domain:research`, `domain:design` | Each domain's private workbench records |

A person's scopes come from their role and domain membership on the server,
never from the client.

---

## Appendix D Glossary

| Term | Meaning |
| --- | --- |
| Adaptive intent | Business intent whose purpose endures while its understanding is revised through decisions, with earlier versions kept |
| Asynchronous work | People contribute on their own schedules; the system carries context between them |
| Complete solution | A handoff package: validated problem and solution, ratified requirements, confidence picture, open issues, readiness call, exact basis |
| Knowledge brain | The knowledge system's five jobs beyond storage: remember with meaning, attend, learn, coach, standardize (and forget responsibly) |
| Workbench | A person's or team's private place to prepare work and reconcile it against project and enterprise context |
| Shared space | Requirements and Decisions & Issues, where alignment is honed and decisions are made |
| Publication | The explicit, previewed, owner-confirmed release of selected work |
| Preflight | Pinning the exact draft and its basis into a prepared packet before publication |
| Building block | A typed unit of knowledge produced in a workbench; shown as a card |
| Component | One of the fixed parts every block is made of: Actor, Situation, Claim, Basis, Strength, Time, Rationale, Alternatives, Criterion, Measure, Owner, Status (D014) |
| Dependency signature | A group's relations, pinned revision, conditions and use around one shared block; compared across groups to find agreement, complement or conflict (D014) |
| Family | Evidence, Direction, Open or Outputs: the four groups of block types |
| Need context | A situated claim about people, job, situation, triggers, pains, gains, boundaries and dependencies |
| Context area | A common meaningful dimension of context (user groups, user flows, ownership...) shared by requirement subcategories, building block types and packet sections |
| Distillation | The reviewed path from raw human material to building blocks, contributions, ratified requirements, lessons and standards |
| Corpus | Meaningful text fields split into passages for retrieval, each tied to its exact record |
| Property graph | Record revisions as nodes and exact typed references as edges, with state signals as properties |
| Context packet | The exact basis selected for a named task and audience |
| Recipe | The versioned plan used to assemble a packet |
| Domain knowledge | A domain's versioned terms, categories, relationships, standards and practices |
| Meaning boundary | What a term includes, excludes and should not be confused with |
| Reach | How far a meaning applies: project, domain, named domains, enterprise |
| Lesson | Scoped learning for another project, with conditions, counterexamples and limits |
| Confidence rating | An owner's recorded judgment for a named use |
| Evidence coverage | A counted measure of shared work on the current version; coverage, not quality (formerly Evidence level) |
| Contributions from | Which teams have published on the current version; publication is not validation (formerly Validated by) |
| Readiness call | A recorded decision that the project may proceed, for what use, under what conditions |
| Review frontier | Connected work not yet examined when a traversal stopped |
| Outbox | Events written in the same transaction as the change they describe |
| Idempotency | Retrying an operation preserves one intended business effect |
| Stale | A record, review or packet whose basis has a newer version |

---

## Appendix E Sources and evidence boundaries

Use these to tell product intent, implemented behaviour, proposed architecture
and open decisions apart. File presence alone is not evidence that a feature runs.

- **Code baseline:** this repository. Implementation claims come from the named
  modules and their tests.
- **Architecture overview:** [architecture.md](architecture.md).
- **Decision records:** [D001](decisions/D001-general-audience-adaptive-cointelligence.md)
  general audience;
  [D002](decisions/D002-research-figjam-flows-and-native-figma.md) FigJam flows
  and Figma;
  [D003](decisions/D003-suggestions-require-validation.md) suggestions require
  validation;
  [D004](decisions/D004-requirement-evidence-level.md) evidence coverage;
  [D005](decisions/D005-knowledge-edited-by-team-lead.md) knowledge edited by the
  team lead;
  [D006](decisions/D006-accepted-intent-changes-update-mirrors.md) accepted
  intent changes update mirrors;
  [D007](decisions/D007-c2-tracker-design-system.md) design system;
  [D008](decisions/D008-readiness-decision-record.md) readiness record;
  [D009](decisions/D009-meaning-governance.md) meaning governance;
  [D010](decisions/D010-workbench-cockpit.md) workbench cockpit;
  [D011](decisions/D011-quiet-ai-suggestions.md) quiet suggestions;
  [D012](decisions/D012-confidence-signals.md) confidence signals;
  [D013](decisions/D013-knowledge-block-families.md) block families;
  [D014](decisions/D014-chained-packets-and-dependency-difference.md) one knowledge
  system (components, chained packets, dependency difference, confidence).
- **Wave test:** [evaluations/wave-test.md](evaluations/wave-test.md).
- **Demo walkthrough:** [demo.md](demo.md). All demo content is synthetic.
- **Decision and action log:** [log.md](log.md).
- **Not established by this manual:** a production installation, enterprise
  identity, live model quality, connector coverage beyond the three read-only
  tool imports, real work-tracker writes, or measured team benefit.
