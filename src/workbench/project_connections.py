"""Explicit operator-only, lossless project copies between local catalogs.

No credentials, private chat sidecars or account memberships are copied. Original
stores stay untouched. Connection receipts identify the source; reruns never
replace working copies or merge divergent histories by title.
"""
from contextlib import contextmanager,closing
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid5, NAMESPACE_URL
from .projects import Projects
from .decisions import now


@contextmanager
def readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:yield db
    finally:db.close()


def fingerprint(db):
    result=hashlib.sha256()
    for table in ('records','dependencies','packets'):
        rows=sorted(db.execute('SELECT * FROM '+table).fetchall(),key=lambda r:json.dumps(r,sort_keys=True))
        result.update(json.dumps([table,rows],sort_keys=True).encode())
    return result.hexdigest()


def copy_database(source,target):
    with readonly(source) as src,closing(sqlite3.connect(target)) as dest:
        src.backup(dest)
        if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('The source database did not pass integrity checks.')
        return fingerprint(dest)


def connect(catalog,source_catalog,label):
    source_catalog=Path(source_catalog).resolve()
    if source_catalog==catalog.catalog.resolve():raise ValueError('Choose a different source catalog.')
    if not isinstance(label,str) or not 0<len(label.strip())<=100:raise ValueError('Name the source environment.')
    source_key=hashlib.sha256(str(source_catalog).encode()).hexdigest()
    result=[]
    with readonly(source_catalog) as source:
        source.row_factory=sqlite3.Row
        for raw in source.execute('SELECT * FROM projects ORDER BY created_at,id'):
            row=dict(raw)
            with readonly(row['path']) as project:
                if not project.execute("SELECT 1 FROM records WHERE kind='project' LIMIT 1").fetchone():
                    result.append(dict(source_id=row['id'],status='empty-skipped'));continue
                digest=fingerprint(project)
            with catalog.db() as db:old=db.execute('SELECT * FROM project_connections WHERE source_key=? AND source_id=?',(source_key,row['id'])).fetchone()
            if old:
                result.append(dict(source_id=row['id'],project_id=old['target_id'],status='already-connected',source_changed=old['source_digest']!=digest));continue
            target_id='connected-'+uuid5(NAMESPACE_URL,source_key+':'+row['id']).hex
            current=catalog.new_path();created=[current]
            try:
                digest=copy_database(row['path'],current);history=[]
                for old_version in source.execute('SELECT * FROM saved_versions WHERE project_id=? ORDER BY saved_at,id',(row['id'],)):
                    target=catalog.new_path();created.append(target);copy_database(old_version['path'],target)
                    history.append((uuid5(NAMESPACE_URL,source_key+':history:'+old_version['id']).hex,target_id,str(target),old_version['reason'],old_version['saved_at']))
                with catalog.db() as db:
                    db.execute('INSERT INTO projects VALUES (?,?,?,?)',(target_id,str(current),row['version'],row['created_at']))
                    catalog.assign_reference(db,target_id)
                    db.executemany('INSERT INTO saved_versions VALUES (?,?,?,?,?)',history)
                    db.execute('INSERT INTO project_connections VALUES (?,?,?,?,?,?,?)',(source_key,row['id'],target_id,label.strip(),row['version'],digest,now()))
                result.append(dict(source_id=row['id'],project_id=target_id,status='connected',generation=row['version'],saved_versions=len(history)))
            except Exception:
                for path in created:path.unlink(missing_ok=True)
                raise
    return result


def main():
    parser=argparse.ArgumentParser(description='Copy saved local projects into this Workbench without changing their source stores.')
    parser.add_argument('--target',type=Path,required=True,help='Current Workbench anchor database')
    parser.add_argument('--source-catalog',type=Path,required=True)
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    print(json.dumps(connect(Projects(args.target),args.source_catalog,args.label),indent=2))

if __name__=='__main__':main()
