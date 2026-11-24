"""Local source extraction. No model, network access, or execution of document content."""
import base64
import hashlib
import io
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree as ET

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 120_000
MAX_PDF_PAGES = 100


def extract(data):
    page_spans=[]
    name = data.get('filename') or data.get('title', 'Pasted material')
    if not isinstance(name, str) or not 0 < len(name.strip()) <= 250:
        raise ValueError('Give the source a short descriptive name')
    name = Path(name).name
    if 'content' not in data:
        text = data.get('text')
        if not isinstance(text, str):
            raise ValueError('Paste readable source text')
        raw, parser = text.encode(), 'pasted-text-v1'
    else:
        try:
            raw = base64.b64decode(data['content'], validate=True)
        except (ValueError, TypeError):
            raise ValueError('The file could not be read') from None
        if len(raw) > MAX_BYTES:
            raise ValueError('Use a file under 5 MB, or paste a relevant excerpt')
        ext = Path(name).suffix.lower()
        parser = ext.lstrip('.') + '-text-v1'
        if ext in {'.txt','.md','.csv','.json'}:
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                raise ValueError('Save this text file as UTF-8 or paste its text') from None
        elif ext in {'.docx','.pptx'}:
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    names = ['word/document.xml'] if ext == '.docx' else sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)), key=lambda n:int(re.search(r'slide(\d+)',n)[1]))
                    if not names or sum(z.getinfo(n).file_size for n in names) > 20_000_000:
                        raise ValueError('Document contents are too large or empty')
                    chunks = []
                    for n in names:
                        xml = z.read(n)
                        if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
                            raise ValueError('Unsupported document XML')
                        root = ET.fromstring(xml)
                        chunks.extend(''.join(x.text or '' for x in p.iter() if x.tag.endswith('}t')) for p in root.iter() if p.tag.endswith('}p'))
                    text = '\n'.join(chunks)
            except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError):
                raise ValueError('Could not read this Office document. Paste a relevant excerpt instead') from None
        elif ext == '.pdf':
            try:
                from pypdf import PdfReader
            except ImportError:
                raise ValueError('PDF support needs the updated installation. Paste text for now') from None
            try:
                reader = PdfReader(io.BytesIO(raw))
                if reader.is_encrypted or len(reader.pages) > MAX_PDF_PAGES:
                    raise ValueError('Use an unencrypted PDF of at most 100 pages, or paste a relevant excerpt')
                parts = []
                for page in reader.pages:
                    content=(page.extract_text() or '').replace('\x00','')
                    start=sum(map(len,parts))+2*len(parts)
                    page_spans.append(dict(page=len(parts)+1,start=start,end=start+len(content)))
                    parts.append(content)
                    if sum(map(len, parts)) > MAX_TEXT:
                        raise ValueError('Use a shorter document or paste an excerpt under 120,000 characters')
                text = '\n\n'.join(parts)
            except ValueError:
                raise
            except Exception:
                raise ValueError('Could not extract PDF text. Paste a readable excerpt; scanned pages need OCR elsewhere') from None
        else:
            raise ValueError('Use TXT, Markdown, CSV, JSON, Word, PowerPoint or a text PDF')
    text = text.replace('\x00','')
    leading=len(text)-len(text.lstrip())
    text=text.strip()
    if not text:
        raise ValueError('No readable text found. Scanned images need OCR elsewhere; paste readable text instead')
    if len(text) > MAX_TEXT:
        raise ValueError('Use a shorter document or paste an excerpt under 120,000 characters')
    # The parser strips outer whitespace; retain page offsets against the saved text.
    result={'title': name, 'text': text, 'sha256': hashlib.sha256(raw).hexdigest(), 'parser': parser,
            'original_bytes': len(raw), 'original_retained': False}
    if page_spans:result['page_spans']=[{**p,'start':max(0,p['start']-leading),'end':min(len(text),max(0,p['end']-leading))} for p in page_spans]
    return result
