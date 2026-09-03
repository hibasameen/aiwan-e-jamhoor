#!/usr/bin/env python3
"""
Convert the scraped results_{1977,1985,1988} CSVs into the window.RESULTS schema
used by map.html, and emit per-year headline stats for the ELEC context cards.

Output: data/_map_inject/results_historic.json
  { "RESULTS": {year:{NA:{name,prov,wp,wn,wv,ws,reg,to,mov,nc,cands:[{n,p,v,s}]}}},
    "STATS":   {year:{polled,cands,tight}} }
"""
import csv, json, os, collections

YEARS = {'1977': 200, '1985': 207, '1988': 207}

def province(n, seats):
    # settled KP 1-26, FATA 27-34, ICT 35, Punjab 36-150, then Sindh / Balochistan
    if n <= 26:  return 'Khyber Pakhtunkhwa'
    if n <= 34:  return 'FATA'
    if n == 35:  return 'Islamabad Capital Territory'
    if n <= 150: return 'Punjab'
    if seats == 200:
        return 'Sindh' if n <= 193 else 'Balochistan'
    return 'Sindh' if n <= 196 else 'Balochistan'

def main():
    RESULTS, STATS = {}, {}
    for year, seats in YEARS.items():
        cons = {r['na']: r for r in csv.DictReader(open(f'data/results_{year}/na_{year}_constituency.csv'))}
        cands = collections.defaultdict(list)
        for r in csv.DictReader(open(f'data/results_{year}/na_{year}_candidates.csv')):
            cands[r['na']].append(r)
        yobj, total_cands, tight = {}, 0, 0
        for na, r in cons.items():
            n = int(na.split('-')[1])
            clist = sorted(cands[na], key=lambda x: (x['votes'] != '', int(x['votes']) if x['votes'] else 0), reverse=True)
            votes = [int(c['votes']) for c in clist if c['votes']]
            tot = sum(votes) if votes else 0
            def party(p):  # 1985 was non-party -> all independents
                return p or 'Independent'
            def share(v):
                return round(v / tot * 100, 1) if (tot and v != '') else None
            cand_objs = [{'n': c['candidate_name'], 'p': party(c['party']),
                          'v': int(c['votes']) if c['votes'] else None,
                          's': share(int(c['votes'])) if c['votes'] else None} for c in clist]
            wv = int(r['winner_votes']) if r['winner_votes'] else None
            ruv = int(r['runnerup_votes']) if r['runnerup_votes'] else None
            ws = round(wv / tot * 100, 1) if (wv and tot) else None
            mov = round((wv - ruv) / tot * 100, 1) if (wv and ruv and tot) else None
            if mov is not None and mov < 5:
                tight += 1
            total_cands += len(cand_objs)
            yobj[na] = {'name': r['constituency_name'] or na, 'prov': province(n, seats),
                        'wp': party(r['winner_party']), 'wn': r['winner_name'],
                        'wv': wv, 'ws': ws, 'reg': None, 'to': None, 'mov': mov,
                        'nc': len(cand_objs), 'cands': cand_objs}
        RESULTS[year] = yobj
        STATS[year] = {'polled': f'{len(yobj)} of {seats}', 'cands': f'{total_cands:,}', 'tight': str(tight)}
        print(f'{year}: {len(yobj)} seats, {total_cands} cand rows, {tight} tight (<5%)')

    os.makedirs('data/_map_inject', exist_ok=True)
    json.dump({'RESULTS': RESULTS, 'STATS': STATS},
              open('data/_map_inject/results_historic.json', 'w'), separators=(',', ':'))
    print('wrote data/_map_inject/results_historic.json')

if __name__ == '__main__':
    main()
