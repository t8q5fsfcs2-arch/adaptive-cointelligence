"""Real private packet manifests and explicit, traceable project releases.

No model, extraction or semantic evaluation. Preparation and release use the
same Store.packet/resolve_packet contract as other evidence trail.
"""
from dataclasses import asdict

from .core import StaleBasis
from .decisions import SCOPE, DecisionBlocked, now
from .validation import reference


def prepared_id(record_id):
    return 'PKT-PREP-' + record_id


def prepare(store, record, purpose, refs, private_scope):
    """Pin the selected private and shared records without releasing them."""
    return store.packet(prepared_id(record.id), 1, purpose, [record, *refs],
                        {private_scope, SCOPE}, {private_scope, SCOPE})


def read_prepared(store, record, scopes):
    raw = record['body'].get('packet')
    if not raw:
        raise StaleBasis('This earlier preflight has no context packet. Prepare a fresh packet')
    if raw != dict(id=prepared_id(record['ref'].id), revision=1):
        raise ValueError('The packet does not belong to this preflight')
    packet = store.resolve_packet(raw['id'], raw['revision'], scopes)
    if asdict(record['ref']) not in packet['refs']:
        raise ValueError('The packet must contain its exact preparation record')
    return packet


def release(store, prepared, packet_id, revision, replacements, actor):
    """Finalize precisely the selected contents, substituting explicit releases.

    Prepared/private references remain in a receipt as lineage identifiers only.
    Every resolved record in the released manifest must be project-readable.
    Added business context or silently substituted newer versions are forbidden.
    Callers construct authorized release records inside the same transaction.
    """
    with store.transaction():
        selected = {reference(raw) for raw in prepared['refs']}
        if set(replacements) - selected:
            raise ValueError('A release mapping references content outside the prepared packet')
        for old, new in replacements.items():
            if old != new and store.read(old, prepared['audience_scopes'])['scope'] == SCOPE:
                raise ValueError('Shared context must retain its prepared version on release')
        receipt_id = 'RECEIPT-' + prepared['id'] + '-' + str(prepared['revision'])
        if store.db.execute('SELECT 1 FROM records WHERE id=?', (receipt_id,)).fetchone():
            raise DecisionBlocked('This prepared packet has already been released')
        released = sorted({replacements.get(ref, ref) for ref in selected})
        for ref in released:
            store.read(ref, {SCOPE})
        receipt = store.put(receipt_id, 'packet-release', SCOPE, dict(
            prepared_packet=dict(id=prepared['id'], revision=prepared['revision']),
            published_packet=dict(id=packet_id, revision=revision),
            reference_map=[dict(prepared=asdict(ref), released=asdict(replacements.get(ref, ref)))
                           for ref in sorted(selected)],
            released_by=actor, at=now(), status='released-not-approved',
            note='Same selected content; private draft/source identities map to explicit project releases.'))
        for ref in released:
            store.depend(receipt, ref, {SCOPE})
        packet = store.packet(packet_id, revision, prepared['purpose'], [*released, receipt], {SCOPE}, {SCOPE})
        return dict(packet=dict(id=packet['id'], revision=packet['revision']), receipt=asdict(receipt))
