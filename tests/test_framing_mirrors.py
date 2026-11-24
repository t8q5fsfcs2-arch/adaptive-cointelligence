import json, unittest

from workbench.sponsor import sync_intent_field


def draft(problem='Old problem', summary_problem=None, approach='Old offering', summary_solution=None, context='Old users'):
    return dict(values=dict(business_challenge=problem, approach=approach, user_situation=context),
                sponsor_brief=dict(answers={}, framing=dict(name='P', context=context, statement=problem,
                    summary=dict(problem=problem if summary_problem is None else summary_problem,
                                 solution=approach if summary_solution is None else summary_solution, risk='', options=''))))


class FramingMirrorTests(unittest.TestCase):
    def test_accepted_problem_change_updates_every_mirror(self):
        body = draft()
        left = sync_intent_field(body, 'business_challenge', 'New problem')
        f = body['sponsor_brief']['framing']
        self.assertEqual(left, [])
        self.assertEqual(body['values']['business_challenge'], 'New problem')
        self.assertEqual(f['statement'], 'New problem')
        self.assertEqual(f['summary']['problem'], 'New problem')
        self.assertEqual(json.loads(body['values']['executive_summary'])['problem'], 'New problem')
        self.assertEqual(body['sponsor_brief']['answers']['q2']['items'], ['New problem'])

    def test_a_summary_the_sponsor_rewrote_is_left_and_reported(self):
        body = draft(summary_problem='My own short summary')
        left = sync_intent_field(body, 'business_challenge', 'New problem')
        f = body['sponsor_brief']['framing']
        self.assertEqual(f['statement'], 'New problem')
        self.assertEqual(f['summary']['problem'], 'My own short summary')
        self.assertEqual(left, ['Summary · problem'])

    def test_offering_and_users_mirrors(self):
        body = draft()
        sync_intent_field(body, 'approach', 'New offering')
        sync_intent_field(body, 'user_situation', 'New users')
        f = body['sponsor_brief']['framing']
        self.assertEqual(f['summary']['solution'], 'New offering')
        self.assertEqual(f['context'], 'New users')


if __name__ == '__main__':
    unittest.main()
