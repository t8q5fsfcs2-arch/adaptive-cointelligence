# D001: General-audience Adaptive Cointelligence

Status: accepted by the user, 21 November 2026.

## Context

The `claude/northstar` branch starts from `codex/northstar-compact-requirement-tiles`
(commit cf6f4da). That version was branded for a specific client, used that
client's design language and shipped a different fictional demonstration.

## Decision

Adapt the product for a general audience under the name **Adaptive
Cointelligence**:

1. Remove client branding: logo, client names and the client design language.
   Replace it with a new design system in a crisp workspace direction.
2. Replace the earlier demonstration and its fixtures with a new synthetic
   business case: outpatient clinic appointment access, with synthetic research
   and design content.
3. Review product language for clarity, through a glossary the user approves.
4. Restructure the interface around the core loop of intent, investigation,
   alignment and delivery.
5. Use Claude for development on this branch: `CLAUDE.md` replaces `AGENTS.md`,
   work happens on `claude/` branches, and commits stay local until the user
   asks to push.
6. Keep earlier documentation as a private archive and write fresh
   documentation going forward.

## Constraint

Presentation changes preserve backend behavior: records, versions, privacy,
publication, decision rights and approval guards. Each step keeps the full test
suite and the launcher check passing, and the core loop is walked in the browser
before a phase is reported complete.

## Sequence

Housekeeping, then the new case, then language, then structure, then the design
system. Structure precedes visual restyling so screens are not restyled and then
moved.

## Follow-up

The Figma renderer's client component library was removed by
[D002](D002-research-figjam-flows-and-native-figma.md).
