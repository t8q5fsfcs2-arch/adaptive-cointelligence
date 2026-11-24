# D007: The C2 tracker design system across the whole experience

Status: accepted by the user, 23 November 2026. Built on branch `claude/thesis-board`.

## Why

The experience needs a visual identity distinct from an earlier related product, and a layout that shows everyone the same running case at a glance. The
user chose direction C2 (horizontal trackers, short labels, strong signs and
wayfinding) from the design canvas, with light and dark modes and a fluorescent
light palette.

## Strategy

1. **One running case.** "The case" is the shared front page: the promise, its proof,
   case strength, the problem side (Research) and the solution side (Design), and
   milestones. Each requirement area is a horizontal tracker row that opens in
   full detail.
2. **Brevity.** Labels, not sentences. A key explains the signs once. Data the
   teams wrote, such as validation questions and the promise, is shown in full.
3. **Readable signs.** A level is always shown three ways: segment fill, a circle
   glyph (empty, quarter, half, full) and the word. Colour is never the only signal.
4. **Wayfinding.** Numbered sections (01 Mission to 06 Milestones), a section strip
   with counts, the current page marked in the navigation, and an arrow on
   everything that opens detail.
5. **Honest play.** Milestones and "next" hints are calculated from existing
   records. No invented points, streaks or leaderboards. Disproving counts like
   proving.

## Visual system

- **Type:** Space Grotesk (600) for headings, numbers and section labels; Inter for
  body text. Section labels are small capitals with wide letter spacing.
- **Tokens:** every colour comes from semantic `--ac-*` tokens in `theme.css`.
  Stylesheets carry no hard-coded colours.
- **Light (fluorescent):** off-white ground #F4F4EF, ink #111318, neon lime #D4FF3A
  fill with dark text, fluorescent pink #FF3D8B for low and attention, neon teal
  #00BFA5 for high, gold #FFC21A for milestones. Text versions are darkened for
  contrast (lime text #3B6300, pink #C2185B, teal #00756A).
- **Dark:** navy ground #0E1330, surfaces #161D45, lime #C8F25C, coral #FF9E7A,
  mint #7CF0B4, gold #F4C34D.
- **Shape:** 8px controls and rows, 14px panels, pill chips.
- **Mode:** a light and dark toggle in the top bar, stored only as a local browser
  preference. It follows the system setting until the person chooses.

## What it does not change

Presentation only. No record types, versions, permissions, publication, decision
rights or approval guards change. The grouping of requirement areas into the problem
and solution sides is a display mapping. Recording a readiness decision would need
a new record type; the readiness view shows the checks only until the user approves
that separately.
