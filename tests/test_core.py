import tempfile
import unittest
from pathlib import Path

from workbench.core import ImpactWorker, Ref, StaleBasis, Store


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.sqlite3"
        self.store = Store(self.path)
        self.shared = {"project:demo"}

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def put(self, id, scope="project:demo", revision=0):
        return self.store.put(id, "test-record", scope, {"text": id}, revision)

    def test_packet_survives_restart_and_does_not_follow_latest(self):
        old = self.put("EVD")
        packet = self.store.packet("PKT", 1, "Review", [old], self.shared, self.shared)
        self.put("EVD", revision=1)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(packet, self.store.read_packet("PKT", 1, self.shared))
        self.assertEqual(self.store.read(old, self.shared)["ref"].revision, 1)

    def test_stale_write_rejected_without_extra_revision(self):
        self.put("REQ")
        self.put("REQ", revision=1)
        with self.assertRaises(StaleBasis):
            self.put("REQ", revision=1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0], 2)

    def test_bridge_checks_recipient_audience_not_only_author(self):
        secret = self.put("PRIVATE", "domain:research")
        with self.assertRaises(PermissionError):
            self.store.packet("BRIDGE", 1, "Shared review", [secret],
                              self.shared, self.shared | {"domain:research"})
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM packets").fetchone()[0], 0)

    def test_impact_follows_transitive_links_and_excludes_unrelated_work(self):
        original = self.put("EVD")
        claim, req, other = self.put("CLM"), self.put("REQ"), self.put("UNRELATED")
        self.store.depend(claim, original, self.shared)
        self.store.depend(req, claim, self.shared)
        candidate = self.put("EVD", revision=1)
        result = ImpactWorker().run(self.store, original, candidate, self.shared)
        self.assertEqual(result["affected"], [{"id": "CLM", "revision": 1}, {"id": "REQ", "revision": 1}])
        self.assertEqual(result["status"], "pending-human-review")
        self.assertEqual(self.store.read(req, self.shared)["ref"], req)

    def test_hidden_record_is_absent_from_graph_and_impact(self):
        original = self.put("EVD")
        private = self.put("PRIVATE", "domain:research")
        self.store.depend(private, original, self.shared | {"domain:research"})
        self.assertNotIn(private, self.store.graph(self.shared))
        candidate = self.put("EVD", revision=1)
        self.assertEqual(ImpactWorker().run(self.store, original, candidate, self.shared)["affected"], [])

    def test_duplicate_packet_version_cannot_overwrite_history(self):
        import sqlite3
        evidence = self.put("EVD")
        original = self.store.packet("PKT", 1, "Original", [evidence], self.shared, self.shared)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.packet("PKT", 1, "Replacement", [evidence], self.shared, self.shared)
        self.assertEqual(original, self.store.read_packet("PKT", 1, self.shared))

    def test_scope_cannot_be_changed_in_place(self):
        self.put("PRIVATE", "domain:research")
        with self.assertRaises(ValueError):
            self.put("PRIVATE", "project:demo", revision=1)

    def test_graph_rebuilds_after_restart(self):
        a, b = self.put("REQ"), self.put("EVD")
        self.store.depend(a, b, self.shared)
        self.store.close()
        self.store = Store(self.path)
        self.assertTrue(self.store.graph(self.shared).has_edge(a, b))


if __name__ == "__main__":
    unittest.main()
