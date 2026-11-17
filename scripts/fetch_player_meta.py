#!/usr/bin/env python3
"""Fetch birth date, draft year and birth country for every player in all 30 organizations
(MLB club + every affiliate, including the complex and Dominican Summer Leagues) from the MLB Stats API.
Writes player_meta.json, which the app uses for Rule 5 eligibility and team-control math.
Standard library only. Runs on GitHub Actions (weekly + on demand)."""
import json, os, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {'User-Agent': 'HotStoveGM-meta/1.0 (+https://fschaeffer16.github.io/hotstove-gm/)'}
MLB_IDS = {108: 'LAA', 109: 'ARI', 110: 'BAL', 111: 'BOS', 112: 'CHC', 113: 'CIN', 114: 'CLE', 115: 'COL', 116: 'DET',
           117: 'HOU', 118: 'KCR', 119: 'LAD', 120: 'WSN', 121: 'NYM', 133: 'ATH', 134: 'PIT', 135: 'SDP', 136: 'SEA',
           137: 'SFG', 138: 'STL', 139: 'TBR', 140: 'TEX', 141: 'TOR', 142: 'MIN', 143: 'PHI', 144: 'ATL', 145: 'CHW',
           146: 'MIA', 147: 'NYY', 158: 'MIL'}
SEASON = int(os.environ.get('META_SEASON', '2026'))

def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            print('retry', url, e); time.sleep(2 + 3 * i)
    return {}

def main():
    teams = dict((k, v) for k, v in MLB_IDS.items())
    aff = get(f'https://statsapi.mlb.com/api/v1/teams?sportIds=11,12,13,14,16&season={SEASON}')
    for t in aff.get('teams', []):
        if t.get('parentOrgId') in MLB_IDS:
            teams[t['id']] = MLB_IDS[t['parentOrgId']]
    out, seen = [], set()
    for tid, org in sorted(teams.items()):
        for rtype in (['fullSeason', '40Man'] if tid in MLB_IDS else ['fullSeason']):
            d = get(f'https://statsapi.mlb.com/api/v1/teams/{tid}/roster?rosterType={rtype}&season={SEASON}&hydrate=person')
            for e in d.get('roster', []):
                p = e.get('person') or {}
                pid = p.get('id')
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                out.append({'id': pid, 'n': p.get('fullName', ''), 'o': org, 'b': p.get('birthDate'),
                            'dy': p.get('draftYear'), 'c': p.get('birthCountry'),
                            'pos': (p.get('primaryPosition') or {}).get('abbreviation'),
                            'debut': p.get('mlbDebutDate')})
            time.sleep(0.15)
    if len(out) < 3000:
        print('Too few players fetched (%d); keeping the old file.' % len(out)); return 0
    meta = {'season': SEASON, 'source': 'MLB Stats API (personal, non-commercial use)', 'count': len(out),
            'players': sorted(out, key=lambda x: (x['o'], x['n']))}
    with open(os.path.join(ROOT, 'player_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    print('wrote', len(out), 'players from', len(teams), 'teams')
    return 0

if __name__ == '__main__':
    sys.exit(main())
