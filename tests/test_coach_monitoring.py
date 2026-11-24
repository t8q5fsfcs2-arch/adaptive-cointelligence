import test_coaching
from workbench.agent_runs import monitoring
from workbench.model_provider import ModelUnavailable
from unittest import TestCase

class CoachMonitoring(TestCase):
    def test_existing_coach_records_failures_and_success_with_exact_config(self):
        fixture=test_coaching.CoachingTests();fixture.setUp()
        try:
            fixture.model.custom={'reply':'Focus on the consequence.','suggestions':[],'questions':[]}
            fixture.run_coach(sources=[])
            info=monitoring(fixture.store,'priya');self.assertEqual(info['runs'][0]['persona_id'],'P02')
            self.assertEqual(info['runs'][0]['status'],'succeeded');self.assertEqual(info['summaries'][0]['tokens'],20)
            fixture.model.custom={}
            with self.assertRaises(ModelUnavailable):fixture.run_coach(sources=[])
            info=monitoring(fixture.store,'priya');self.assertEqual(info['summaries'][0]['failed'],1)
            self.assertEqual(info['summaries'][0]['completed'],1);self.assertEqual(info['legacy_count'],0)
        finally:fixture.tearDown()
