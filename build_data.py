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
              ('Godzilla', 'Godzilla'), ('Rocketeer', 'The Rocketeer'), ('Marvel', 'Marvel')]
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
    if 'liqueur' in l: return 'Liqueur'
    if 'rum' in l: return 'Rum'
    if 'gin' in l.split(' ')[0] or l.startswith('gin'): return 'Gin'
    if 'vodka' in l: return 'Vodka'
    return 'Other whisky'

BADGES = {'best price': ('good', 'Best price'), 'cheaper elsewhere': ('warn', 'Cheaper elsewhere'),
          'no comparison': ('none', 'No comparison')}

def field(rest, key):
    return next((re.sub(r'^' + key + r':\s*', '', p, flags=re.I) for p in rest if p.lower().startswith(key.lower() + ':')), '')

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
    series_full = field(rest, 'Series')
    msrp = field(rest, 'MSRP') or 'unknown'
    lowest_raw = field(rest, 'Lowest found')
    compare = field(rest, 'Compare')
    special = {p for p in rest if re.match(r'^(Series|MSRP|Lowest found|Compare):', p, re.I)}
    notes = [p for p in rest if p not in (pc, url, got, price) and p not in special]
    lm = re.match(r'^(.*?)\s*@\s*(.*?)(?:\s*<(\S+)>)?$', lowest_raw)
    price_lowest, lowest_store, lowest_url = (lm.group(1), lm.group(2), lm.group(3) or '') if lm else ('none', '', '')
    cm = re.match(r'^(Best price|Cheaper elsewhere|No comparison)\s*-\s*(.*)$', compare, re.I)
    if not cm: raise SystemExit(f'missing/invalid Compare field for: {name}')
    vclass, vlabel = BADGES[cm.group(1).lower()]
    verdict = cm.group(2).strip()
    series = series_full.split(' - ')[0].strip() if series_full else ''

    pc_text = re.sub(r'^price check:\s*', '', pc, flags=re.I)
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
        name=re.sub(r'\s*\(ADDED [^)]*\)', '', name), new=(re.search(r'\(ADDED ([^)]*)\)', name).group(1) if re.search(r'\(ADDED ([^)]*)\)', name) else ''), status=section,
        franchise=franchise(name), type=short_type, type_full=full_type, type_cat=type_cat(ltype),
        price=price or '—', url=url, seller=host or 'n/a', region='Non-US' if non_us else 'US',
        got_tag=got, house=house, notes=' | '.join(notes), price_check=pc_text,
        verdict=verdict, verdict_class=vclass, verdict_label=vlabel,
        price_current=price or '—', price_msrp=msrp, price_lowest=price_lowest,
        lowest_store=lowest_store, lowest_url=lowest_url,
        series=series or 'None (standalone)', series_full=series_full))

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
