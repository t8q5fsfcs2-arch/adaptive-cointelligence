"""Shared, exact-approval delivery observations; simulation is never external proof."""
from dataclasses import asdict
from copy import deepcopy
from .core import Ref
from .decisions import SCOPE
from .validation import reference


class ReceiptDelivery:
    def __init__(self,store):self.store=store;self._records=None
    def records(self):
        if self._records is None:
            self._records=[]
            for row in self.store.db.execute("SELECT id,MAX(revision) revision FROM records WHERE scope=? AND kind IN ('delivery-draft','demo-delivery-preview','demo-delivery-receipt') GROUP BY id",(SCOPE,)):
                self._records.append(self.store.read(Ref(row['id'],row['revision']),{SCOPE}))
        return self._records
    def observed(self,issue,decision,approved):
        result=dict(applicable=bool(approved and approved['kind']=='requirement'),external_status='not-confirmed',connected=False,external_story_url=None,
                    message='No confirmed external update is recorded. A live Jira/ADO connector is not connected.',targets=[])
        if not result['applicable']:
            result['message']='This decision approved no requirement change for delivery.'
            return result
        req=approved['ref'];dec=asdict(decision['ref']);records=self.records();previews={}
        for r in records:
            b=r['body']
            if r['kind']=='demo-delivery-preview' and b.get('mode')=='simulated' and b.get('issue',{}).get('id')==issue['ref'].id and b.get('decision')==dec and b.get('requirement')==req and b.get('target') in {'jira','ado'}:
                previews[r['ref']]=r
        valid=[];unavailable=False
        for r in records:
            b=r['body']
            if r['kind']!='demo-delivery-receipt' or b.get('decision')!=dec or b.get('requirement')!=req or b.get('issue',{}).get('id')!=issue['ref'].id:continue
            try:
                p=self.store.read(reference(b.get('preview')),{SCOPE});pb=p['body']
                item=self.store.read(reference(b.get('item')),{SCOPE});ib=item['body'];snapshot=b.get('item_snapshot',{})
                if (b.get('mode')!='simulated' or b.get('external_request_sent') is not False or b.get('status')!='demo-update-recorded' or b.get('target') not in {'jira','ado'} or
                    p['kind']!='demo-delivery-preview' or pb.get('mode')!='simulated' or pb.get('decision')!=dec or pb.get('requirement')!=req or pb.get('issue',{}).get('id')!=issue['ref'].id or pb.get('target')!=b['target'] or
                    item['kind']!='demo-delivery-item' or ib.get('mode')!='simulated' or ib.get('target')!=b['target'] or ib.get('approval')!=dec or ib.get('issue',{}).get('id')!=issue['ref'].id or ib.get('snapshot')!=snapshot or snapshot.get('source')!=req or not isinstance(snapshot.get('key'),str)):
                    unavailable=True;continue
                valid.append(r)
            except (PermissionError,ValueError,KeyError,TypeError):unavailable=True
        for target in ('jira','ado'):
            receipts=[r for r in valid if r['body']['target']==target];receipt_previews={reference(r['body']['preview']) for r in receipts};transactions=[]
            for r in previews.values():
                b=r['body']
                if b['target']==target:
                    transactions.append(dict(ref=asdict(r['ref']),kind=r['kind'],status='simulated' if r['ref'] in receipt_previews else 'staged',mode='demo',target=target,destination=b.get('destination',''),at=b.get('at'),story_key=b.get('after',{}).get('key'),source=req))
            for r in records:
                b=r['body']
                if r['kind']!='delivery-draft' or b.get('target')!=target or req not in b.get('requirements',[]):continue
                # No private sponsor previews cross into this shared receipt.
                selected=[deepcopy(item) for item in b.get('items',[]) if item.get('source')==req]
                if not selected:continue
                transactions.append(dict(ref=asdict(r['ref']),kind=r['kind'],status='staged',mode='preview',target=target,destination=b.get('destination',''),at=b.get('at'),source=req,
                                         work_item_type=b.get('work_item_type'),items=selected,unverified_external_references=bool(b.get('external_receipts'))))
            transactions.sort(key=lambda x:(x.get('at') or '',x['ref']['id']),reverse=True)
            receipts.sort(key=lambda r:(r['body'].get('at') or '',r['ref'].id),reverse=True)
            stories=[dict(receipt=asdict(r['ref']),item=r['body']['item'],key=r['body']['item_snapshot']['key'],at=r['body'].get('at'),mode='simulated',external_request_sent=False) for r in receipts]
            result['targets'].append(dict(target=target,status='simulated' if stories else 'staged' if transactions else 'not-staged',transactions=transactions,stories=stories))
        if unavailable:result['warning']='A linked simulation result could not be verified in shared context. It is not evidence of an external update.'
        return result
