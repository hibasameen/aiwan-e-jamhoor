#!/usr/bin/env python3
"""Inject data/house/house.json into scripts/house/house_template.html -> house.html (site root)."""
import json, os
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
tpl = open(os.path.join(ROOT, 'scripts/house/house_template.html'), encoding='utf-8').read()
data = json.load(open(os.path.join(ROOT, 'data/house/house.json'), encoding='utf-8'))
blob = 'window.HOUSE=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';'
assert tpl.count('/*__HOUSE_JSON__*/') == 1
out = tpl.replace('/*__HOUSE_JSON__*/', blob)
open(os.path.join(ROOT, 'house.html'), 'w', encoding='utf-8').write(out)
print('wrote house.html', len(out), 'bytes')
