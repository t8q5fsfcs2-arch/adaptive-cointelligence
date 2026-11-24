"""A fictional, explicitly unratified walkthrough; each run gets its own database."""
import json
from pathlib import Path
from uuid import uuid4

from .core import ImpactWorker, Store


def main() -> None:
    folder = Path("data")
    folder.mkdir(exist_ok=True)
    path = folder / f"demo-{uuid4().hex[:12]}.sqlite3"
    store = Store(path)
    shared = {"project:demo"}
    try:
        intent = store.put("INT-001", "intent", "project:demo",
                           {"text": "Help customers complete enrollment", "status": "draft"})
        evidence = store.put("EVD-001", "evidence", "project:demo",
                             {"text": "Synthetic sample: customers with unusual documents need help"})
        research = store.put("CON-RES-001", "contribution", "project:demo",
                             {"domain": "Research", "text": "Propose an assisted enrollment route",
                              "status": "published-for-review"})
        operations = store.put("CON-OPS-001", "contribution", "project:demo",
                               {"domain": "Operations", "text": "Assistance has staffing and hours constraints",
                                "status": "published-for-review"})
        requirement = store.put("REQ-001", "requirement", "project:demo",
                                {"text": "Define the assisted route and operating limits", "status": "proposed"})
        for dependent, basis in [(research, evidence), (requirement, research),
                                 (requirement, operations), (requirement, intent)]:
            store.depend(dependent, basis, shared)
        packet = store.packet("PKT-BRIDGE-001", 1, "Review the assisted enrollment proposal",
                              [intent, evidence, research, operations, requirement], shared, shared)
        print("1. CREATED: intent, evidence, two domain contributions and a proposed requirement.")
        print("2. ASSEMBLED: exact-version packet for shared review; no decision is implied.")
        print(json.dumps(packet, indent=2))
        revised = store.put("EVD-001", "evidence", "project:demo",
                            {"text": "Synthetic follow-up: some customers need assistance outside staffed hours"},
                            expected_revision=1)
        result = ImpactWorker().run(store, evidence, revised, shared)
        change = store.put("CHG-001", "change-case", "project:demo", result)
        print("3. CHANGED: EVD-001:v2 saved. The worker follows known dependencies.")
        print(json.dumps(result, indent=2))
        print(f"4. RECORDED: {change.label()} awaits human review. Nothing was automatically approved.")
        assert store.read_packet("PKT-BRIDGE-001", 1, shared) == packet
        print("5. PRESERVED: PKT-BRIDGE-001:v1 still references EVD-001:v1.")
        print(f"Database: {path.resolve()}")
        print("Next increment: human resolution, decision history and next packet revision.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
