"""Exact source links in the existing record repository; no external retrieval.

The text entered in a contribution's `source` field remains an unverified citation.
`source_refs` identifies retained record versions, not proof that a claim is correct.
"""
from .core import StaleBasis
from .validation import reference

SOURCE_KINDS = {"source", "intake-source", "evidence"}


def source_references(store, values, scopes, *, require_current=False):
    """Validate a bounded set for the actual recipient context, without copying data."""
    if not isinstance(values, list) or len(values) > 100:
        raise ValueError("Choose at most 100 exact source versions")
    refs = sorted(set(reference(value) for value in values))
    if len({ref.id for ref in refs}) != len(refs):
        raise ValueError("Choose one version of each source")
    scopes = set(scopes)
    for ref in refs:
        source = store.read(ref, scopes)
        if source["kind"] not in SOURCE_KINDS:
            raise ValueError("Source links must refer to retained source or evidence records")
        if require_current and store.latest(ref.id, scopes)["ref"] != ref:
            raise StaleBasis("A linked source changed. Review it and update the contribution before sharing or requesting review")
    return refs
