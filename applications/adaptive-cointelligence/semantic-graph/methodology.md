# Adaptive Cointelligence methodology

## Why the method exists

**ACI-M01 | Preserve the reasons behind intent.** At handoffs, the latest brief can survive while assumptions, conflicting evidence and reasons disappear. Preserve the chain from intent and success measures through evidence, proposals and decisions to the resulting work. Evidence may change the solution, the problem framing, or the original business thesis. Measure reconstructability, better cross-domain decisions, and delivery impact separately; the prototype does not establish those outcomes. Source: [Architecture proposition](../../../docs/architecture.md#proposition), [enterprise value](../../../docs/developer-guide.md#value-to-the-enterprise).

## Publication and authority

**ACI-M02 | Explicit release is the boundary.** People may do consequential work in existing tools or a private workbench. Preview the exact draft, supporting source material, scope and limits before publication. A release makes selected material available to its authorized audience. It neither publishes the rest of the workbench nor approves intent. Source: [publication boundary](../../../docs/developer-guide.md#the-boundary-publication).

**ACI-M03 | Validate suggestions separately from deciding shared meaning.** AI proposals stay attributable and editable; explicit human validation creates a new version of the person's work, without silently overwriting it. A consequential change to shared meaning needs a separate authorized disposition against its exact evidence and current decision policy. Changing an assignee does not itself grant source access. Source: [D003](../../../docs/decisions/D003-suggestions-require-validation.md), [engineering rules](../../../docs/developer-guide.md#6-rules-you-must-not-break).

## Evidence and change

**ACI-M04 | Preserve the difference between observation and claim.** Attach the exact source passage, applicable people or population, situation, time, method and limits where supplied. Distinguish a different view of the same fact, a different applicable context and a genuine knowledge change. New evidence can be important without being linked to a requirement. Similarity, a mention or packet membership does not establish corroboration, dependency or approval. Source: [three kinds of change](../../../docs/developer-guide.md#three-kinds-of-change-three-different-responses), [D013](../../../docs/decisions/D013-knowledge-block-families.md).

**ACI-M05 | Propagate changes through recorded dependencies.** A decision records its disposition, authority, rationale, alternatives where relevant, exact basis and any successor version it authorizes. Keep the predecessor and pinned packet intact; flag only work that relied on a changed basis. Owners reconsider their work; a new fact does not cascade into silent edits. Source: [change propagation](../../../docs/developer-guide.md#how-change-travels), [D006](../../../docs/decisions/D006-accepted-intent-changes-update-mirrors.md) for the specific prototype mirror behavior.

**ACI-M06 | Keep evidence and readiness separate.** Recorded confidence is a person's judgment for a use; computed evidence level describes shared evidence; contributor coverage shows whose work concerns the current version. An authorized readiness call records its basis, outcome and conditions. New shared evidence can change the computed coverage and prompt reassessment; it does not itself change the recorded confidence or readiness decision. None of these signals substitutes for the others. Low confidence need not stop a person from proceeding. D004's numerical thresholds are a prototype choice, not a default Anchor policy. Source: [D004](../../../docs/decisions/D004-requirement-evidence-level.md), [D008](../../../docs/decisions/D008-readiness-decision-record.md), [D012](../../../docs/decisions/D012-confidence-signals.md).

## Meaning and reusable learning

**ACI-M07 | Reuse meaning by context and explicit adoption.** A concept can have different valid meanings in different domains. Keep inclusions, exclusions, reach and typed mappings explicit; widening reach needs a decision, and a new shared concept version does not replace a project's adopted version. A reusable lesson needs its conditions and limits; copying an interpretation does not make it a second independent source. D009's prototype roles are examples of separation of duties, not universal job titles. Automated cross-project learning and supplying adopted concepts to another team's AI partner are not established capabilities. Source: [D009](../../../docs/decisions/D009-meaning-governance.md), [D013](../../../docs/decisions/D013-knowledge-block-families.md), [learning service status](../../../docs/developer-guide.md#learning-service-to-build).

### Relation candidates for review

These are graph modeling candidates, not existing registered edges. Bind both endpoints to approved identities and exact versions before admission.

| Example relation | Required distinction |
| --- | --- |
| Claim `cites` source span; contribution `challenges` intent revision | A citation gives provenance; a challenge supplies a reason to reconsider. Neither ratifies a change. |
| Decision `based_on` proposal/evidence/policy revisions; new intent `supersedes` old intent | Keep old authority and evidence reproducible to the current authorized reader. |
| Packet `includes` a claim; affected artifact `depends_on` a revision | Evaluate impact from real dependencies, not every reference in a packet. |
| Project `adopts` concept revision; concept `distinct_from` another concept | Preserve scope and approved mapping; avoid implicit synonym replacement. |
