import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from workbench.web import BrowserServer
from workbench.model_provider import UnconfiguredModel


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = BrowserServer(("127.0.0.1", 0), Path(self.tmp.name) / "web.sqlite3", UnconfiguredModel(), test_profiles=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        self.conn.request("GET", "/api/state")
        response = self.conn.getresponse()
        self.cookie = response.getheader("Set-Cookie").split(";")[0]
        self.state = json.loads(response.read())
        self.csrf = self.state["csrf"]

    def tearDown(self):
        self.conn.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def post(self, action, payload, headers=None):
        self.conn.request("POST", "/api/" + action, body=json.dumps(payload), headers={"Cookie": self.cookie, "X-CSRF-Token": self.csrf, "Content-Type": "application/json", "X-Workbench-Project": self.state["project"]["id"], "X-Workbench-Version": str(self.state["project"]["version"]), **(headers or {})})
        response = self.conn.getresponse()
        return response.status, json.loads(response.read())

    def test_workspace_notice_is_explicit_server_configuration(self):
        self.assertIsNone(self.state['workspace_notice'])
        self.server.workspace_notice = 'Test workspace · Synthetic data'
        self.conn.request('GET', '/api/state', headers={'Cookie': self.cookie})
        response = self.conn.getresponse()
        self.assertEqual(json.loads(response.read())['workspace_notice'], self.server.workspace_notice)

    def test_removed_assignment_creation_is_rejected_over_http(self):
        before=self.state['project_flow']['requests']
        status,result=self.post('work-request-create',{})
        self.assertEqual(status,400)
        self.assertIn('work assignment has been removed',result['error'])
        self.conn.request('GET','/api/state',headers={'Cookie':self.cookie})
        response=self.conn.getresponse()
        flow=json.loads(response.read())['project_flow']
        self.assertFalse(flow['can_request'])
        self.assertEqual(flow['requests'],before)

    def test_api_rejects_cross_site_and_missing_csrf(self):
        self.assertEqual(self.post("profile", {"actor": "sam"}, {"Origin": "https://unrelated.example"})[0], 403)
        self.assertEqual(self.post("profile", {"actor": "sam"}, {"X-CSRF-Token": ""})[0], 403)

    def test_external_entry_serves_only_public_shell_without_session(self):
        headers={'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'navigate',
                 'Sec-Fetch-Dest':'document','Sec-Fetch-User':'?1','Cookie':self.cookie}
        before=dict(self.server.sessions)
        self.conn.request('GET','/',headers=headers)
        response=self.conn.getresponse()
        self.assertEqual(response.status,200)
        self.assertIn('text/html',response.getheader('Content-Type'))
        self.assertIsNone(response.getheader('Set-Cookie'))
        self.assertIn("frame-ancestors 'none'",response.getheader('Content-Security-Policy'))
        self.assertIn(b'<html',response.read().lower())
        self.assertEqual(self.server.sessions,before)
        cases=[('GET','/api/state',{}),('GET','/api/auth',{}),('POST','/api/profile',{}),
               ('POST','/',{}),('GET','/app.js',{}),('GET','/?action=change',{}),
               ('GET','/',{'Host':'evil.example'}),('GET','/',{'Host':'127.0.0.1:1'}),
               ('GET','/',{'Origin':'https://unrelated.example'}),('GET','/',{'Origin':'null'}),
               ('GET','/',{'Origin':''}),('GET','/',{'Sec-Fetch-Dest':'iframe'}),
               ('GET','/',{'Sec-Fetch-Dest':'image','Sec-Fetch-Mode':'no-cors'}),
               ('GET','/',{'Sec-Fetch-User':''})]
        for method,path,override in cases:
            with self.subTest(method=method,path=path,override=override):
                self.conn.request(method,path,headers={**headers,**override})
                response=self.conn.getresponse();self.assertEqual(response.status,403);response.read()
        # Opening the shell grants no write privilege: CSRF remains required.
        self.assertEqual(self.post('profile',{'actor':'sam'},{'X-CSRF-Token':''})[0],403)

    def test_host_and_path_guard(self):
        self.conn.request("GET", "/api/state", headers={"Host": "evil.example"})
        response = self.conn.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        self.conn.request("GET", "/../pyproject.toml")
        response = self.conn.getresponse()
        self.assertEqual(response.status, 404)
        response.read()

    def test_browser_assets_and_project_creation(self):
        for path in ("/", "/app.js", "/settings.js", "/agent-quality.js", "/document-changes.js", "/requirement-agent.js", "/field-coach.js", "/goals.js", "/domains.js", "/bridge.js", "/packets.js", "/intake.js", "/refinements.js", "/style.css", "/signals.js", "/signals.css", "/signal-accountability.css"):
            self.conn.request("GET", path)
            response = self.conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("frame-ancestors 'none'", response.getheader("Content-Security-Policy"))
            self.assertGreater(len(response.read()), 100)
        self.post("profile", {"actor": "alex"})
        status, body = self.post("setup", {"title": "My test", "intent": "Reduce effort", "boundary": "Keep rules"})
        self.assertEqual(status, 200, body)
        self.conn.request("GET", "/api/state", headers={"Cookie": self.cookie})
        response = self.conn.getresponse()
        self.assertTrue(json.loads(response.read())["initialized"])

    def test_agent_descriptor_round_trip(self):
        self.assertEqual(self.post('intake-start',{'title':'Synthetic agent inventory'})[0],200)
        status,body=self.post('agent-descriptor-save',{'expected':None,'persona_id':'P04','descriptor':'Requirement quality partner'})
        self.assertEqual(status,200,body)
        self.conn.request('GET','/api/state',headers={'Cookie':self.cookie})
        response=self.conn.getresponse();state=json.loads(response.read())
        registry=state['coaching']['settings']['agent_registry']
        p4=next(p for p in registry['profiles'] if p['id']=='P04')
        self.assertEqual(p4['descriptor'],'Requirement quality partner')
        self.assertEqual(p4['implementation']['status'],'partial')
        self.assertEqual(p4['implementation']['runtime_id'],'requirement-assistant')
        self.assertEqual(p4['implementation']['mode'],'not-connected')

    def test_profile_is_server_session_and_not_command_actor(self):
        self.assertEqual(self.post("profile", {"actor": "sam"})[0], 200)
        self.assertEqual(self.post("setup", {"actor": "alex", "title": "Spoof", "intent": "No", "boundary": "No"})[0], 403)


if __name__ == "__main__":
    unittest.main()
