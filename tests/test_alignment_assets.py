import unittest

import test_web


class AlignmentAssetTests(unittest.TestCase):
    def setUp(self):
        self.web = test_web.WebTests()
        self.web.setUp()

    def tearDown(self):
        self.web.tearDown()

    def test_alignment_layer_is_served_after_component_styles(self):
        self.web.conn.request("GET", "/")
        response = self.web.conn.getresponse()
        self.assertEqual(response.status, 200)
        html = response.read().decode()
        alignment = html.index('href="/alignment.css"')
        for stylesheet in ("workspace.css", "signals.css", "requirement-organization.css", "reviewer-ui.css"):
            self.assertLess(html.index(f'href="/{stylesheet}"'), alignment)

        self.web.conn.request("GET", "/alignment.css")
        response = self.web.conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertTrue(response.getheader("Content-Type").startswith("text/css"))
        self.assertIn(b"--alignment-marker-space", response.read())


if __name__ == "__main__":
    unittest.main()
