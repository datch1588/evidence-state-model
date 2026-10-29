"""SSVC Exploitation from CISA Vulnrichment: value at forecast time vs current value.

Reproduces the check in Section 6 of the article: vulnerabilities published
01.01-13.06.2026 that entered the KEV catalog (version 2026.10.15) within
90 days after the forecast time t = publication + 7 days.

    python3 vulnrichment_history.py fetch DATA_DIR   # downloads ~300 small JSON files
    python3 vulnrichment_history.py check DATA_DIR [--list]

Sources (all public):
  KEV catalog 2026.10.15 - github.com/cisagov/kev-data, commit 7923b5f7040256ca9887d268b4c2a02453a2ff30
  current CVE records    - github.com/CVEProject/cvelistV5, commit 728adf1c (15.10.2026)
  records at time t      - cvelistV5 hourly release tags cve_YYYY-MM-DD_HH00Z: the latest tag
                           strictly earlier than t (if no release was made in that hour,
                           the previous hour is tried, up to 48 hours back)

Standard library only.
"""
import glob
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

KEV_URL = ('https://raw.githubusercontent.com/cisagov/kev-data/'
           '7923b5f7040256ca9887d268b4c2a02453a2ff30/known_exploited_vulnerabilities.json')
CVELIST = 'https://raw.githubusercontent.com/CVEProject/cvelistV5/{ref}/cves/{y}/{d}/{cid}.json'
CURRENT_REF = '728adf1c'
A = datetime(2026, 1, 1, tzinfo=timezone.utc)
B = datetime(2026, 6, 14, tzinfo=timezone.utc)   # publication date before 14.06, i.e. up to 13.06
LEAD = timedelta(days=7)                         # forecast time t = publication + 7 days
HORIZON = timedelta(days=90)                     # event: t < KEV dateAdded <= t + 90 days


def parse_time(s):
    if not s:
        return None
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def record_url(ref, cid):
    _, y, n = cid.split('-')
    return CVELIST.format(ref=ref, y=y, d=f'{int(n) // 1000}xxx', cid=cid)


def get(url, path):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
    with open(path, 'wb') as f:
        f.write(data)
    return True


def exploitation(record):
    """Exploitation value from the CISA-ADP SSVC block, or None if there is no block."""
    ex = None
    for a in record.get('containers', {}).get('adp', []) or []:
        if a.get('providerMetadata', {}).get('shortName') != 'CISA-ADP':
            continue
        for mt in a.get('metrics', []) or []:
            o = mt.get('other', {})
            if o.get('type') == 'ssvc':
                for opt in o['content'].get('options', []):
                    ex = opt.get('Exploitation', ex)
    return ex


def load_kev(data_dir):
    kev = json.load(open(os.path.join(data_dir, 'kev.json'), encoding='utf-8'))
    assert kev['catalogVersion'] == '2026.10.15', kev['catalogVersion']
    return {v['cveID']: datetime.fromisoformat(v['dateAdded']).replace(tzinfo=timezone.utc)
            for v in kev['vulnerabilities']}


def events(data_dir, kev):
    """(cve, publication time, forecast time t, KEV date) for every event."""
    out = []
    for f in sorted(glob.glob(os.path.join(data_dir, 'current', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))['cveMetadata']
        d0 = parse_time(m.get('datePublished'))
        if m.get('state') != 'PUBLISHED' or d0 is None or not (A <= d0 < B):
            continue
        cid = m['cveId']
        t = d0 + LEAD
        if t < kev[cid] <= t + HORIZON:
            out.append((cid, d0, t, kev[cid]))
    return out


def fetch(data_dir):
    for sub in ('current', 'at_t'):
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)
    get(KEV_URL, os.path.join(data_dir, 'kev.json'))
    kev = load_kev(data_dir)
    # An event needs KEV dateAdded > t >= 08.01.2026, so older KEV entries cannot be events.
    recent = sorted(c for c, d in kev.items() if d > A + LEAD)
    for cid in recent:
        if not get(record_url(CURRENT_REF, cid), os.path.join(data_dir, 'current', cid + '.json')):
            print('no current record:', cid)
    tags = {}
    for cid, d0, t, _ in events(data_dir, kev):
        hour = t.replace(minute=0, second=0, microsecond=0)
        if hour == t:                     # the tag must be strictly earlier than t
            hour -= timedelta(hours=1)
        for back in range(49):
            tag = 'cve_' + (hour - timedelta(hours=back)).strftime('%Y-%m-%d_%H') + '00Z'
            if get(record_url(tag, cid), os.path.join(data_dir, 'at_t', cid + '.json')):
                tags[cid] = tag
                break
        else:
            print('no record at t:', cid)
    with open(os.path.join(data_dir, 'tags_used.json'), 'w', encoding='utf-8') as f:
        json.dump(tags, f, indent=1, sort_keys=True)
    print(f'KEV entries added after 08.01.2026: {len(recent)}; events: {len(tags)}')


def check(data_dir, listing=False):
    kev = load_kev(data_dir)
    ev = events(data_dir, kev)
    at_t, now, rows = Counter(), Counter(), []
    for cid, d0, t, k in ev:
        p = os.path.join(data_dir, 'at_t', cid + '.json')
        x_t = exploitation(json.load(open(p, encoding='utf-8'))) if os.path.exists(p) else 'no record'
        x_now = exploitation(json.load(open(os.path.join(data_dir, 'current', cid + '.json'), encoding='utf-8')))
        at_t[str(x_t)] += 1
        now[str(x_now)] += 1
        rows.append((cid, d0.date().isoformat(), k.date().isoformat(), str(x_t), str(x_now)))
    print('events (published 01.01-13.06.2026, KEV 2026.10.15 within 90 days after t = publication + 7 days):', len(ev))
    print('SSVC Exploitation at t (None = no SSVC block):', dict(sorted(at_t.items())))
    print('SSVC Exploitation now (cvelistV5 commit 728adf1c):', dict(sorted(now.items())))
    if listing:
        print('cve, published, KEV dateAdded, Exploitation at t, Exploitation now')
        for r in sorted(rows, key=lambda z: (z[1], z[0])):
            print(*r, sep=', ')


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('fetch', 'check'):
        sys.exit(__doc__)
    if sys.argv[1] == 'fetch':
        fetch(sys.argv[2])
    else:
        check(sys.argv[2], '--list' in sys.argv[3:])
