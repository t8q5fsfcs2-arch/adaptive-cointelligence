"""Private PDF originals and lazily rendered exact pages in the project SQLite store.

Record bodies contain metadata only. Binary originals and page caches never enter
workspace JSON, packet releases, model traces or arbitrary filesystem routes.
"""
import base64
import hashlib
import io
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from dataclasses import asdict

from .core import Ref
from .validation import reference

MAX_BYTES=5*1024*1024
MAX_PAGES=100
RENDERER='poppler-png-1600-v1'


def tools():
    found={name:shutil.which(name) for name in ('pdftoppm','pdftotext')}
    if not all(found.values()):
        raise ValueError('Visual PDF review needs Poppler (pdftoppm and pdftotext) installed on the server. No text-only substitute was used.')
    return found


def run(command):
    try:
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=False)
        if result.returncode:raise ValueError('Could not process this PDF. Use an unencrypted, readable PDF of at most 100 pages.')
    except subprocess.TimeoutExpired:
        raise ValueError('This PDF took too long to render. Export a smaller prototype PDF and retry.') from None


def extract_visual(data):
    from pypdf import PdfReader
    name=Path(str(data.get('filename',''))).name
    if not name or len(name)>250 or Path(name).suffix.lower()!='.pdf':raise ValueError('Choose a prototype PDF')
    try:raw=base64.b64decode(data.get('content',''),validate=True)
    except (ValueError,TypeError):raise ValueError('The PDF could not be read') from None
    if not raw or len(raw)>MAX_BYTES or not raw.lstrip().startswith(b'%PDF-'):raise ValueError('Use a PDF under 5 MB')
    try:
        reader=PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted or not 1<=len(reader.pages)<=MAX_PAGES:raise ValueError()
        for page in reader.pages:
            if not 0<float(page.mediabox.width)<=14400 or not 0<float(page.mediabox.height)<=14400:raise ValueError()
        count=len(reader.pages)
    except Exception:raise ValueError('Use an unencrypted PDF with 1 to 100 normally sized pages') from None
    binaries=tools()
    with tempfile.TemporaryDirectory(prefix='workbench-pdf-') as tmp:
        path=Path(tmp)/'source.pdf';path.write_bytes(raw);path.chmod(0o600)
        text_path=Path(tmp)/'text.txt'
        run([binaries['pdftotext'],'-enc','UTF-8',str(path),str(text_path)])
        if not text_path.exists() or text_path.stat().st_size>480000:raise ValueError('Use a shorter PDF with at most 120,000 text characters')
        text=text_path.read_text().replace('\x00','').strip()
    if len(text)>120000:raise ValueError('Use a shorter PDF with at most 120,000 text characters')
    return dict(title=name,text=text or 'No extractable text. Review the selected PDF page images.',sha256=hashlib.sha256(raw).hexdigest(),parser='visual-pdf-text-v1',original_bytes=len(raw),original_retained=True,visual_pdf=dict(page_count=count,renderer=RENDERER)),raw


def schema(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS visual_pdf_files(
      source_id TEXT,source_revision INTEGER,sha256 TEXT NOT NULL,content BLOB NOT NULL,
      PRIMARY KEY(source_id,source_revision),FOREIGN KEY(source_id,source_revision) REFERENCES records(id,revision))''')
    store.db.execute('''CREATE TABLE IF NOT EXISTS visual_pdf_pages(
      source_id TEXT,source_revision INTEGER,page INTEGER,renderer TEXT,width INTEGER,height INTEGER,
      image_sha256 TEXT NOT NULL,content BLOB NOT NULL,
      PRIMARY KEY(source_id,source_revision,page,renderer),
      FOREIGN KEY(source_id,source_revision) REFERENCES visual_pdf_files(source_id,source_revision))''')


def retain(store,ref,raw):
    schema(store)
    store.db.execute('INSERT INTO visual_pdf_files VALUES (?,?,?,?)',(ref.id,ref.revision,hashlib.sha256(raw).hexdigest(),raw))


def source(workspace,raw):
    workspace.domains.author()
    r=workspace.store.read(reference(raw),{workspace.domains.scope})
    if r['kind']!='source' or r['body'].get('owner')!=workspace.actor or not r['body'].get('visual_pdf'):raise ValueError('Choose a retained PDF from your active domain')
    return r


def page(workspace,raw,number):
    r=source(workspace,raw);ref=r['ref']
    if type(number) is not int or not 1<=number<=r['body']['visual_pdf']['page_count']:raise ValueError('Choose a page within this PDF')
    store=workspace.store
    row=store.db.execute('SELECT * FROM visual_pdf_pages WHERE source_id=? AND source_revision=? AND page=? AND renderer=?',(ref.id,ref.revision,number,RENDERER)).fetchone()
    if not row:
        original=store.db.execute('SELECT * FROM visual_pdf_files WHERE source_id=? AND source_revision=?',(ref.id,ref.revision)).fetchone()
        if not original or hashlib.sha256(original['content']).hexdigest()!=r['body']['sha256']:raise ValueError('The retained PDF is unavailable or failed its integrity check')
        binary=tools()['pdftoppm']
        with tempfile.TemporaryDirectory(prefix='workbench-page-') as tmp:
            input_path=Path(tmp)/'source.pdf';input_path.write_bytes(original['content']);input_path.chmod(0o600)
            prefix=Path(tmp)/'page'
            run([binary,'-f',str(number),'-l',str(number),'-singlefile','-scale-to','1600','-png',str(input_path),str(prefix)])
            output=prefix.with_suffix('.png')
            if not output.exists() or output.stat().st_size>5*1024*1024:raise ValueError('Rendered page is too large or unreadable')
            image=output.read_bytes()
        if image[:8]!=b'\x89PNG\r\n\x1a\n' or len(image)<24:raise ValueError('PDF renderer did not return a usable page image')
        width,height=struct.unpack('>II',image[16:24])
        if not 0<width<=1600 or not 0<height<=1600:raise ValueError('Rendered page dimensions exceed the review limit')
        with store.transaction():
            store.db.execute('INSERT OR IGNORE INTO visual_pdf_pages VALUES (?,?,?,?,?,?,?,?)',(ref.id,ref.revision,number,RENDERER,width,height,hashlib.sha256(image).hexdigest(),image))
        row=store.db.execute('SELECT * FROM visual_pdf_pages WHERE source_id=? AND source_revision=? AND page=? AND renderer=?',(ref.id,ref.revision,number,RENDERER)).fetchone()
    if hashlib.sha256(row['content']).hexdigest()!=row['image_sha256']:raise ValueError('The saved page failed its integrity check')
    return dict(source=asdict(ref),page=number,renderer=RENDERER,width=row['width'],height=row['height'],sha256=row['image_sha256']),bytes(row['content'])


def cached_metadata(workspace,raw,number):
    r=source(workspace,raw)
    row=workspace.store.db.execute('SELECT width,height,image_sha256 FROM visual_pdf_pages WHERE source_id=? AND source_revision=? AND page=? AND renderer=?',(r['ref'].id,r['ref'].revision,number,RENDERER)).fetchone()
    if not row:raise ValueError('The reviewed page image is no longer available. Prepare the review again.')
    return dict(source=asdict(r['ref']),page=number,renderer=RENDERER,width=row['width'],height=row['height'],sha256=row['image_sha256'])
