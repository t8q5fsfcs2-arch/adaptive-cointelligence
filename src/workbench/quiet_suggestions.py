"""Quiet AI partner suggestions (D011): a person's own switch and dismissals.

The suggestions themselves are the ones the AI partner already returns with each
reply and saves in the review of that reply. Nothing here calls a model or
creates a suggestion. This keeps only two private facts per person and team:
whether they want suggestions surfaced, and which ones they dismissed.
"""
from dataclasses import asdict

from .core import StaleBasis

KIND = 'suggestion-preferences'
KEEP = 400


class QuietSuggestions:
    def __init__(self, w):
        self.w = w
        self.store = w.store
        self.domain = w.domains

    def _id(self):
        return f'SUGPREF-{self.domain.key}-{self.w.actor}'

    def _latest(self):
        row = self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 1', (self._id(),)).fetchone()
        return self.store.latest(self._id(), {self.domain.scope}) if row else None

    def state(self):
        if not self.domain.key or self.w.actor not in self.domain.profile()['config']['authors']:
            return None
        record = self._latest()
        body = record['body'] if record else dict(enabled=True, dismissed=[])
        return dict(ref=asdict(record['ref']) if record else None, enabled=body['enabled'], dismissed=body['dismissed'])

    def _save(self, data, change):
        self.domain.author()
        with self.store.transaction():
            record = self._latest()
            expected = asdict(record['ref']) if record else None
            if data.get('expected') != expected:
                raise StaleBasis('Your suggestion settings changed in another tab. Reopen and try again.')
            body = dict(record['body']) if record else dict(owner=self.w.actor, enabled=True, dismissed=[])
            change(body)
            ref = self.store.put(self._id(), KIND, self.domain.scope, body, record['ref'].revision if record else 0)
        return asdict(ref)

    def toggle(self, data):
        enabled = data.get('enabled')
        if not isinstance(enabled, bool):
            raise ValueError('Turn quiet suggestions on or off.')
        ref = self._save(data, lambda body: body.update(enabled=enabled))
        return dict(message='Quiet suggestions are on.' if enabled else 'Quiet suggestions are off. Your AI partner still answers when you ask.', ref=ref)

    def dismiss(self, data):
        items = data.get('items')
        if not isinstance(items, list) or not items or len(items) > 40:
            raise ValueError('Choose the suggestions to dismiss.')
        clean = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('report'), str) or type(item.get('index')) is not int:
                raise ValueError('Choose the suggestions to dismiss.')
            try:
                report = self.store.latest(item['report'], {self.domain.scope})
            except PermissionError:
                raise ValueError('Choose one of your own suggestions.')
            if report['kind'] != 'domain-chat-review' or report['body']['owner'] != self.w.actor:
                raise PermissionError('Dismiss only suggestions on your own work.')
            output = report['body']['output']
            if not 0 <= item['index'] < len(output.get('findings') or output.get('suggestions') or []):
                raise ValueError('Choose one of the displayed suggestions.')
            clean.append(dict(report=item['report'], index=item['index']))

        def change(body):
            kept = list(body['dismissed'])
            for item in clean:
                if item not in kept:
                    kept.append(item)
            body['dismissed'] = kept[-KEEP:]
        ref = self._save(data, change)
        return dict(message='Dismissed.' if len(clean) == 1 else f'{len(clean)} suggestions dismissed.', ref=ref)
