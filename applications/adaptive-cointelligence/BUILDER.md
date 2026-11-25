# Adaptive Cointelligence | Prepare corpus for Builder

## Invariants

Use the native ADK Builder and existing Source Adapter contracts selected by the application. This is an authored entry point, not a package manifest, an ADK command wrapper, or a second indexing pipeline. No package, composition, registry, deployment, or native Corpus selection is declared yet. Do not synthesize package paths, Collection IDs, grants or physical index names.

The application owns its authored corpus and its logical selections. Ferb owns admitted Collection membership, permissions, index bindings and source readback. An app-specific Corpus may be selected without making application ID a physical storage namespace. A Group may supply shared selections; the application can select its own under the native contract. Neither selection grants access. Check the actual owner scope and current source membership before treating any result as available.

## Index

| WHEN | READ |
| --- | --- |
| Starting the first preparation or changing source selection | [Preparation order](#preparation-order) |
| Classifying methodology rules, prototype choices, research or reference UI | [Source roles](semantic-graph/index.md#source-roles) |
| Checking that retrieval returns correct meaning rather than a plausible nearest match | [Representative retrieval questions](#representative-retrieval-questions) |
| Confirming behavior or distinguishing graph plans from working contracts | [Human intent](application-intent/index.md) and [Product graph](product-graph/index.md) |

## Preparation order

1. Select the app root and walk the semantic and product source roots separately. Preserve the exact source revision, heading, content, applicability and authoring status. Keep useful research provenance linked, but out of the normative kernel unless the application owner approves it. Do not bulk-ingest the demo, decision log, license tree, implementation instructions, or runtime state.
2. Confirm human Gherkin+ separately, against the smallest proposed journey. Record unresolved behavior with its decision owner. App methodology can inform the proposal; it cannot confirm the human intent.
3. Once a real application package exists, use its generated index and one composition entry to select the app-owned sources and matching known ADK corpora. Locate an existing authorized native Corpus binding before proposing creation. Use owner tooling to derive the needed document closure and check stable IDs, links, scope, source bytes and variant boundaries. Do not hand-write the generated package paths or copy shared contract corpora.
4. With authorized native admission, verify source/version readback and representative retrieval through the selected Collection and indexes. Check exact citations and dependency closure; verify a denied or unselected source stays out. Document missing, unsupported or stale evidence instead of reporting it as indexed.
5. Only when the real app inputs and current native evidence are ready, run Resolve → Annotate → Materialize → Skeptic through the installed Builder. Review accepted phase outputs and validate the graph and app behavior separately. Do not edit generated outputs to settle a product decision.

## Representative retrieval questions

| Question | Expected selected meaning |
| --- | --- |
| A published finding conflicts with the current framing. Did the framing change? | Publication and decision are separate; the exact framing revision and the authorized disposition determine what changed. |
| Two claims sound contradictory but describe different populations. Which wins? | Preserve both qualifications; raise a genuine conflict only after checking what each claim applies to. |
| A requirement revision changed. Which packet needs review? | Follow recorded dependencies to exact old revisions; packet inclusion alone proves no dependency. |
| Can a highly evidenced finding or a readiness call authorize release? | Evidence coverage, recorded confidence, publication authority and readiness are different. Check current governing policy. |
| A selected shared corpus contains a newer concept, or a source grant was revoked. What should Builder use? | Honor the adopted exact version and current authorized membership. Report the missing access or changed basis, never swap in evidence silently. |

## Return

Return selected corpus roots, exact source and native binding evidence, supported query results, and READY or the smallest owner-bound blockers. At this checkpoint: **source home is ready to review; native Builder preparation is blocked on confirmed intent, package/composition, scope selection and native readback.**
