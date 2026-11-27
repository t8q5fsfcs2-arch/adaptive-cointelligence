# Developer guide (moved)

The developer guide was replaced on 26 November 2026 by the
[developer manual](developer-manual.md). This page keeps the old section links
working. Each heading below is a section of the old guide and says where its
content now lives. Link to the manual directly in new work.

| Old section | Now in the developer manual |
| --- | --- |
| 1. Why this exists | [1 Purpose and design strategy](developer-manual.md#1-purpose-and-design-strategy) |
| Value to the enterprise | [Prove the value](developer-manual.md#prove-the-value) |
| The boundary (publication) | [Two spaces and one boundary](developer-manual.md#two-spaces-and-one-boundary) |
| Three kinds of change, three different responses | Kept below; see also [Shared meaning across domains](developer-manual.md#shared-meaning-across-domains) |
| How change travels | [How change travels](developer-manual.md#how-change-travels) |
| 6. Rules you must not break | [Invariants](architecture.md#invariants) and [Invariants no domain can turn off](developer-manual.md#invariants-no-domain-can-turn-off) |
| 9. What exists and what is missing | Every manual section opens with a status line: [How to use this manual](developer-manual.md#how-to-use-this-manual) |
| Learning service (To build) | [How the enterprise learns](developer-manual.md#how-the-enterprise-learns-partial) and [Learning from outcomes](developer-manual.md#learning-from-outcomes-to-build) |
| Behaviour test pack (acceptance for any rebuild) | [One integrated acceptance pack](developer-manual.md#one-integrated-acceptance-pack) |

## 1. Why this exists

Now [1 Purpose and design strategy](developer-manual.md#1-purpose-and-design-strategy).

### Value to the enterprise

Now [Prove the value](developer-manual.md#prove-the-value).

### The boundary (publication)

Now [Two spaces and one boundary](developer-manual.md#two-spaces-and-one-boundary)
and [Keep private thinking private](developer-manual.md#keep-private-thinking-private).

### Three kinds of change, three different responses

The manual no longer has this table, so it is kept here as it stood in the old guide.

| Kind of change | Example (clinic project) | What the system does |
| --- | --- | --- |
| **Perspective** | The sponsor and the researcher look at the same requirement | Different explanation and emphasis. Facts, rights and versions unchanged. |
| **Applicability** | "Appointment" means a booked slot to Operations and a clinical encounter to Research | Select the valid meaning for this task and record which one was used. Both meanings can stay valid. |
| **Knowledge** | Research finds most missed visits are known in advance, not forgotten | Prepare a proposal against the exact version. Review it. Only an authorized decision creates a successor version. |

A view change never rewrites history. A retrieved claim never becomes accepted
knowledge by being retrieved.

Since D014, services also detect differences between groups' dependencies on the
same identifier (for example, a claim scoped to one population used for another).
See [D014](decisions/D014-chained-packets-and-dependency-difference.md) and
[Shared meaning across domains](developer-manual.md#shared-meaning-across-domains).

### How change travels

Now [How change travels](developer-manual.md#how-change-travels).

## 6. Rules you must not break

Now [Invariants](architecture.md#invariants) and
[Invariants no domain can turn off](developer-manual.md#invariants-no-domain-can-turn-off).

#### Learning service (To build)

Now [How the enterprise learns](developer-manual.md#how-the-enterprise-learns-partial)
and [Learning from outcomes](developer-manual.md#learning-from-outcomes-to-build).

## 9. What exists and what is missing

Every manual section opens with a Built, Partial or To build status line. See
[How to use this manual](developer-manual.md#how-to-use-this-manual).

### Behaviour test pack (acceptance for any rebuild)

Now [One integrated acceptance pack](developer-manual.md#one-integrated-acceptance-pack).
