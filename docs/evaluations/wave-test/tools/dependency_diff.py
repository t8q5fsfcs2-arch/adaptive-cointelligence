"""Deterministic dependency-difference report over a graph snapshot. No model involved.
Rules:
- Signature of X for group G: (relation, conditions, use, pinned revision) of every link
  from G's latest records to X.
- Conflict: two groups link to the same X with different non-empty conditions, or one
  group's link is pinned to an older revision of X than the latest.
- Mapping conflict: two groups map terms 'same-as' to one enterprise concept with
  different conditions.
- Revision skew: any current link or packet ref pinned to an older revision.
- Propagation: everything that links (directly or transitively) to a block with an open
  challenge, plus packets that pin it."""
import json, sys, collections
g = json.load(open(sys.argv[1]))
latest = {r['id']: r['revisions'][-1] for r in g['records']}
lrev = {i: r['rev'] for i, r in latest.items()}
out = []
links = [(i, r['group'], l) for i, r in latest.items() for l in r.get('links', [])]

out.append('# Dependency difference report (computed)\n')
out.append('## Shared identifiers: signatures by group')
by_target = collections.defaultdict(lambda: collections.defaultdict(list))
for src, grp, l in links:
    by_target[l['target']][grp].append((src, l))
for x, groups in sorted(by_target.items()):
    if len(groups) < 2: continue
    out.append(f'\n### {x} (latest rev {lrev.get(x)})')
    conds = {}
    for grp, items in groups.items():
        for src, l in items:
            out.append(f"- {grp}: {src} --{l['relation']}--> {x} rev {l['target_rev']}; conditions: {l['conditions'] or '(none)'}; use: {l['use'] or '(none)'}")
            if l['conditions']: conds.setdefault(grp, set()).add(l['conditions'])
    distinct = {c for s in conds.values() for c in s}
    if len(conds) >= 2 and len(distinct) >= 2:
        out.append(f'- **Classification: CONFLICT (scope or conditions differ across groups: {sorted(distinct)})**')
    elif any(l['target_rev'] < lrev.get(x, 0) for its in groups.values() for _, l in its):
        out.append('- **Classification: CONFLICT (revision skew)**')
    else:
        uses = {l['use'] for its in groups.values() for _, l in its if l['use']}
        out.append('- Classification: ' + ('COMPLEMENT (different uses: ' + ', '.join(sorted(uses)) + ')' if len(uses) > 1 else 'AGREEMENT'))

out.append('\n## Meaning mappings to enterprise concepts')
maps = collections.defaultdict(list)
for src, grp, l in links:
    if l['relation'] == 'same-as': maps[l['target']].append((grp, src, l['conditions']))
for c, ms in maps.items():
    for grp, src, cond in ms: out.append(f'- {c}: {grp} term {src} same-as, conditions: {cond}')
    if len({m[2] for m in ms}) > 1 and len({m[0] for m in ms}) > 1:
        out.append(f'- **MAPPING CONFLICT on {c}: groups map same-as under different conditions; enterprise queries will merge different meanings.**')

out.append('\n## Revision skew (current work pinned to superseded revisions)')
for src, grp, l in links:
    if l['target_rev'] < lrev.get(l['target'], 0):
        out.append(f"- {src} ({grp}) uses {l['target']} rev {l['target_rev']}; latest is rev {lrev[l['target']]} ({latest[l['target']]['date']}).")
for p in g['packets']:
    for t, rv in p['refs']:
        if rv < lrev.get(t, 0):
            out.append(f"- Packet {p['id']} (resolved {p['resolved']}) pins {t} rev {rv}; latest is rev {lrev[t]} ({latest[t]['date']}).")

out.append('\n## Propagation from open challenges')
DEPENDS = {'supported-by','rests-on','informed-by','implements','depends-on','approves'}
rev_edges = collections.defaultdict(set)
for src, grp, l in links:
    if l['relation'] in DEPENDS: rev_edges[l['target']].add(src)
for i, r in latest.items():
    if r['kind'] == 'challenge' and r.get('status') == 'open':
        for l in r['links']:
            if l['relation'] != 'challenges': continue
            x = l['target']; seen = {}; frontier = [(x, 0)]
            while frontier:
                n, d = frontier.pop(0)
                for s in sorted(rev_edges[n]):
                    if s not in seen and s != i:
                        seen[s] = d + 1; frontier.append((s, d + 1))
            out.append(f'\n{i} challenges {x} ({l["conditions"]}). Dependents:')
            for s, d in sorted(seen.items(), key=lambda kv: kv[1]):
                via = [ll['relation'] for ll in latest[s].get('links', []) if ll['target'] in ([x] if d == 1 else list(seen))]
                out.append(f"- {'direct' if d == 1 else 'indirect (depth %d)' % d}: {s} ({latest[s]['group']}, {latest[s]['kind']})")
            for p in g['packets']:
                if any(t == x for t, _ in p['refs']): out.append(f"- packet: {p['id']}")

out.append('\n## Revision history (lineage)')
for r in g['records']:
    if len(r['revisions']) > 1:
        out.append(f"\n### {r['id']}")
        for v in r['revisions']:
            extra = v.get('change_reason') or v.get('changed_by') or v.get('interpretation') or ''
            out.append(f"- rev {v['rev']} ({v['date']}): {v['text']}" + (f' [basis/reason: {extra}]' if extra else ''))
print('\n'.join(out))
