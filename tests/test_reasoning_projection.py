from copy import deepcopy
import unittest
from workbench.core import Ref
from workbench.reasoning_projection import reasoning_record


class ReasoningProjectionTests(unittest.TestCase):
    def test_intent_keeps_exact_user_context_and_roles_without_repeating_taxonomy(self):
        roles=dict(roles=[dict(name='Supervisor',needs='Accepted ownership')],confirmed=False)
        record=dict(ref=Ref('INT-001',2),kind='intent',scope='project',body=dict(text='Current value',intake=dict(jobs='Coordinate nonurgent follow-through',out_scope='Active operational command',investment_case='Costs unknown'),scaffold=[dict(label='Experience',children=[dict(question='Repeated template')])],business_brief=dict(answers=dict(q4=roles,q2=dict(items=['Repeated problem'])))))
        before=deepcopy(record);view=reasoning_record(record)
        self.assertEqual(record,before);self.assertEqual(view['ref'],Ref('INT-001',2))
        self.assertEqual(view['body']['intake'],record['body']['intake'])
        self.assertEqual(view['body']['business_brief']['answers']['q4'],roles)
        self.assertNotIn('scaffold',view['body']);self.assertIn('context_projection',view)

    def test_requirement_and_source_content_are_not_summarized(self):
        for kind in ('requirement','source','contribution'):
            record=dict(ref=Ref('R',4),kind=kind,body=dict(text='Exact wording',acceptance_criteria='Exact test',source_refs=[dict(id='S',revision=2)]))
            self.assertEqual(reasoning_record(record),record)

    def test_only_proven_duplicate_specification_is_removed_and_issue_authority_stays(self):
        r=dict(ref=Ref('G',1),kind='goal',body=dict(title='Outcome',specification=dict(title='Outcome')))
        self.assertNotIn('specification',reasoning_record(r)['body'])
        r['body']['specification']['unique']='Important extra';self.assertIn('specification',reasoning_record(r)['body'])
        issue=dict(ref=Ref('I',2),kind='bridge-issue',body=dict(question='Who decides?',decision_rights=dict(decider='priya'),status='open',packet_refs=[dict(id='P',revision=1)],observed_versions=[dict(selected=dict(id='R',revision=1))]))
        v=reasoning_record(issue)
        for key in ('question','decision_rights','status','packet_refs'):self.assertEqual(v['body'][key],issue['body'][key])
