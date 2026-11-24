"""Source-linked persona inventory. Entries do not create executable agents."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

_RAW = (Path(__file__).parent / 'config' / 'agent_personas.json').read_bytes()
_CATALOG = json.loads(_RAW)
CATALOG_VERSION = _CATALOG['version']
CATALOG_FINGERPRINT = hashlib.sha256(_RAW).hexdigest()
INTAKE_AGENT_ID = 'business-intent-coach'
INTAKE_PERSONA_ID = 'P02'
PERSONA_IDS = frozenset(p['id'] for p in _CATALOG['profiles'])

# Capability claims are code-owned, never editable through descriptive metadata.
_COVERAGE = {
    'P01': 'Workflow routing is handled by application code. No Supervisor reasoning role is connected.',
    'P02': 'One intake AI partner uses seven skills and question-specific expertise. An explicit Business Intent assessment freezes material claims before a separate model judgment applies the shared evidence and reasoning standard. Completeness and confidence remain distinct and provisional. AI partner guidance, editable suggestions and source-grounded document reconsideration work; the full Lucid role, including retrieval of domain guidance, is not yet complete.',
    'P03': 'Selected sources and context questions support intake. No separate Context assistant or domain-source retrieval workflow is connected.',
    'P04': 'A separate Requirement Assistant drafts a candidate requirement and acceptance criteria for a selected drawer, and reviews existing wording. It also proposes project-specific scaffold questions and checks, linked to saved intake and recorded requirements. It prepares editable goals and success measures with proposed links to scaffold areas from the saved intake. It also teaches and reviews individual goal, measure and requirement fields from an explicitly submitted working copy, without saving or approving it. It suggests specific intake connections for goal and measure drafts, with reasons and exact saved answers for human review. These proposals and links require human review. The configured taxonomy is retained; domain retrieval is not implemented.',
    'P05': 'File text extraction runs as ordinary code. The finding/process extraction persona is not connected.',
    'P06': 'The shared domain-coach runtime reviews saved Research deliverables against configured evidence standards, selected source text and linked requirements/goals. Authors ask follow-up questions, preview suggested edits and retain decisions while working. Preflight separately packages an exact version for sharing. Automatic research synthesis and cross-domain reconciliation are not implemented.',
    'P07': 'Configured domains reuse the shared domain-coach runtime for private conversations, incoming-packet interpretation and deliverable review. Versioned active glossary, taxonomy, concept relationships, standards and methods guide the bounded operation. Sources are not automatically retrieved, and expert quality and compliance remain for human evaluation. This is one configured runtime pattern, not a separately deployed agent per domain.',
    'P08': 'No Mapping assistant is connected to compare domain meanings.',
    'P09': 'Review and reconciliation records exist. No Reconciliation assistant is connected to compare positions.',
    'P10': 'The impact worker follows recorded dependencies using ordinary code. No model-based Impact assistant is connected.',
    'P11': 'No Options assistant is connected to prepare an options comparison.',
    'P12': 'The shared domain-coach runtime reviews Design evaluations using the Design configuration. A bounded design-visual-coach operation reviews selected actual PDF page images against published intent, selected Research, linked requirements, acceptance criteria and goals/measures. It returns page/area feedback with exact context citations and saves execution receipts; an adapter with image-review support is required. Feedback is advisory, not acceptance or compliance certification. Broader artifact-fit automation is not implemented.',
    'P13': 'Recorded changes and dependency checks support reconsideration. No Change analyst reasoning role or external-source monitor is connected.',
    'P14': 'Human review gates and decision records are handled by application code. No Ratification coordinator reasoning role is connected.',
}


def catalog(model=None):
    from .agent_runs import execution_mode
    mode = execution_mode(model) if model else "not-connected"
    data = deepcopy(_CATALOG)
    data['fingerprint'] = CATALOG_FINGERPRINT
    for p in data['profiles']:
        wired = p['id'] in {'P02', 'P04', 'P06', 'P07', 'P12'}
        supporting = p['id'] in {'P01','P03','P04','P05','P09','P10','P13','P14'}
        active_mode = mode if wired else 'not-implemented'
        p['implementation'] = {
            'status': 'partial' if wired else 'specified',
            'mode': active_mode,
            'label': {'live':'Live', 'simulated':'Simulated', 'not-connected':'Not connected', 'not-implemented':'Not implemented'}[active_mode],
            'summary': _COVERAGE[p['id']],
            'runtime_id': INTAKE_AGENT_ID if p['id']=='P02' else 'requirement-assistant' if p['id']=='P04' else 'domain-coach' if p['id'] in {'P06','P07','P12'} else None,
            'version': '19' if p['id']=='P02' else '11' if p['id']=='P04' else '5' if p['id'] in {'P06','P07','P12'} else None,
            'supporting_service': supporting,
        }
    return data
