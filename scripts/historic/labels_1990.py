#!/usr/bin/env python3
"""1990 constituency labels from the 9th National Assembly roster (Wikipedia).

These name cross-district seats properly, which the scraped page titles do not.
Applied over the ElectionPakistani results so the district pipeline sees the
same naming convention it already handles for 1993 and 1997.
"""
RAW = """1 Peshawar-I|2 Peshawar-II|3 Peshawar-cum-Nowshera|4 Nowshera|5 Charsadda|6 Mardan-I
7 Mardan-II|8 Swabi|9 Kohat|10 Karak|11 Abottabad-I|12 Abbottabad-II|13 Abbottabad-III
14 Mansehra-I|15 Mansehra-II|16 Mansehra-III|17 Kohistan|18 D.I. Khan|19 Bannu-I|20 Bannu-II
21 Swat-I|22 Swat-II|23 Swat-III|24 Chitral|25 Dir|26 Malakand Protected Area-cum-Dir
27 Tribal Area-I|28 Tribal Area-II|29 Tribal Area-III|30 Tribal Area-IV|31 Tribal Area-V
32 Tribal Area-VI|33 Tribal Area-VII|34 Tribal Area-VIII|35 Federal Capital
36 Rawalpindi-I|37 Rawalpindi-II|38 Rawalpindi-III|39 Rawalpindi-IV|40 Rawalpindi-V
41 Attock-I|42 Attock-II|43 Chakwal-I|44 Chakwal-II|45 Jhelum-I|46 Jhelum-II
47 Sargodha-I|48 Sargodha-II|49 Sargodha-III|50 Sargodha-IV|51 Sargodha-cum-Khushab|52 Khushab
53 Mianwali-I|54 Mianwali-II|55 Bhakkar-I|56 Bhakkar-II
57 Faisalabad-I|58 Faisalabad-II|59 Faisalabad-III|60 Faisalabad-IV|61 Faisalabad-V
62 Faisalabad-VI|63 Faisalabad-VII|64 Faisalabad-VIII|65 Faisalabad-IX
66 Jhang-I|67 Jhang-II|68 Jhang-III|69 Jhang-IV|70 Jhang-V
71 T.T. Singh-I|72 T.T. Singh-II|73 T.T. Singh-III
74 Gujranwala-I|75 Gujranwala-II|76 Gujranwala-III|77 Gujranwala-IV|78 Gujranwala-V|79 Gujranwala-VI
80 Gujrat-I|81 Gujrat-II|82 Gujrat-III|83 Gujrat-IV|84 Gujrat-V
85 Sialkot-I|86 Sialkot-II|87 Sialkot-III|88 Sialkot-IV|89 Sialkot-V|90 Sialkot-VI|91 Sialkot-VII
92 Lahore-I|93 Lahore-II|94 Lahore-III|95 Lahore-IV|96 Lahore-V|97 Lahore-VI|98 Lahore-VII
99 Lahore-VIII|100 Lahore-IX
101 Sheikhupura-I|102 Sheikhupura-II|103 Sheikhupura-III|104 Sheikhupura-IV|105 Sheikhupura-V
106 Kasur-I|107 Kasur-II|108 Kasur-III|109 Kasur-IV
110 Okara-I|111 Okara-II|112 Okara-III|113 Okara-IV
114 Multan-I|115 Multan-II|116 Multan-III|117 Multan-IV|118 Multan-V|119 Multan-VI
120 Multan-cum-Khanewal|121 Khanewal-I|122 Khanewal-II|123 Khanewal-III
124 Sahiwal-I|125 Sahiwal-II|126 Sahiwal-III|127 Sahiwal-IV|128 Sahiwal-V
129 Vehari-I|130 Vehari-II|131 Vehari-III
132 D.G. Khan|133 D.G. Khan-cum-Rajanpur|134 Rajanpur
135 Muzaffargarh-I|136 Muzaffargarh-II|137 Muzaffargarh-III|138 Muzaffargarh-IV
139 Layyah-I|140 Layyah-II|141 Bahawalpur-I|142 Bahawalpur-II|143 Bahawalpur-III
144 Bahawalnagar-I|145 Bahawalnagar-II|146 Bahawalnagar-III
147 Rahimyar Khan-I|148 Rahimyar Khan-II|149 Rahimyar Khan-III|150 Rahimyar Khan-IV
151 Sukkur-I|152 Sukkur-II|153 Sukkur-III|154 Shikarpur-I|155 Shikarpur-II
156 Jacobabad-I|157 Jacobabad-II|158 Naushehro Feroze-I|159 Naushehro-II
160 Nawabshah-I|161 Nawabshah-II|162 Khairpur-I|163 Khairpur-II
164 Larkana-I|165 Larkana-II|166 Larkana-III
167 Hyderabad-I|168 Hyderabad-II|169 Hyderabad-III|170 Hyderabad-IV|171 Hyderabad-V
172 Badin-I|173 Badin-II|174 Tharparkar-I|175 Tharparkar-II|176 Tharparkar-III
177 Dadu-III|178 Dadu-I|179 Dadu-II|180 Sanghar-I|181 Sanghar-II|182 Thatta-I|183 Thatta-II
184 Karachi West-I|185 Karachi West-II|186 Karachi Central-I|187 Karachi Central-II
188 Karachi Central-III|189 Karachi South-I|190 Karachi South-II|191 Karachi South-III
192 Karachi East-I|193 Karachi East-II|194 Karachi East-III|195 Karachi East-IV|196 Karachi East-V
197 Quetta-cum-Chagai|198 Pishin|199 Loralai|200 Zhob-cum-Killa Saifullah|201 Kachhi
202 Sibbi-cum-Kohlu-cum-Dera Bugti-cum-Ziarat|203 Jaffarabad-cum-Tamboo|204 Kalat-cum-Kharan
205 Khuzdar|206 Lasbela-cum-Gwadar|207 Turbat-cum-Panjgur"""

TRIBAL = {1:'Mohmand',2:'Kurram',3:'Orakzai',4:'North Waziristan',
          5:'South Waziristan',6:'Bajaur',7:'Khyber'}
FR = ('Tribal Area 8: Tribal Areas Attached To Peshawar, Kohat, Bannu, '
      'Dera Ismail Khan, Tank And Lakki Marwat Districts')
ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10}
# label spelling -> the unit name the district pipeline already uses
FIX = {'Abottabad':'Abbottabad','T.T. Singh':'Toba Tek Singh','D.I. Khan':'Dera Ismail Khan',
       'D.G. Khan':'Dera Ghazi Khan','Rahimyar Khan':'Rahim Yar Khan','Sibbi':'Sibi',
       'Naushehro Feroze':'Naushero Feroz','Naushehro':'Naushero Feroz','Kachhi':'Bolan',
       'Federal Capital':'Islamabad','Malakand Protected Area':'Malakand',
       'Tamboo':'Jaffarabad','Turbat':'Turbat','Gwadar':'Gwadar'}

def labels():
    import re
    out = {}
    for chunk in RAW.replace('\n', '|').split('|'):
        chunk = chunk.strip()
        if not chunk: continue
        n, name = chunk.split(' ', 1)
        parts, ordinal = [], None
        segs = re.split(r'(?i)-cum-', name)
        for i, s in enumerate(segs):
            s = s.strip()
            m = re.search(r'-([IVX]+)$', s)
            if m:
                ordinal = ROMAN.get(m.group(1)); s = s[:m.start()].strip()
            parts.append(FIX.get(s, s))
        # collapse duplicates that FIX may introduce (e.g. Tamboo -> Jaffarabad)
        seen, uniq = set(), []
        for p in parts:
            if p not in seen: seen.add(p); uniq.append(p)
        if uniq == ['Tribal Area']:
            # match the 1993 convention so the agency can be recovered
            label = FR if ordinal == 8 else f'Tribal Area {ordinal} - {TRIBAL[ordinal]} Agency'
            out[f'NA-{n}'] = label; continue
        label = '-Cum-'.join(uniq)
        if ordinal and len(uniq) == 1: label = f'{label} {ordinal}'
        out[f'NA-{n}'] = label
    return out

if __name__ == '__main__':
    L = labels()
    print(len(L), 'labels')
    for k in ['NA-1','NA-3','NA-26','NA-35','NA-71','NA-132','NA-174','NA-197','NA-202','NA-207']:
        print(' ', k, '->', L[k])
