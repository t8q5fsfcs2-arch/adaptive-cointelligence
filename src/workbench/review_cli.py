"""One-step local human review walkthrough. Identity selection is simulation only."""
import argparse
from pathlib import Path
import sqlite3
from uuid import uuid4

from .core import Ref, Store
from .decisions import ACTORS, DecisionLoop
from .scenario import initialize, latest_case, add_follow_up


def explain(loop, case):
    body = case["body"]
    current = loop.store.read(Ref(**body["target"]), loop.scopes)
    print(f"\nSHARED REVIEW | {case['ref'].label()} | {body['status'].upper()}")
    print(f"Current wording ({current['body'].get('status')}): {current['body']['text']}")
    print(f"Proposed wording: {body['proposal']['text']}")
    print(f"Acceptance criteria: {body['proposal']['acceptance_criteria']}")
    print(f"Conditions: {body['proposal']['conditions']}")
    for raw in body["basis"]:
        record = loop.store.read(Ref(**raw), loop.scopes)
        if record["kind"] in {"evidence", "contribution"}:
            print(f"  {record['ref'].label()}: {record['body'].get('text', '')}")
            if record["body"].get("limitation"):
                print(f"    Limit: {record['body']['limitation']}")
    for actor in ("sam", "maya"):
        raw = body["reviews"].get(actor)
        review = loop.store.read(Ref(**raw), loop.scopes)["body"] if raw else None
        print(f"{ACTORS[actor]['name']}'s review: " + (review["disposition"] if review else "NOT RECORDED"))
    if body["status"] == "deferred":
        print(f"Next owner: {body['next_owner']} | Next question: {body['next_question']}")
    governing = loop.store.latest("REQ-001", loop.scopes)
    print(f"Current requirement record: {governing['ref'].label()} / {governing['body']['status']}")
    if body["status"] not in {"approved", "rejected"}:
        print("Next: record Research's evidence review and Operations' response, then Alex's decision.")
    elif body["status"] == "approved":
        print("Next: inspect history, or introduce follow-up evidence to test reconsideration.")
    else:
        print("Proposal rejected. History is retained. Use --new for another walkthrough.")


def record_review(loop, case, actor):
    print(f"\nYou are simulating {ACTORS[actor]['name']} — {ACTORS[actor]['role']}.")
    if actor == "sam":
        print("1. Evidence supports the stated need within its limits\n2. More evidence is needed")
        values = {"1": "supported-with-limits", "2": "needs-more-evidence"}
    else:
        print("1. Proposed wording is acceptable with its stated conditions\n2. Operational concerns remain unresolved")
        values = {"1": "cleared-with-conditions", "2": "not-cleared"}
    answer = input("Choose 1 or 2 (blank cancels): ").strip()
    if answer not in values:
        print("No review saved.")
        return
    rationale = input("Explain the evidence limits or operational conditions: ")
    result = loop.review(actor, case["ref"], values[answer], rationale)
    print(f"Saved review against exact basis. {result.label()} — requirement remains unchanged.")


def record_decision(loop, case):
    print("\nYou are simulating Alex, the configured requirement owner.")
    print("This approves a requirement only. Evidence limits and trial conditions remain.")
    choice = input("Type approve, reject or defer (blank cancels): ").strip().lower()
    if not choice:
        return
    rationale = input("Why this decision? ")
    owner = question = None
    if choice == "defer":
        owner = input("Who responds next? sam / maya / alex: ").strip().lower()
        question = input("What specific question must they answer? ")
    if choice == "approve" and input("Type APPROVE to confirm this exact proposal: ").strip() != "APPROVE":
        print("Cancelled. No decision saved.")
        return
    result = loop.decide("alex", case["ref"], choice, rationale, next_owner=owner, next_question=question)
    print(f"Saved {result['decision']['id']}: {choice.upper()}.")
    if result["requirement"]:
        print(f"New requirement: {Ref(**result['requirement']).label()}")
        print(f"New packet: {result['packet']['id']}:v{result['packet']['revision']}")
        print("Prior packet retained. Fulfillment: NOT EVALUATED. Execution: NOT AUTHORIZED.")
    else:
        print("The requirement and packet were not revised.")


def main():
    parser = argparse.ArgumentParser(description="Local Research/Operations decision walkthrough")
    parser.add_argument("--db", type=Path, help="Database to resume (defaults to data/research-operations.sqlite3)")
    parser.add_argument("--new", action="store_true", help="Create a separate walkthrough without deleting prior work")
    args = parser.parse_args()
    if args.new and args.db:
        parser.error("Choose --new or --db, not both")
    path = args.db or Path("data") / (f"review-{uuid4().hex[:12]}.sqlite3" if args.new else "research-operations.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    store = Store(path)
    loop = DecisionLoop(store)
    try:
        initialize(store)
        print("RESEARCH + OPERATIONS — LOCAL DECISION WALKTHROUGH")
        print("Fictional material. You simulate named roles; no authentication or AI is running.")
        print(f"Saved database: {path.resolve()}")
        print("Each action is saved. q exits; rerun with this database to resume.")
        explain(loop, latest_case(loop))
        while True:
            print("\n1 Read comparison | 2 Research review | 3 Operations response")
            print("4 Requirement decision | 5 Add follow-up evidence | 6 Decision history | q Exit")
            command = input("Choose: ").strip().lower()
            if command in {"q", "quit", "exit"}:
                break
            try:
                case = latest_case(loop)
                if command == "1":
                    explain(loop, case)
                elif command in {"2", "3"}:
                    record_review(loop, case, "sam" if command == "2" else "maya")
                elif command == "4":
                    record_decision(loop, case)
                elif command == "5":
                    case = add_follow_up(loop)
                    print("New evidence opened a fresh review. Earlier approval stays recorded; no automatic rewrite.")
                    explain(loop, case)
                elif command == "6":
                    events = loop.history()
                    if not events:
                        print("No decisions recorded yet.")
                    for event in events:
                        body = event["body"]
                        print(f"{event['ref'].label()} | {body['at']} | {body['actor']['name']} | {body['disposition']}")
                        print(f"  Reason: {body['rationale']}")
                        print(f"  Exact case: {Ref(**body['case']).label()}")
                else:
                    print("Choose a listed action. Nothing changed.")
            except (ValueError, PermissionError, sqlite3.IntegrityError) as error:
                print(f"NOT SAVED: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Completed actions remain saved; incomplete input was not submitted.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
