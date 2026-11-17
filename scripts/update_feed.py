#!/usr/bin/env python3
"""Hot Stove GM live feed.

Runs every 10 minutes on GitHub Actions. Pulls three free sources and updates:
  transactions.json  real-world moves the page applies on load
  news.json          the news feed (newest first)

Sources
  ESPN MLB news JSON   fastest for agreed deals ("reported")
  MLB Trade Rumors RSS rumors, contract terms ("reported")
  MLB Stats API        processed transactions ("official")

Rules
  * Official moves come only from the MLB Stats API.
  * A reported signing is added only when a headline names one club, a player on
    our free-agent board, and agreement language (no "interest", "linked", etc.).
  * Nothing already in transactions.json is changed or removed.
Standard library only.
"""
import json, os, re, sys, unicodedata, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TX, NEWS, DATA = (os.path.join(ROOT, f) for f in ('transactions.json', 'news.json', 'data.json'))
UA = {'User-Agent': 'HotStoveGM-feed/1.0 (+https://fschaeffer16.github.io/hotstove-gm/)'}

MLB_IDS = {108: 'LAA', 109: 'ARI', 110: 'BAL', 111: 'BOS', 112: 'CHC', 113: 'CIN', 114: 'CLE', 115: 'COL', 116: 'DET',
           117: 'HOU', 118: 'KCR', 119: 'LAD', 120: 'WSN', 121: 'NYM', 133: 'ATH', 134: 'PIT', 135: 'SDP', 136: 'SEA',
           137: 'SFG', 138: 'STL', 139: 'TBR', 140: 'TEX', 141: 'TOR', 142: 'MIN', 143: 'PHI', 144: 'ATL', 145: 'CHW',
           146: 'MIA', 147: 'NYY', 158: 'MIL'}
NICK = [('White Sox', 'CHW'), ('Red Sox', 'BOS'), ('Blue Jays', 'TOR'), ('Diamondbacks', 'ARI'), ('D-backs', 'ARI'),
        ('Athletics', 'ATH'), ("A's", 'ATH'), ('Braves', 'ATL'), ('Orioles', 'BAL'), ('Cubs', 'CHC'), ('Reds', 'CIN'),
        ('Guardians', 'CLE'), ('Rockies', 'COL'), ('Tigers', 'DET'), ('Astros', 'HOU'), ('Royals', 'KCR'),
        ('Angels', 'LAA'), ('Dodgers', 'LAD'), ('Marlins', 'MIA'), ('Brewers', 'MIL'), ('Twins', 'MIN'),
        ('Mets', 'NYM'), ('Yankees', 'NYY'), ('Phillies', 'PHI'), ('Pirates', 'PIT'), ('Padres', 'SDP'),
        ('Giants', 'SFG'), ('Mariners', 'SEA'), ('Cardinals', 'STL'), ('Rays', 'TBR'), ('Rangers', 'TEX'),
        ('Nationals', 'WSN')]
NUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
       'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15}
AGREE = re.compile(r'\b(reach|reaches|agree|agrees|agreed|sign|signs|signed|land|lands|finalize|finalized|deal|contract|re-sign|re-signs)\b', re.I)
RUMOR = re.compile(r'\b(interest|interested|linked|eye|eyes|eyeing|among|could|would|should|fits?|best|rumou?rs?|pursu|target|meet|met|talks?|considering|checked in|in on|predict|mailbag|chat|tracker|notes|candidates|ranking|top \d+|why|how|what|which|chance)\b|\?', re.I)


def nmz(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().strip()
    s = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv|v)$', '', s)
    return re.sub(r'[^a-z ]', '', s).strip()


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def teams_in(text):
    found, t = [], text
    for nick, code in NICK:
        if re.search(r'(?<![\w])' + re.escape(nick) + r'(?![\w])', t):
            if code not in found:
                found.append(code)
            t = t.replace(nick, ' ')
    return found


def money(text):
    """(years, total $) from text like '3-year, $52.5M' or 'one-year, $2.25 million'."""
    m = re.search(r'(\d+|' + '|'.join(NUM) + r')[- ]year[s]?,?\s*(?:deal|contract|pact)?\s*(?:worth|for)?\s*\$\s*([\d.]+)\s*(M|MM|million|B|billion)\b', text, re.I)
    if not m:
        return None
    yrs = int(m.group(1)) if m.group(1).isdigit() else NUM[m.group(1).lower()]
    amt = float(m.group(2)) * (1e9 if m.group(3).lower().startswith('b') else 1e6)
    return yrs, amt


# ---------------- sources ----------------
def espn():
    out = []
    d = json.loads(get('https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/news?limit=50'))
    for a in d.get('articles', []):
        link = ((a.get('links') or {}).get('web') or {}).get('href', '')
        out.append({'title': a.get('headline', ''), 'blurb': a.get('description', ''), 'link': link,
                    'time': a.get('published', ''), 'source': 'ESPN'})
    return out


def mlbtr():
    out = []
    root = ET.fromstring(get('https://www.mlbtraderumors.com/feed'))
    for it in root.iter('item'):
        pub = it.findtext('pubDate') or ''
        try:
            t = datetime.strptime(pub, '%a, %d %b %Y %H:%M:%S %z').astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            t = ''
        desc = re.sub(r'<[^>]+>', ' ', it.findtext('description') or '')
        out.append({'title': (it.findtext('title') or '').strip(), 'blurb': re.sub(r'\s+', ' ', desc).strip()[:300],
                    'link': it.findtext('link') or '', 'time': t, 'source': 'MLB Trade Rumors'})
    return out


def parents():
    m = dict(MLB_IDS)
    try:
        d = json.loads(get('https://statsapi.mlb.com/api/v1/teams?sportIds=11,12,13,14,15,16'))
        for t in d.get('teams', []):
            p = t.get('parentOrgId')
            if p in MLB_IDS:
                m[t['id']] = MLB_IDS[p]
    except Exception as e:
        print('teams lookup failed:', e)
    return m


def statsapi(days=4):
    end = datetime.now(timezone(timedelta(hours=-5))).date()
    start = end - timedelta(days=days)
    d = json.loads(get(f'https://statsapi.mlb.com/api/v1/transactions?startDate={start}&endDate={end}'))
    return d.get('transactions', [])


# ---------------- main ----------------
def main():
    T = load(TX, {'moves': []})
    N = load(NEWS, {'items': []})
    D = load(DATA, {})
    P = D.get('players', {})
    fa_names = {nmz(P[i]['n']): P[i] for i in D.get('fa', []) if i in P}
    forty = {c: {nmz(P[i]['n']) for i in ids if i in P} for c, ids in D.get('fortyBy', {}).items()}
    forty['NYM'] = forty.get('NYM', set()) | {nmz(P[i]['n']) for i in D.get('forty', []) if i in P}
    known = {nmz(p['n']) for p in P.values()}
    moves = T.setdefault('moves', [])
    have_sid = set(T.get('seen_sids', [])) | {m.get('sid') for m in moves if m.get('sid')}
    have_np = {(nmz(m.get('name', '')), m.get('type')) for m in moves if m.get('name')}
    for m in moves:
        for p in m.get('players', []) or []:
            have_np.add((nmz(p['name']), m.get('type')))
    added, news_new = [], []
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # -------- official: MLB Stats API --------
    try:
        org = parents()
        for t in statsapi():
            sid, code = t.get('id'), t.get('typeCode')
            if not sid or sid in have_sid or 'person' not in t:
                continue
            name = t['person'].get('fullName', '')
            to_id, fr_id = (t.get('toTeam') or {}).get('id'), (t.get('fromTeam') or {}).get('id')
            to, fr = org.get(to_id), org.get(fr_id)
            to_mlb = to_id in MLB_IDS
            desc = t.get('description', '')
            date = (t.get('date') or t.get('effectiveDate') or now)[:10]
            mv = None
            if code == 'TR' and to and fr and to != fr:
                mv = {'type': 'trade', 'players': [{'name': name, 'from': fr, 'to': to, 'forty': nmz(name) in forty.get(fr, set()), 'pos': '?'}]}
            elif code == 'CLW' and to:
                mv = {'type': 'claim', 'players': [{'name': name, 'from': fr or 'FA', 'to': to, 'forty': True, 'pos': '?'}]}
            elif code in ('SFA', 'SGN', 'SIGN') and to:
                minor = (not to_mlb) or re.search(r'minor league', desc, re.I)
                mv = {'type': 'sign_minor' if minor else 'sign', 'name': name, 'team': to, 'pos': '?'}
                if not minor:
                    mv['forty'] = True
            elif code == 'DES' and (to or fr):
                mv = {'type': 'dfa', 'name': name, 'team': to or fr}
            elif code == 'OUT' and (to or fr):
                mv = {'type': 'outright', 'name': name, 'team': fr or to}
            elif code == 'REL' and (to or fr):
                mv = {'type': 'release', 'name': name, 'team': fr or to}
            elif code == 'SE' and to:
                mv = {'type': 'select', 'name': name, 'team': to, 'pos': '?'}
            elif code == 'RET' and (to or fr):
                mv = {'type': 'retire', 'name': name, 'team': to or fr}
            if not mv:
                continue
            # only moves that touch our database: a tracked player, or an MLB club at the MLB level
            mlb_level = to_mlb or fr_id in MLB_IDS
            if nmz(name) not in known and not (mlb_level and mv['type'] in ('trade', 'claim', 'sign', 'select')) \
                    and not (mlb_level and mv['type'] == 'sign_minor' and re.search(r'spring training', desc, re.I)):
                have_sid.add(sid)
                continue
            key = (nmz(name), mv['type'])
            mv.update({'date': date, 'summary': desc, 'src': 'MLB Stats API', 'sid': sid, 'status': 'official'})
            have_sid.add(sid)
            if key in have_np:
                # already reported: mark the earlier entry official instead of adding a duplicate
                for m in moves:
                    if (nmz(m.get('name', '')), m.get('type')) == key:
                        m['status'] = 'official'
                        m.setdefault('sid', sid)
                continue
            moves.append(mv)
            have_np.add(key)
            added.append(mv)
            news_new.append({'title': desc, 'link': '', 'time': now, 'source': 'MLB transactions', 'kind': 'official',
                             'teams': [x for x in {to, fr} if x]})
    except Exception as e:
        print('statsapi failed:', e)

    # -------- reported: ESPN + MLB Trade Rumors --------
    items = []
    for fn in (espn, mlbtr):
        try:
            items += fn()
        except Exception as e:
            print(fn.__name__, 'failed:', e)
    for it in items:
        it['teams'] = teams_in(it['title'])
        it['kind'] = 'news'
        title = it['title']
        if not AGREE.search(title) or RUMOR.search(title) or len(it['teams']) != 1:
            continue
        who = [n for n in fa_names if n and re.search(r'\b' + re.escape(n) + r'\b', nmz(title))]
        if len(who) != 1:
            continue
        p, team = fa_names[who[0]], it['teams'][0]
        minor = re.search(r'minor[- ]league', title + ' ' + it.get('blurb', ''), re.I)
        typ = 'sign_minor' if minor else 'sign'
        if (who[0], typ) in have_np or (who[0], 'sign') in have_np:
            it['kind'] = 'report'
            continue
        mv = {'date': (it['time'] or now)[:10], 'type': typ, 'summary': title, 'name': p['n'], 'team': team,
              'pos': p.get('pos', '?'), 'src': it['source'] + (' ' + it['link'] if it['link'] else ''), 'status': 'reported'}
        if not minor:
            mv['forty'] = True
            mm = money(title) or money(it.get('blurb', ''))
            if mm:
                yrs, tot = mm
                aav = round(tot / yrs)
                y0 = 2027
                mv['contract'] = {'aav': aav, 'desc': f"{yrs} yr, ${tot/1e6:g}M ({y0}-{str(y0+yrs-1)[2:]})",
                                  'yrs': {**{str(y0 + i): aav for i in range(yrs)}, str(y0 + yrs): 'FREE AGENT'}}
        moves.append(mv)
        have_np.add((who[0], typ))
        added.append(mv)
        it['kind'] = 'report'

    # -------- news feed --------
    seen = {i.get('link') or i.get('title') for i in N.get('items', [])}
    n_before = len(seen)
    for it in news_new + items:
        k = it.get('link') or it.get('title')
        if k and k not in seen:
            seen.add(k)
            N.setdefault('items', []).append({x: it.get(x, '') for x in ('title', 'blurb', 'link', 'time', 'source', 'kind', 'teams')})
    N['items'] = sorted(N.get('items', []), key=lambda i: i.get('time', ''), reverse=True)[:300]
    if len(seen) != n_before or added or 'updated' not in N:
        N['updated'] = now  # only touch the file when something is new, so quiet runs make no commit

    T['seen_sids'] = sorted(x for x in have_sid if isinstance(x, int))[-4000:]  # remember skipped MLB ids so they're not re-checked
    if added:
        T['updated'] = datetime.now(timezone(timedelta(hours=-5))).strftime('%Y-%m-%d')
        T['live'] = now
    with open(TX, 'w', encoding='utf-8') as f:
        json.dump(T, f, indent=1, ensure_ascii=False)
    with open(NEWS, 'w', encoding='utf-8') as f:
        json.dump(N, f, indent=1, ensure_ascii=False)
    print(f'{len(added)} moves added; {len(N["items"])} news items')
    for m in added:
        print(' ', m.get('status'), m['type'], m.get('name') or m['players'][0]['name'], m.get('team') or '')


if __name__ == '__main__':
    sys.exit(main())
