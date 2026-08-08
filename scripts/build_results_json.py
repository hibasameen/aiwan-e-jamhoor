#!/usr/bin/env python3
"""
Build results_all.json — per-year, per-constituency results powering the map app.

Structure: { "2008": { "NA-1": {name, prov, wp (winning party), wn (winner name),
wv (votes), ws (share %), reg (registered), to (turnout %), mov (margin %),
nc (n candidates), cands: [top-6 {n,p,v,s}] }, ... }, "2013": ..., "2018": ..., "2024": ... }

Sources:
- 2008/2013: colincookman/pakistan_elections  (candidate + constituency CSVs; GE-day
  rows only — election_type == "General Election"; supplementary polls for postponed
  seats are labelled By-Election by Cookman and are excluded).
- 2018:      colincookman/pakistan_election_results_2018 (270 contested; NA-60 &
  NA-103 postponed).
- 2024:      data/results_2024/*.csv scraped from ElectionPakistani (Form-47-based,
  unofficial; see that folder's SOURCES.md). Registered/turnout not available.
  Shares computed over total tabulated candidate votes.

Data notes handled here:
- Cookman candidate file uses m/d/yy dates; constituency file uses ISO dates.
- 2008 constituency file contains a duplicated NA-230 row (dropped).
- Party names differ across vintages ("Pakistan Muslim League (Nawaz)" vs "(N)");
  harmonisation to display categories happens in the app (PARTY_CAT), not here.
- 2024 party abbreviations are expanded to full names via PARTY_FULL.
"""
import pandas as pd, json

def top6(cc, name_col, party_col, votes_col, share_col=None, total=None):
    out = []
    for _, x in cc.head(6).iterrows():
        v = None if pd.isna(x[votes_col]) else int(x[votes_col])
        if share_col is not None:
            s = None if pd.isna(x[share_col]) else round(float(x[share_col]) * 100, 1)
        else:
            s = None if (v is None or not total) else round(100 * v / total, 1)
        out.append({'n': x[name_col], 'p': x[party_col], 'v': v, 's': s})
    return out

def year_0813(cand, cons, cdate, sdate):
    c = cand[(cand['assembly'] == 'National') & (cand['election_date'] == cdate)
             & (cand['election_type'] == 'General Election')].copy()
    k = cons[(cons['assembly'] == 'National') & (cons['election_date'] == sdate)
             & (cons['election_type'] == 'General Election')].drop_duplicates('constituency_number')
    c = c.drop_duplicates(['constituency_number', 'candidate_name', 'candidate_votes'])
    yd = {}
    for _, r in k.iterrows():
        num = r['constituency_number']
        cc = c[c['constituency_number'] == num].sort_values('candidate_votes', ascending=False)
        yd[num] = {'name': r['constituency_name'], 'prov': r['province'],
            'wp': r['win_party'], 'wn': r['win_name'],
            'wv': None if pd.isna(r['win_votes']) else int(r['win_votes']),
            'ws': None if pd.isna(r['win_pct']) else round(float(r['win_pct']) * 100, 1),
            'reg': None if pd.isna(r['voter_reg']) else int(r['voter_reg']),
            'to': None if pd.isna(r['turnout']) else round(float(r['turnout']) * 100, 1),
            'mov': None if pd.isna(r['MOV_pct']) else round(float(r['MOV_pct']) * 100, 1),
            'nc': len(cc), 'cands': top6(cc, 'candidate_name', 'candidate_party',
                                         'candidate_votes', 'candidate_share')}
    return yd

def year_2018():
    k = pd.read_csv('data/pakistan_election_results_2018/pk_constituency_data_2018.csv', low_memory=False)
    c = pd.read_csv('data/pakistan_election_results_2018/pk_candidate_data_2018.csv', low_memory=False)
    kn, cn = k[k['assembly'] == 'National'], c[c['assembly'] == 'National']
    yd = {}
    for _, r in kn.iterrows():
        na = str(r['constituency_code'])
        cc = cn[cn['constituency_code'] == na].sort_values('candidate_votes', ascending=False)
        yd[na] = {'name': r['constituency_name'], 'prov': r['province'],
            'wp': r['win_party'], 'wn': r['win_name'],
            'wv': None if pd.isna(r['win_votes']) else int(r['win_votes']),
            'ws': None if pd.isna(r['win_pct']) else round(float(r['win_pct']) * 100, 1),
            'reg': None if pd.isna(r['voter_reg']) else int(r['voter_reg']),
            'to': None if pd.isna(r['turnout']) else round(float(r['turnout']) * 100, 1),
            'mov': None if pd.isna(r['MOV_pct']) else round(float(r['MOV_pct']) * 100, 1),
            'nc': len(cc), 'cands': top6(cc, 'candidate_name', 'candidate_party',
                                         'candidate_votes', 'candidate_share')}
    return yd

PARTY_FULL = {'PML-N':'Pakistan Muslim League (N)','PPP':'Pakistan Peoples Party Parliamentarians',
 'Independent':'Independent','MQM-P':'Muttahida Qaumi Movement Pakistan','MQM':'Muttahida Qaumi Movement Pakistan',
 'JUI-F':'Jamiat Ulema-e-Islam (F)','PML-Q':'Pakistan Muslim League (Q)','IPP':'Istehkam-e-Pakistan Party',
 'MWM':'Majlis Wahdat-e-Muslimeen','PML-Z':'Pakistan Muslim League (Zia)','BAP':'Balochistan Awami Party',
 'BNP':'Balochistan National Party (Mengal)','NP':'National Party','PKMAP':'Pashtunkhwa Milli Awami Party',
 'TLP':'Tehreek-e-Labbaik Pakistan','JIP':'Jamaat-e-Islami Pakistan','PMML':'Pakistan Markazi Muslim League',
 'SIC':'Sunni Ittehad Council','ANP':'Awami National Party','PAT':'Pakistan Awami Tehreek',
 'GDA':'Grand Democratic Alliance','PTI-N':'PTI-Nazriati','JUP-IN':'Jamiat Ulema-e-Pakistan (Noorani)'}

def year_2024():
    cs = pd.read_csv('data/results_2024/na_2024_constituency.csv')
    cd = pd.read_csv('data/results_2024/na_2024_candidates.csv')
    cd['party'] = cd['party'].map(lambda p: PARTY_FULL.get(p, p))
    yd = {}
    for _, r in cs.iterrows():
        na = r['na']
        cc = cd[cd['na'] == na].sort_values('votes', ascending=False)
        tot = cc['votes'].sum()
        wv = None if pd.isna(r['winner_votes']) else int(r['winner_votes'])
        ruv = None if pd.isna(r['runnerup_votes']) else int(r['runnerup_votes'])
        yd[na] = {'name': r['constituency_name'], 'prov': r['province'],
            'wp': PARTY_FULL.get(r['winner_party'], r['winner_party']), 'wn': r['winner_name'],
            'wv': wv, 'ws': None if (wv is None or not tot) else round(100 * wv / tot, 1),
            'reg': None, 'to': None,
            'mov': None if (wv is None or ruv is None or not tot) else round(100 * (wv - ruv) / tot, 1),
            'nc': len(cc), 'cands': top6(cc, 'candidate_name', 'party', 'votes', total=tot)}
    return yd

if __name__ == '__main__':
    cand = pd.read_csv('data/pakistan_elections/data/pk_candidate_data.csv', low_memory=False)
    cons = pd.read_csv('data/pakistan_elections/data/pk_constituency_data.csv', low_memory=False)
    res = {'2008': year_0813(cand, cons, '2/18/08', '2008-02-18'),
           '2013': year_0813(cand, cons, '5/11/13', '2013-05-11'),
           '2018': year_2018(), '2024': year_2024()}
    json.dump(res, open('results_all.json', 'w'))
    print({y: len(v) for y, v in res.items()})
