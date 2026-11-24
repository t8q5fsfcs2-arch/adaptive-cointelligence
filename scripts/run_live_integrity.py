#!/usr/bin/env python3
"""Build a synthetic live Integrity Review, or serve its saved history.

Never consumes a client database. --serve-existing requires the fixture marker.
The Settings-managed credential is used in memory, never copied into the demo.
"""
import argparse,json
from contextlib import closing
from pathlib import Path
from dataclasses import asdict
from workbench.core import Store,Ref
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.integrity_example import Fixture
from workbench.model_connection import ModelConnections

MARKER='INTEGRITY-LIVE-EXAMPLE'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-settings',required=True,type=Path);p.add_argument('--project',required=True)
    where=p.add_mutually_exclusive_group(required=True);where.add_argument('--output',type=Path);where.add_argument('--serve-existing',type=Path)
    p.add_argument('--serve',action='store_true');p.add_argument('--port',default=8769,type=int);args=p.parse_args()
    model=ModelConnections(args.model_settings).select([args.project])
    if not model.status().get('configured'):p.error('Use a project with an existing model connection.')
    db=args.serve_existing
    if db:
        with closing(Store(db)) as store:
            if store.latest(MARKER,{SCOPE})['body'].get('synthetic') is not True:raise SystemExit('Only a marked synthetic fixture can be served with this command.')
    else:
        args.output.mkdir(parents=True,exist_ok=True);db=args.output/'worked-case.sqlite3'
        if db.exists():raise SystemExit('Choose a fresh directory; existing history was preserved.')
        f=Fixture(db)
        try:
            f.store.put(MARKER,'demo-fixture',SCOPE,dict(synthetic=True,boundary='Synthetic testing only; fictional human roles, real requested model execution.'))
            f.store.put('PROJECT-001','project',SCOPE,dict(title='Integrity Review — synthetic qualification case'))
            f.local_approvals();a=f.assessment(associations=[f.association()])['ref'];issue=f.issue(a)
            for finding in f.review(a)['body']['findings']:
                if finding['material']:
                    f.w('alex').integrity.dispose(dict(expected=asdict(f.current(issue)['ref']),finding=finding['key'],disposition='investigate-and-defer',rationale='Synthetic setup: retain this gap for evidence review before any ratification.'))
            current=f.current(issue);ctx=f.review(a)['body']['context'];w=Workspace(f.store,'alex',model)
            live=w.integrity.assess(dict(packets=ctx['packets'],associations=ctx['associations'],proposal=ctx['proposal'],evaluation_scope='cross-domain',mode='formal',confirm=True,semantic=True,consent=True))
            w.integrity.attach(dict(expected=asdict(current['ref']),assessment=live['ref']))
            trace=w.integrity.decision_view(f.current(issue));(args.output/'review.json').write_text(json.dumps(trace,default=lambda r:asdict(r) if isinstance(r,Ref) else str(r),indent=2))
            print(json.dumps(dict(database=str(db),issue=issue,assessment=live['ref'],summary=trace['summary'],ratification=trace['ratification'])),flush=True)
        finally:f.store.close()
    if args.serve or args.serve_existing:
        from workbench.web import BrowserServer
        server=BrowserServer(('127.0.0.1',args.port),db,model,development=True)
        print(f'Live synthetic Integrity Review: http://127.0.0.1:{args.port}/',flush=True)
        print('Existing Settings-managed connection; no copied credential. Local development roles; no automatic ratification.',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:print('Stopped. Review history is saved.')
        finally:server.server_close()

if __name__=='__main__':main()
