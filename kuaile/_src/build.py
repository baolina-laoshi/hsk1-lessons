"""Собирает урок «快乐汉语» из шаблона HSK-урока (l07.html) и данных урока."""
import json, re, sys, os

SRC = '/home/claude/baolina-laoshi/hsk1-lessons/l07.html'
HWD = '/home/claude/hwd/package'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/kl/out'
lesson = json.load(open(sys.argv[1], encoding='utf-8'))
s = open(SRC, encoding='utf-8').read()
dec = json.JSONDecoder()

def swap_obj(s, marker, new):
    i = s.index(marker) + len(marker)
    _, end = dec.raw_decode(s[i:])
    return s[:i] + json.dumps(new, ensure_ascii=False) + s[i + end:]

def rep(s, old, new, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f'expected {count}x, found {n}: {old[:70]}')
    return s.replace(old, new)

L = lesson['L']
num = L['n']
# words: review words go into games, lesson words into learn stage
s = swap_obj(s, 'const L=', {
    'id': f'k{num:02d}', 'file': f'k{num:02d}.html', 'num': f'Урок {num}', 'numlow': f'урок {num}',
    'zh': L['zh'], 'ru': L['ru'], 'title': f'Урок {num}: {L["zh"]}',
    **{k: L[k] for k in ['words', 'texts', 'sent', 'react', 'duel', 'fin', 'finTitle', 'finSub', 'gram', 'tw', 'tq', 'test', 'cast', 'hw']}})

# stroke data for every character of lesson words
chars = sorted({c for w in L['words'] if w[3] == num for c in w[0]})
HW = {c: json.load(open(f'{HWD}/{c}.json', encoding='utf-8')) for c in chars}
s = swap_obj(s, 'const HW=', HW)

# audio map: audio/kNN_xx.mp3 for every phrase (files may be added later; browser voice is the fallback)
norm = lambda t: re.sub(r'（.*?）|[，。！？、\s]', '', t)
phr = []
def add(t):
    t = t.split('…')[0]
    if re.search(r'[一-龥]', t) and norm(t) not in [norm(x) for x in phr]:
        phr.append(t)
for w in L['words']: add(w[0]); add(w[4])
for T in L['texts']:
    for d in T['dlg']: add(d[1])
for x in L['sent']: add(''.join(x[0]) + x[1])
for q, o, c in L['react']: add(q); [add(y) for y in o]
for d in L['duel']: add(d[1])
for f in L['fin']: add(f[1])
for g in L['gram']:
    for z, r in g.get('ex', []): add(z.split(' → ')[-1]); add(z.split(' → ')[0])
    for q in g['q']: add(q[1])
for w in L['tw']: add(w['zh'])
for t in L['test']:
    if t.get('a'): add(t['a'])
for c in L['cast']: add(c[1])
AUD = {norm(t): f'audio/k{num:02d}_{i:02d}.mp3' for i, t in enumerate(phr)}
s = swap_obj(s, 'const AUD=', AUD)

# characters from 快乐汉语: reuse the existing drawings under the textbook heroes' names
heroes = lesson['heroes']  # key -> [base drawing, zh name, ru name]
add_js = 'Object.assign(CH,{' + ','.join(f"{k}:{{...CH.{b},n:'{z}',ru:'{r}'}}" for k, (b, z, r) in heroes.items()) + '});'
add_js += 'Object.assign(PPL,{' + ','.join(f"'{z}':'{k}'" for k, (b, z, r) in heroes.items()) + '});'
i = s.index('const PPL=')
j = s.index('};', i) + 2
s = s[:j] + add_js + s[j:]

# separate wallet, shop and word bank from HSK
s = s.replace("'hsk1_", "'kl1_")
assert 'hsk1_' not in s

# texts in markup and JS
for old, new in lesson['replace']:
    s = rep(s, old, new)

os.makedirs(OUT, exist_ok=True)
open(f'{OUT}/k{num:02d}.html', 'w', encoding='utf-8').write(s)
with open(f'{OUT}/k{num:02d}_audio.txt', 'w', encoding='utf-8') as f:
    for k, t in enumerate(phr):
        f.write(f'k{num:02d}_{k:02d}.mp3\t{t}\n')
print('ok', len(s), 'chars', ''.join(chars), 'phrases', len(phr))
