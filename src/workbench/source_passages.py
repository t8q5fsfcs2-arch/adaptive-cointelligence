"""Addressable source excerpts. Models select IDs; code supplies the exact quotation."""

def source_with_passages(source):
    text = source['text']
    passages = []
    cursor = 0
    while cursor < len(text):
        end = min(cursor + 900, len(text))
        if end < len(text):
            boundary = text.rfind('\n', cursor + 200, end)
            if boundary < 0:
                boundary = text.rfind(' ', cursor + 400, end)
            if boundary >= 0:
                end = boundary + 1
        raw = text[cursor:end]
        if raw.strip():
            start = cursor + len(raw) - len(raw.lstrip())
            stop = end - len(raw) + len(raw.rstrip())
            passages.append(dict(id=f"{source['id']}@{source['ref']['revision']}:p{len(passages)+1}",
                                 text=text[start:stop], start=start, end=stop))
        cursor = end
    return {**{k:v for k,v in source.items() if k != 'text'}, 'passages': passages}


def passage_citations(sources):
    return {p['id']: dict(source_id=s['id'], quote=p['text'], start=p['start'], end=p['end'],
                          source_title=s['title'], source_ref=s['ref'], passage_id=p['id'])
            for s in sources for p in s['passages']}
