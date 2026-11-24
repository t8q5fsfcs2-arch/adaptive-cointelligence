"""Human-curated report sections within the existing versioned domain deliverable.

No model calls. AI partner output stays immutable; only explicitly selected excerpts
enter the authored report. Publication remains the domain preflight service.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .validation import reference
from .conversation_findings import document


def text(value, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError('Provide report text within the displayed field limits')
    return value.strip()


def public_report(report, mapping):
    """Only selected authored content and citation metadata cross the boundary."""
    result=deepcopy(report)
    result.pop('conversation_update',None)
    for entry in result.get('entries',[]):
        if entry.get('knowledge_card_ref'):
            raw=reference(entry['knowledge_card_ref']);entry['knowledge_card_ref']=asdict(mapping.get(raw,raw))
        for citation in entry.get('citations',[]):
            if citation.get('ref'):
                raw=reference(citation['ref']);citation['ref']=asdict(mapping.get(raw,raw))
        # Original review/draft identifiers are lineage only, never review contents.
        if entry.get('origins'):
            entry['origins']=[{k:o[k] for k in ('review','index','mode','reviewed_draft') if k in o} for o in entry['origins']]
        if entry.get('origin'):
            origin=entry['origin']
            entry['origin']={k:origin[k] for k in ('review','index','mode','reviewed_draft') if k in origin}
    return result


class WorkingReport:
    def __init__(self, workspace):
        self.w=workspace;self.store=workspace.store
    def current(self, data):
        thread=self.w.domain_chat.owned(data.get('conversation'))
        self.w.domain_chat.available(thread)
        draft=self.w.domain_chat.draft(thread)
        if reference(data.get('expected'))!=draft['ref']:
            raise StaleBasis('This deliverable changed. Your report edits are retained; reload its current version before saving.')
        return thread,draft
    def selection_current(self, report, thread):
        """Curation alone does not prevent selecting another finding from one review.

        All assessed inputs other than the authored report and draft identity must
        still match. Actual source, requirement, intent or authored-field changes
        require an explicit historical-selection acknowledgement.
        """
        try:
            b=report['body'];draft=self.w.domain_chat.draft(thread)
            current,_=self.w.domain_chat.basis(thread,b['batch'],expected=asdict(draft['ref']),source_ref=b.get('source'),purpose=b.get('purpose'))
            original=deepcopy(b['context'])
            if 'evidence_passages' not in original:current.pop('evidence_passages',None)
            for ctx,raw in ((current,asdict(draft['ref'])),(original,b['draft'])):
                for key in ('question','previous_exchanges','author_assessments','working_implications','working_report','conversation_findings','card_capture_options','card_assessment','brief_development'):ctx.pop(key,None)
                ctx['basis']=[r for r in ctx['basis'] if r!=raw]
            return current==original
        except (ValueError,PermissionError,KeyError):
            return False
    def persist(self, draft, report):
        report={**deepcopy(report),'purpose':'Editable private findings developed with the author and AI partner. Other fields may be earlier supporting notes. This is not validated evidence or requirement approval.','saved_by':self.w.actor,'saved_at':now()}
        body={**draft['body'],'working_report':report,'saved_at':now()}
        ref=self.store.put(draft['ref'].id,draft['kind'],draft['scope'],body,draft['ref'].revision)
        # Carry forward the existing exact dependencies, then selected advice lineage.
        bases={Ref(r[0],r[1]) for r in self.store.db.execute('SELECT basis_id,basis_revision FROM dependencies WHERE dependent_id=? AND dependent_revision=?',(draft['ref'].id,draft['ref'].revision))}
        bases.difference_update(reference(e['origin']['review']) for e in draft['body'].get('working_report',{}).get('entries',[]) if e.get('origin'))
        bases.update(reference(e['origin']['review']) for e in report['entries'] if e.get('origin'))
        bases.update(reference(o['review']) for e in report['entries'] for o in e.get('origins',[]))
        for basis in bases:self.store.depend(ref,basis,self.w.scopes)
        return dict(id=ref.id,ref=asdict(ref),message='Outcomes report saved as a new draft version. Sharing remains separate.')
    def add(self,data):
        if data.get('confirm') is not True:raise ValueError('Confirm adding this finding to your report')
        with self.store.transaction():
            thread,draft=self.current(data)
            review=self.store.read(reference(data.get('report')),{self.w.domains.scope})
            b=review['body']
            if review['kind']!='domain-chat-review' or b.get('conversation')!=thread['ref'].id or b.get('owner')!=self.w.actor:
                raise PermissionError('Choose a finding from your own conversation')
            index=data.get('index');items=b['output'].get('findings',b['output'].get('suggestions',[]))
            if type(index) is not int or not 0<=index<len(items):raise ValueError('Choose a saved AI partner finding')
            report=deepcopy(draft['body'].get('working_report',{'entries':[]}))
            if any(e.get('origin',{}).get('review')==asdict(review['ref']) and e['origin']['index']==index for e in report['entries']):
                return dict(id=draft['ref'].id,ref=asdict(draft['ref']),duplicate=True,message='This finding is already in your report.')
            fresh=self.selection_current(review,thread)
            if not fresh and data.get('confirm_historical') is not True:
                raise StaleBasis('This finding uses earlier inputs. Inspect its basis and explicitly confirm using it as historical advice.')
            if len(report['entries'])>=40:raise ValueError('An Outcomes report can contain up to 40 sections')
            report['entries'].append(self.review_entry(draft,review,index,fresh))
            if len(json.dumps(report))>160000:raise ValueError('Shorten the report before adding another finding')
            return self.persist(draft,report)
    def review_entry(self,draft,review,index,fresh=True):
        b=review['body'];items=b['output'].get('findings',b['output'].get('suggestions',[]));f=items[index];citations=[]
        if b['format']=='visual':
            heading='Page '+str(f['page'])+' · '+f['area']
            wording='Observation\n'+f['observation']+'\n\nWhy it matters\n'+f['rationale']+'\n\nRecommendation\n'+f['recommendation']
            if f.get('uncertainty'):wording+='\n\nUncertainty\n'+f['uncertainty']
            citations=[dict(ref=deepcopy(link['ref']),quote=link['quote']) for link in f['context_links']]
            citations.insert(0,dict(ref=deepcopy(b['source']),quote='',page=f['page']))
            reqs=[raw for raw in draft['body']['requirement_refs'] if raw in [c['ref'] for c in citations]]
        else:
            heading=f['issue'];wording=f['question']
            if f.get('edit',{}).get('text'):wording+='\n\nSuggested wording\n'+f['edit']['text']
            source=next((s for s in b['context'].get('sources',[]) if s['ref']['id']==f['basis']),None)
            citations=[dict(ref=deepcopy(source['ref']) if source else None,quote=f['quote'],basis=f['basis'])]
            reqs=[r['ref'] for r in b['context'].get('requirements',[]) if r['ref']['id'] in f.get('requirement_ids',[])]
        attached=draft['body'].get('source_refs',[])
        for c in citations:
            if c.get('ref'):
                rec=self.store.read(reference(c['ref']),self.w.scopes)
                if rec['kind']=='source' and c['ref'] not in attached:
                    raise ValueError('Attach the cited source version to this deliverable before adding its finding')
        return dict(id='WRITEM-'+uuid4().hex[:12],heading=text(heading,240,True),text=text(wording,20000,True),
            citations=citations,requirement_refs=deepcopy(reqs),origin=dict(review=asdict(review['ref']),index=index,mode=b['mode'],reviewed_draft=deepcopy(b['draft']),historical_confirmed=not fresh),selected_by=self.w.actor,selected_at=now())
    def save(self,data):
        with self.store.transaction():
            _,draft=self.current(data);entries=data.get('entries')
            if not isinstance(entries,list) or len(entries)>40:raise ValueError('Provide up to 40 report sections')
            old=draft['body'].get('working_report',{'entries':[]});known={e['id']:e for e in old['entries']};seen=set();updated=[]
            for item in entries:
                if not isinstance(item,dict) or set(item)!={'id','heading','text'}:raise ValueError('Edit only report headings and text')
                key=item['id']
                if not isinstance(key,str) or key in seen:raise ValueError('Each report section needs a unique identity')
                seen.add(key)
                if key not in known and (not key.startswith('new-') or len(key)>80):raise ValueError('Choose an existing section or add a new section')
                entry=deepcopy(known[key]) if key in known else dict(id='WRITEM-'+uuid4().hex[:12],citations=[],requirement_refs=[],authored_by=self.w.actor)
                entry.update(heading=text(item['heading'],240,True),text=text(item['text'],20000,True));updated.append(entry)
            report={**old,'entries':updated}
            if len(json.dumps(report))>160000:raise ValueError('Shorten the report (maximum 160,000 characters including citations)')
            if old.get('entries')==updated:return dict(id=draft['ref'].id,ref=asdict(draft['ref']),message='Your report is already saved.')
            return self.persist(draft,report)
    def document_report(self,draft,value,review=None):
        old=draft['body'].get('working_report',{});entries=old.get('entries',[])
        metadata=list(entries)
        if review:
            items=review['body']['output'].get('findings',review['body']['output'].get('suggestions',[]))
            metadata += [self.review_entry(draft,review,i) for i in range(len(items))]
        def distinct(items):
            return list({json.dumps(v,sort_keys=True):v for v in items}.values())
        citations=distinct([c for e in metadata for c in e.get('citations',[])])
        origins=distinct([o for e in metadata for o in ([e['origin']] if e.get('origin') else [])+e.get('origins',[])])
        refs=distinct([raw for e in metadata for raw in e.get('requirement_refs',[])])
        entry=dict(id=entries[0]['id'] if old.get('format')=='document' and entries else 'WRITEM-'+uuid4().hex[:12],
            heading='Findings',text=value,citations=citations,requirement_refs=refs,origins=origins)
        if not review:entry.update(authored_by=self.w.actor)
        report=dict(format='document',entries=[entry] if value else [])
        if review:report['conversation_update']=dict(before=asdict(draft['ref']),after=dict(id=draft['ref'].id,revision=draft['ref'].revision+1),review=asdict(review['ref']))
        if len(json.dumps(report))>160000:raise ValueError('The findings and their evidence exceed the current document limit. Narrow the review scope.')
        return report
    def aggregate(self,thread,review):
        value=review['body']['output'].get('findings_document')
        if value is None:return None
        draft=self.w.domain_chat.draft(thread)
        if asdict(draft['ref'])!=review['body']['draft']:raise StaleBasis('Findings changed while the reply was being prepared. Your saved wording is retained.')
        value=text(value,20000)
        # A conversation without new findings must not erase an existing draft.
        if not value or value==document(draft['body']):return None
        return self.persist(draft,self.document_report(draft,value,review))
    def save_document(self,data):
        with self.store.transaction():
            _,draft=self.current(data);value=text(data.get('document'),20000)
            if value==document(draft['body']):return dict(id=draft['ref'].id,ref=asdict(draft['ref']),message='Findings already saved.')
            return self.persist(draft,self.document_report(draft,value))
    def undo_document(self,data):
        with self.store.transaction():
            _,draft=self.current(data);update=draft['body'].get('working_report',{}).get('conversation_update')
            if not update or update['after']!=asdict(draft['ref']):raise StaleBasis('The findings have changed since that update. Your current wording is retained.')
            before=self.store.read(reference(update['before']),{self.w.domains.scope})
            if before['ref'].id!=draft['ref'].id or before['body']['owner']!=self.w.actor:raise PermissionError('Choose the prior version of your findings')
            old=before['body'].get('working_report')
            return self.persist(draft,old or self.document_report(before,document(before['body'])))
    def prepare_document(self,data):
        with self.store.transaction():
            _,draft=self.current(data)
            if not document(draft['body']).strip():raise ValueError('Develop your findings before sharing.')
            previous=sorted([h for h in self.w.domains.handoffs() if h['body']['draft']['id']==draft['ref'].id and h['body']['owner']==self.w.actor],key=lambda h:h['body'].get('at',''),reverse=True)
            notes=previous[0]['body'].get('handoff',{}) if previous else draft['body']
            return self.w.domains.prepare(dict(expected=asdict(draft['ref']),recipient=previous[0]['body']['recipient'] if previous else 'bridge',
                **{k:notes.get(k,'') for k in ('intent_implications','downstream_needs','open_questions')}))
    def read_version(self,data):
        thread=self.w.domain_chat.owned(data.get('conversation'))
        raw=reference(data.get('version'))
        if raw.id!=thread['body']['draft_id']:raise PermissionError('Choose a saved version of this report')
        record=self.store.read(raw,{self.w.domains.scope})
        if record['kind']!='contribution-draft' or record['body'].get('owner')!=self.w.actor or not record['body'].get('working_report'):
            raise PermissionError('Choose your own saved report')
        return dict(ref=asdict(raw),title=record['body']['title'],report=deepcopy(record['body']['working_report']))
    def history(self):
        if not self.w.domains.key:return []
        ids={t['body']['draft_id'] for t in self.w.domain_chat.threads()};result=[]
        for id in ids:
            rows=self.store.db.execute("SELECT id,revision FROM records WHERE id=? AND scope=? ORDER BY revision DESC LIMIT 20",(id,self.w.domains.scope)).fetchall()
            for row in rows:
                r=self.store.read(Ref(row['id'],row['revision']),{self.w.domains.scope});b=r['body']
                if b.get('owner')==self.w.actor and b.get('working_report'):
                    result.append(dict(ref=asdict(r['ref']),section_count=len(b['working_report']['entries']),saved_at=b['working_report']['saved_at']))
        return result
