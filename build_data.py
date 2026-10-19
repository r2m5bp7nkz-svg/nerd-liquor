#!/usr/bin/env python3
"""Regenerate data.json from the nerd liquor master list markdown.
Usage: python3 build_data.py [path/to/master-list.md]"""
import json, re, sys, os
from urllib.parse import urlparse

SRC = sys.argv[1] if len(sys.argv) > 1 else '/workspace/nerd-liquor-master-list.md'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
md = open(SRC, encoding='utf-8').read()

m = re.search(r'\(updated ([^)]+)\)', md)
updated = m.group(1) if m else ''

SECTIONS = {'available now': 'Available now', 'preorder': 'Preorder / upcoming', 'watching': 'Watching'}
FRANCHISES = [('GoT', 'Game of Thrones'), ('LOTR', 'Lord of the Rings'), ('Star Trek', 'Star Trek'),
              ('D&D', 'Dungeons & Dragons'), ('Ghost in the Shell', 'Ghost in the Shell'),
              ('Godzilla', 'Godzilla'), ('Rocketeer', 'The Rocketeer')]
HOUSES = ['Stark', 'Lannister', 'Greyjoy', 'Targaryen', "Night's Watch", 'Baratheon', 'Tyrell', 'Tully']

def franchise(name):
    for k, v in FRANCHISES:
        if name.startswith(k): return v
    return 'Other'

def type_cat(t):
    l = t.lower()
    if 'scotch' in l: return 'Scotch'
    if 'bourbon' in l: return 'Bourbon'
    if 'rye' in l: return 'Rye'
    if 'brandy' in l: return 'Brandy'
    if 'rum' in l: return 'Rum'
    if 'gin' in l.split(' ')[0] or l.startswith('gin'): return 'Gin'
    if 'vodka' in l: return 'Vodka'
    return 'Other whisky'

def verdict_cat(v):
    l = v.lower()
    if 'well above' in l: return ('bad', 'Well above market')
    if 'above market' in l or ' is above' in l: return ('warn', 'Above market')
    if 'lowest found' in l or 'lowest verified' in l: return ('good', 'Lowest found')
    if 'at msrp' in l: return ('ok', 'At MSRP')
    if 'cheaper' in l or 'is the lowest' in l or 'bargain' in l: return ('warn', 'Cheaper elsewhere')
    if ' over ' in l: return ('warn', 'Slightly above')
    if 'at msrp' in l: return ('ok', 'At MSRP')
    if 'near typical' in l or 'about typical' in l: return ('ok', 'Near typical')
    if 'no comparison' in l or 'no reputable' in l or 'lottery-only' in l: return ('none', 'No comparison')
    return ('ok', 'See notes')

items, section = [], None
for line in md.splitlines():
    h = re.match(r'^##\s+(.*)', line)
    if h:
        t = h.group(1).lower()
        section = next((v for k, v in SECTIONS.items() if t.startswith(k)), h.group(1))
        continue
    if not (section and line.startswith('- ')): continue
    parts = [p.strip() for p in line[2:].split(' | ')]
    name, ltype = parts[0], parts[1] if len(parts) > 1 else ''
    rest = parts[2:]
    pc = next((p for p in rest if p.lower().startswith('price check')), '')
    url = next((p for p in rest if p.startswith('http')), '')
    got = next((p for p in rest if p.startswith('GoT ')), '')
    price = ''
    if url:
        i = rest.index(url)
        if i > 0: price = rest[i - 1]
    else:
        price = next((p for p in rest if re.match(r'^([$£€—-]|GBP|JPY|NZ\$)', p)), '')
    notes = [p for p in rest if p not in (pc, url, got, price)]
    pc_text = re.sub(r'^price check:\s*', '', pc, flags=re.I)
    vm = re.search(r'Verdict:\s*(.*)$', pc_text)
    verdict = vm.group(1).strip() if vm else pc_text
    vclass, vlabel = verdict_cat(verdict)
    host = urlparse(url).hostname or '' if url else ''
    host = host.replace('www.', '')
    non_us = bool(re.search(r'\.(uk|jp|nz)$', host)) or host in ('kamikiwhisky.com',) \
        or price.startswith(('GBP', 'JPY', 'NZ$')) or 'Japan-only' in ' '.join(notes)
    house = next((h for h in HOUSES if re.search(r'House Collection: (House )?' + re.escape(h), got)), '')
    if not house and got: house = 'Add-on'
    full_type = ltype
    short_type = re.sub(r',\s*not beer.*', '', ltype.split(':')[0]).strip()
    if len(short_type) > 45: short_type = re.sub(r'\s*\(.*\)', '', short_type).strip()
    if short_type.isupper(): short_type = short_type.title()
    items.append(dict(
        name=re.sub(r'\s*\(NEW\)', '', name), new='(NEW)' in name, status=section,
        franchise=franchise(name), type=short_type, type_full=full_type, type_cat=type_cat(ltype),
        price=price or '—', url=url, seller=host or 'n/a', region='Non-US' if non_us else 'US',
        got_tag=got, house=house, notes=' | '.join(notes), price_check=pc_text,
        verdict=verdict, verdict_class=vclass, verdict_label=vlabel))

# GoT checklist
checklist = []
hc = re.search(r'GoT 2018 House Collection.*?:\n(.*?)\n', md, re.S)
pairs = re.findall(r"([A-Z][\w']+(?: [A-Z][\w']+)?) = ([^|.]+?)(?= \||\. |$)", hc.group(1)) if hc else []
for house, bottle in pairs:
    it = next((i for i in items if i['house'] == house), None)
    checklist.append(dict(kind='House', house=house, bottle=bottle.strip(),
                          listed=bool(it), item=it['name'] if it else None,
                          price=it['price'] if it else None, url=it['url'] if it else None))
for key, label in [('Mortlach', 'Mortlach 15 "Six Kingdoms" (9th & final release, 2019)'),
                   ('White Walker', 'Johnnie Walker White Walker (2018 companion blend)')]:
    it = next((i for i in items if key in i['name']), None)
    checklist.append(dict(kind='Add-on', house='Add-on', bottle=label, listed=bool(it),
                          item=it['name'] if it else None, price=it['price'] if it else None,
                          url=it['url'] if it else None))

json.dump(dict(updated=updated, source=os.path.basename(SRC), items=items, got_checklist=checklist),
          open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(f'wrote {OUT}: {len(items)} items, {len(checklist)} checklist rows, updated {updated}')
