# D002: Research user flows in FigJam and native Figma prototypes

Status: accepted by the user, 21 November 2026.

## Context

The demonstration case must lead to a software and AI solution, so that Design
evaluates and creates prototypes in Figma and Research maps user flows in FigJam,
pushing and pulling through MCP connections configured per user in Settings.

Before this decision, Design could create prototypes in Figma (archived ADR 0035)
and any domain could import a FigJam, Figma or Lucid selection (archived ADR 0034).
Research could not create anything in FigJam, and Design's prototype renderer
depended on a client's Figma component library.

## Decision

1. **Research user flows.** A domain whose profile sets `flow_export` (Research
   by default) can author private, versioned user-flow schematics in Mermaid
   syntax (flowchart, sequence or state diagrams).
2. **Push to FigJam.** The author stages an exact flow version and an optional
   destination board, then sends it only after explicit confirmation. Sending
   requires the author's own FigJam connection with creation allowed in
   Settings → Integrations, and an MCP server exposing `generate_diagram`. Only
   the flow name and text are sent. Arguments are mapped from the tool's own
   input schema; if required inputs cannot be supplied, nothing is sent.
3. **Receipts.** The attempt is recorded before the external call. A confirmed
   result stores the board location and a receipt digest. An uncertain result is
   kept as "outcome unknown" and never retried automatically. A changed flow
   cannot send a stale staged copy.
4. **Pull back.** A confirmed board opens the existing FigJam import, pre-filled,
   so the refined flow returns as a private source with its tool provenance.
5. **Native Figma prototypes.** Design's renderer builds screens from native
   Figma frames, auto layout and text instead of a client component library, so
   it works in any Figma file. The client library configuration is removed.

## Preserved

Private work stays private until explicitly published. No model call, approval or
publication is implied by pushing or pulling. Design's existing prototype flow,
staging, confirmation and receipts are unchanged apart from the renderer output.

## Limits

Live push and pull require an authorized Figma MCP connection; the offline demo
seeds a labelled synthetic flow and does not contact Figma. Adding `flow_export`
to the Research profile changes that profile's fingerprint, so Research work in
databases created before this change may ask for a refresh.
