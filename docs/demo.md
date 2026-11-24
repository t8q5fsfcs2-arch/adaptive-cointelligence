# Demo: Riverbend Health AI appointment assistant

A synthetic project that shows adaptive intent through multiple people's
consequential work. Every person, observation, source, dialogue and decision is
authored for the demo. No interviews, prototype sessions, Figma retrievals or AI
assessments took place.

## The story

1. **Intent.** Dana Okafor (business sponsor, Director of Patient Access) wants to
   cut missed appointments from 18% to 10%. She proposes an AI assistant that sends
   reminders and asks patients to confirm.
2. **Research.** Jordan Reyes (Research) maps the current rescheduling journey as a
   FigJam user flow and interviews patients and front-desk staff. Finding: most
   people who miss appointments already knew they could not come, but rescheduling
   needs a phone call during office hours. Forgetting is a smaller share.
3. **Intent adapts.** Jordan asks Dana to revise the problem statement, citing the
   published finding. Dana adopts it, re-confirms her goals, adds a refill-rate
   measure and republishes. Business intent moves to version 2; version 1 is kept.
4. **Design.** Mei Chen (Design) generates three assistant concepts into Figma
   (reminder bot, conversational rescheduling agent, self-serve page with AI
   waitlist) and evaluates them. She raises a dependency: some visit types need
   staff.
5. **Decisions & Issues.** Mei asks Research for the visit-type rules; Jordan
   answers. Mei publishes a revised concept with a staff handoff.
6. **Decision.** Sofia Alvarez (requirement owner) proposes requirement version 2.
   Research and Design review it, Dana comments, and Sofia approves it.

## People

| Persona | Role |
| --- | --- |
| Dana Okafor | Business sponsor |
| Jordan Reyes | Research |
| Mei Chen | Design |
| Sofia Alvarez | Requirement owner |
| Tom Becker | Operations reviewer (legacy role, kept for compatibility) |
| Administrator | Access and settings; no workflow decisions |

Switch between them with the preview-user menu in the header.

## Things to try

- As Dana, open Business Intent and compare intent version 1 and version 2.
- As Jordan, open the Research workbench and the scripted journey conversation.
- As Mei, open the Design workbench, the prototype alternatives and the developer
  brief.
- Open Decisions & Issues to follow the dependency issue to its decision.
- As Administrator, connect a model and your Figma account in Settings to try live
  AI, FigJam and Figma steps with your own credentials.

## Run

```sh
python3 run_demo.py          # serve the demo (creates .demo/ on first run)
python3 run_demo.py --check  # verify the full workflow in disposable data
python3 run_demo.py --reload # serve and restart automatically when code changes; data is kept
```
