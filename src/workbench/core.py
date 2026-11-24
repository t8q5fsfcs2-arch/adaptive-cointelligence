"""Persistent records and rebuildable context mechanics; no model or network calls."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Iterable

import networkx as nx


@dataclass(frozen=True, order=True)
class Ref:
    id: str
    revision: int

    def label(self) -> str:
        return f"{self.id}:v{self.revision}"


class StaleBasis(ValueError):
    pass


# D014: typed relationships are written in the same transaction as the record that states
# them. Extractors are pure functions registered by domain modules; core stays kind-agnostic.
RELATION_EXTRACTORS: list = []


def register_relation_extractor(fn) -> None:
    if fn not in RELATION_EXTRACTORS:
        RELATION_EXTRACTORS.append(fn)


class Store:
    """Append revisions; access scopes are supplied by the trusted local test harness."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS records (
            id TEXT NOT NULL, revision INTEGER NOT NULL, kind TEXT NOT NULL,
            scope TEXT NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY (id, revision));
          CREATE TABLE IF NOT EXISTS dependencies (
            dependent_id TEXT, dependent_revision INTEGER,
            basis_id TEXT, basis_revision INTEGER,
            PRIMARY KEY (dependent_id, dependent_revision, basis_id, basis_revision),
            FOREIGN KEY (dependent_id, dependent_revision) REFERENCES records(id, revision),
            FOREIGN KEY (basis_id, basis_revision) REFERENCES records(id, revision));
          CREATE TABLE IF NOT EXISTS packets (
            id TEXT, revision INTEGER, purpose TEXT NOT NULL,
            audience_scopes TEXT NOT NULL, refs TEXT NOT NULL,
            PRIMARY KEY (id, revision));
          CREATE TABLE IF NOT EXISTS relationships (
            from_id TEXT NOT NULL, from_revision INTEGER NOT NULL,
            to_id TEXT NOT NULL, to_revision INTEGER,
            relation TEXT NOT NULL, conditions TEXT NOT NULL DEFAULT '',
            use TEXT NOT NULL DEFAULT '', rationale TEXT NOT NULL DEFAULT '',
            scope TEXT NOT NULL,
            PRIMARY KEY (from_id, from_revision, to_id, relation),
            FOREIGN KEY (from_id, from_revision) REFERENCES records(id, revision));
          CREATE TABLE IF NOT EXISTS relationship_index (
            id TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY (id, revision));
        """)
        self.backfill_relationships()

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self):
        """A workflow command owns one transaction, including nested store calls."""
        if self.db.in_transaction:
            yield
            return
        try:
            self.db.execute("BEGIN IMMEDIATE")
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def latest(self, id: str, allowed_scopes: Iterable[str]) -> dict:
        row = self.db.execute(
            "SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 1", (id,)
        ).fetchone()
        if row is None:
            raise PermissionError("Record is unavailable for this context")
        return self.read(Ref(id, row["revision"]), allowed_scopes)

    def put(self, id: str, kind: str, scope: str, body: dict,
            expected_revision: int = 0) -> Ref:
        if not id or not kind or not scope:
            raise ValueError("Identity, record kind and scope are required")
        encoded = json.dumps(body, sort_keys=True)
        # BEGIN IMMEDIATE makes the expected-version check and insertion atomic.
        with self.transaction():
            previous = self.db.execute(
                "SELECT * FROM records WHERE id=? ORDER BY revision DESC LIMIT 1", (id,)
            ).fetchone()
            actual = previous["revision"] if previous else 0
            if actual != expected_revision:
                raise StaleBasis(f"{id}: expected v{expected_revision}, found v{actual}")
            if previous and (previous["kind"] != kind or previous["scope"] != scope):
                raise ValueError("Scope or kind changes require a separate reviewed release")
            ref = Ref(id, actual + 1)
            self.db.execute("INSERT INTO records VALUES (?,?,?,?,?)",
                            (id, ref.revision, kind, scope, encoded))
            self._index_relationships(ref, kind, scope, body)
            return ref

    def _index_relationships(self, ref: Ref, kind: str, scope: str, body: dict) -> None:
        if not RELATION_EXTRACTORS:
            return
        for extract in RELATION_EXTRACTORS:
            for rel in extract(kind, body) or []:
                self.db.execute(
                    "INSERT OR IGNORE INTO relationships VALUES (?,?,?,?,?,?,?,?,?)",
                    (ref.id, ref.revision, rel["to_id"], rel.get("to_revision"), rel["relation"],
                     rel.get("conditions", ""), rel.get("use", ""), rel.get("rationale", ""), scope))
        self.db.execute("INSERT OR IGNORE INTO relationship_index VALUES (?,?)", (ref.id, ref.revision))

    def backfill_relationships(self) -> int:
        """Index any revision written before its extractor existed. Idempotent."""
        if not RELATION_EXTRACTORS:
            return 0
        rows = self.db.execute("""SELECT r.id, r.revision, r.kind, r.scope, r.body FROM records r
            LEFT JOIN relationship_index i ON i.id=r.id AND i.revision=r.revision
            WHERE i.id IS NULL""").fetchall()
        if not rows:
            return 0
        with self.transaction():
            for row in rows:
                self._index_relationships(Ref(row["id"], row["revision"]), row["kind"], row["scope"],
                                          json.loads(row["body"]))
        return len(rows)

    def relationships(self, allowed_scopes: Iterable[str], latest_only: bool = True) -> list[dict]:
        """Typed links stated by records the caller may read; by default only current statements."""
        scopes = set(allowed_scopes)
        query = """SELECT l.* FROM relationships l"""
        if latest_only:
            query += """ JOIN (SELECT id, MAX(revision) revision FROM records GROUP BY id) cur
                ON cur.id=l.from_id AND cur.revision=l.from_revision"""
        return [dict(row) for row in self.db.execute(query + " ORDER BY l.rowid") if row["scope"] in scopes]

    def read(self, ref: Ref, allowed_scopes: Iterable[str]) -> dict:
        row = self.db.execute("SELECT * FROM records WHERE id=? AND revision=?",
                              (ref.id, ref.revision)).fetchone()
        # Use one error for absent/inaccessible records to avoid disclosing existence.
        if row is None or row["scope"] not in set(allowed_scopes):
            raise PermissionError("Record is unavailable for this context")
        return {"ref": ref, "kind": row["kind"], "scope": row["scope"],
                "body": json.loads(row["body"])}

    def depend(self, dependent: Ref, basis: Ref, allowed_scopes: Iterable[str]) -> None:
        scopes = set(allowed_scopes)
        self.read(dependent, scopes)
        self.read(basis, scopes)
        with self.transaction():
            self.db.execute("INSERT OR IGNORE INTO dependencies VALUES (?,?,?,?)",
                            (dependent.id, dependent.revision, basis.id, basis.revision))

    def graph(self, allowed_scopes: Iterable[str]) -> nx.MultiDiGraph:
        scopes = set(allowed_scopes)
        graph = nx.MultiDiGraph()
        for row in self.db.execute("SELECT * FROM records"):
            if row["scope"] in scopes:
                graph.add_node(Ref(row["id"], row["revision"]),
                               kind=row["kind"], scope=row["scope"])
        for row in self.db.execute("SELECT * FROM dependencies"):
            dependent = Ref(row["dependent_id"], row["dependent_revision"])
            basis = Ref(row["basis_id"], row["basis_revision"])
            if dependent in graph and basis in graph:
                graph.add_edge(dependent, basis, key="depends_on", relation="depends_on")
        return graph

    def packet(self, id: str, revision: int, purpose: str, refs: Iterable[Ref],
               audience_scopes: Iterable[str], requester_scopes: Iterable[str]) -> dict:
        audience = set(audience_scopes)
        if not audience or not audience <= set(requester_scopes):
            raise PermissionError("The requester cannot assemble for this audience")
        chosen = sorted(set(refs))
        if not chosen or not purpose:
            raise ValueError("A packet needs a purpose and at least one reference")
        for ref in chosen:
            self.read(ref, audience)
        manifest = {"id": id, "revision": revision, "purpose": purpose,
                    "audience_scopes": sorted(audience),
                    "refs": [asdict(ref) for ref in chosen]}
        with self.transaction():
            self.db.execute("INSERT INTO packets VALUES (?,?,?,?,?)",
                            (id, revision, purpose, json.dumps(sorted(audience)),
                             json.dumps(manifest["refs"])))
        return manifest

    def packet_manifests(self, allowed_scopes: Iterable[str]) -> list[dict]:
        """List only manifests whose complete audience the caller can inspect."""
        scopes = set(allowed_scopes)
        rows = self.db.execute('SELECT id,revision,audience_scopes FROM packets ORDER BY rowid DESC')
        return [self.read_packet(row['id'], row['revision'], scopes) for row in rows
                if set(json.loads(row['audience_scopes'])) <= scopes]

    def read_packet(self, id: str, revision: int, allowed_scopes: Iterable[str]) -> dict:
        allowed_scopes = set(allowed_scopes)
        row = self.db.execute("SELECT * FROM packets WHERE id=? AND revision=?",
                              (id, revision)).fetchone()
        if row is None or not set(json.loads(row["audience_scopes"])) <= set(allowed_scopes):
            raise PermissionError("Packet is unavailable for this context")
        refs = json.loads(row["refs"])
        for ref in refs:
            self.read(Ref(**ref), set(json.loads(row["audience_scopes"])))
        return {"id": id, "revision": revision, "purpose": row["purpose"],
                "audience_scopes": json.loads(row["audience_scopes"]), "refs": refs}


    def resolve_packet(self, id: str, revision: int, allowed_scopes: Iterable[str]) -> dict:
        """Materialize the issued recipe; newer records never replace its contents.

        Resolve for the packet audience, even when the requester has broader access.
        This local repository retains exact revisions. No external links are fetched.
        """
        manifest = self.read_packet(id, revision, allowed_scopes)
        audience = set(manifest["audience_scopes"])
        records, changed = [], []
        for raw in manifest["refs"]:
            ref = Ref(**raw)
            records.append(self.read(ref, audience))
            current = self.latest(ref.id, audience)["ref"]
            if current != ref:
                changed.append({"previous": raw, "current": asdict(current)})
        return {**manifest, "records": records, "changed_refs": changed}


class ImpactWorker:
    """Trigger: explicit comparison request. Output: known affected references only.

    Motivation: help an owner focus reconsideration. Boundary: no semantic inference,
    approval, automatic requirement updates, or claim of complete dependency coverage.
    """

    def run(self, store: Store, original: Ref, candidate: Ref,
            allowed_scopes: Iterable[str]) -> dict:
        scopes = set(allowed_scopes)
        store.read(original, scopes)
        store.read(candidate, scopes)
        if original.id != candidate.id or candidate.revision <= original.revision:
            raise ValueError("Compare a later revision of the same record")
        graph = store.graph(scopes)
        affected = sorted(nx.ancestors(graph, original) - {original})
        return {"trigger": "record-revision-comparison-requested",
                "original": asdict(original), "candidate": asdict(candidate),
                "affected": [asdict(ref) for ref in affected],
                "coverage": "Known recorded dependencies in the permitted scope only",
                "status": "pending-human-review"}
