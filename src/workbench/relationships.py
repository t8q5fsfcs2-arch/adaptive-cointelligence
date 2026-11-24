"""D014 Rule 5: extract typed links from the records that state them.

Registered with the store so links are written in the same transaction as the record.
Covers block links (private and shared) and contribution references to requirements.
Other body fields keep working as before and can be added here later.
"""
from .core import register_relation_extractor
from .knowledge_cards import LEGACY_TYPES
from .knowledge_components import link_use


def extract(kind: str, body: dict) -> list[dict]:
    if kind == 'domain-implication':
        card = body.get('card') or {}
        block_type = card.get('type') or LEGACY_TYPES.get((body.get('payload') or {}).get('kind'), 'note')
        links = card.get('relations') or []
    elif kind == 'knowledge-card':
        block_type = body.get('type', 'note')
        links = body.get('relations') or []
    elif kind == 'contribution':
        return [dict(to_id=r['id'], to_revision=r.get('revision'), relation='references', use='contribution',
                     conditions='', rationale='Published work that references this requirement')
                for r in body.get('requirement_refs') or [] if isinstance(r, dict) and isinstance(r.get('id'), str)]
    else:
        return []
    out = []
    for link in links:
        ref = link.get('ref') or {}
        if not isinstance(ref.get('id'), str) or not link.get('relation'):
            continue
        out.append(dict(to_id=ref['id'], to_revision=ref.get('revision'), relation=link['relation'],
                        conditions=link.get('conditions') or '', use=link_use(block_type),
                        rationale=link.get('rationale') or ''))
    return out


register_relation_extractor(extract)
