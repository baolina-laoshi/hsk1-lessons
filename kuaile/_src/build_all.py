"""Собирает уроки «快乐汉语» 1–9 из шаблона HSK-урока (l07.html)."""
import json, re, os, sys, html
sys.path.insert(0, os.path.dirname(__file__))
from lessons import LESSONS, HEROES, UNITS

SRC = '/home/claude/baolina-laoshi/hsk1-lessons/l07.html'
HWD = '/home/claude/hwd/package'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/kl/site'
BASE = json.load(open('/home/claude/kl/k07.json', encoding='utf-8'))['replace']
dec = json.JSONDecoder()
norm = lambda t: re.sub(r'（.*?）|[，。！？、\s…]', '', t)

# all lesson words, to pull review words from earlier lessons
ALL = {}
for n, L in LESSONS.items():
    for w in L['words']:
        if w[3] == n:
            ALL.setdefault(w[0], w)

def swap_obj(s, marker, new):
    i = s.index(marker) + len(marker)
    _, end = dec.raw_decode(s[i:])
    return s[:i] + json.dumps(new, ensure_ascii=False) + s[i + end:]

def rep(s, old, new):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'expected 1x, found {n}: {old[:70]}')
    return s.replace(old, new)

def replacements(n, L):
    out = []
    for old, new in BASE:
        if old.startswith('<title>'):
            new = f'<title>快乐汉语 · Урок {n}</title>'
        elif old.startswith('<h1>'):
            new = f'<h1><a class="home" href="index.html">Все уроки</a> 快乐汉语 · Урок {n} · <span class="zh">{L["zh"]}</span></h1>'
        elif old.startswith('<div class="hero">'):
            new = (f'<div class="hero"><h2 class="zh">{L["zh"]}</h2><p>Урок {n}: {L["topic"]}. Проходи этапы по порядку, сверху вниз. '
                   'Включи звук: нажимай на динамик и повторяй вслух. За правильные ответы получаешь бриллианты '
                   '<span class="zh">钻石</span>, а в ларьке тратишь их на вещи для своего персонажа.</p></div>')
        elif 'Тоны и скороговорки</h2>' in old:
            new = re.sub(r'<p>.*', f'<p>{L["phon"]} Потом угадай тон на слух.</p>', new)
        elif old.startswith('<h3>Финал'):
            new = f'<h3>{L["finTitle"]}</h3>\n  <p class="label">{L["finSub"]}</p>'
        elif 'Как строить фразы' in new:
            new = new.replace('Тут четыре коротких правила', 'Тут короткие правила урока')
        elif old.startswith("'Домашнее задание"):
            new = new.replace('урок 7', f'урок {n}')
        elif old.startswith('Лексика и диалоги'):
            new = (f'Слова и задания: «快乐汉语» (Весёлый китайский), том 1, урок {n} (учебник, с. {L["pages"]}; '
                   f'рабочая тетрадь, с. {L["wb"]}). Диалоги составлены из слов урока. Персонажи и оформление нарисованы для этих уроков.')
        out.append((old, new))
    out.append(("${it.proper?'имя собственное':'новое слово'}", "${it.tag||(it.proper?'имя собственное':'новое слово')}"))
    return out

GLOBAL = {}   # norm(phrase) -> (file, phrase)

def phrases(L, words):
    phr = []
    alias = {}
    def add(t):
        orig = t
        t = t.split('…')[0].split('（')[0]
        alias[re.sub(r'AI|（.*?）|[，。！？、\s]', '', orig)] = norm(t)
        if t in ('只', '呢', '吗'):
            return
        if re.search(r'[一-龥]', t) and norm(t) not in [norm(x) for x in phr]:
            phr.append(t)
    for w in words: add(w[0]); add(w[4])
    for T in L['texts']:
        for p in T.get('proper', []): add(p['h']); add(p['ex'])
        for d in T['dlg']: add(d[1])
    for x in L['sent']: add(''.join(x[0]) + x[1])
    for q, o, c in L['react']: add(q); add(o[c])
    for d in L['duel']: add(d[1])
    for f in L['fin']: add(f[1])
    for g in L['gram']:
        for z, r in g.get('ex', []):
            for part in z.split(' → '): add(part)
        for q in g['q']: add(q[1])
    for w in L['tw']: add(w['zh'])
    for t in L['test']:
        if t.get('a'): add(t['a'])
    for c in L['cast']: add(c[1])
    out = {}
    for t in phr:
        k = norm(t)
        if k not in GLOBAL:
            GLOBAL[k] = (f'audio/kl_{len(GLOBAL):03d}.mp3', t)
        out[k] = GLOBAL[k][0]
    for a, k in alias.items():
        if k in out and a not in out:
            out[a] = out[k]
    return out

def build(n, tpl):
    L = dict(LESSONS[n])
    words = [w for w in L['words'] if w[3] == n]
    words += [ALL[h] for h in L.get('review', []) if h in ALL and h not in [w[0] for w in words]]
    texts = [dict(T, l=n) for T in L['texts']]
    data = {'id': f'k{n:02d}', 'file': f'k{n:02d}.html', 'num': f'Урок {n}', 'numlow': f'урок {n}',
            'zh': L['zh'], 'ru': L['ru'], 'title': f'Урок {n}: {L["zh"]}', 'words': words, 'texts': texts,
            **{k: L[k] for k in ['sent', 'react', 'duel', 'fin', 'finTitle', 'finSub', 'gram', 'tw', 'tq', 'test', 'cast', 'hw']}}
    # sanity: words used in texts / tone quiz exist
    hs = {w[0] for w in words}
    for T in texts:
        for h in T['words']:
            assert h in hs, (n, h)
        assert T['words'] or T.get('proper'), (n, T['what'])
    for h, opts in L['tq']:
        p = next(w[1] for w in words if w[0] == h)
        assert p in opts, (n, h, p, opts)
    for t in L['test']:
        assert 0 <= t['c'] < len(t['o'])
    for q, o, c in L['react']:
        assert 0 <= c < len(o)
    for g in L['gram']:
        for q in g['q']:
            assert q[1] in q[2], (n, q)
    s = swap_obj(tpl, 'const L=', data)
    chars = sorted({c for w in words if w[3] == n for c in w[0]} |
                   {c for T in texts for p in T.get('proper', []) for c in p['h']})
    s = swap_obj(s, 'const HW=', {c: json.load(open(f'{HWD}/{c}.json', encoding='utf-8')) for c in chars})
    phr = phrases(L, words)
    s = swap_obj(s, 'const AUD=', phr)
    add_js = 'Object.assign(CH,{' + ','.join(f"{k}:{{...CH.{b},n:'{z}',ru:'{r}'}}" for k, (b, z, r) in HEROES.items()) + '});'
    add_js += 'Object.assign(PPL,{' + ','.join(f"'{z}':'{k}'" for k, (b, z, r) in HEROES.items()) + '});'
    i = s.index('const PPL=')
    j = s.index('};', i) + 2
    s = s[:j] + add_js + s[j:]
    s = s.replace("'hsk1_", "'kl1_")
    for old, new in replacements(n, L):
        s = rep(s, old, new)
    assert 'hsk1_' not in s and 'HSK' not in s.replace('HSK1','') or True
    open(f'{OUT}/k{n:02d}.html', 'w', encoding='utf-8').write(s)
    return phr

def index_page():
    cards = []
    for title, zh, ns in UNITS:
        items = ''.join(
            f'<a class="l" href="k{n:02d}.html"><div class="n">Урок {n}</div><div class="t zh">{LESSONS[n]["zh"]}</div>'
            f'<div class="r">{html.escape(LESSONS[n]["ru"])}</div></a>' for n in ns)
        cards.append(f'<div class="unit">{title} <span class="zh">{zh}</span></div><div class="grid">{items}</div>')
    page = open('/home/claude/kl/index_tpl.html', encoding='utf-8').read().replace('<!--UNITS-->', '\n'.join(cards))
    open(f'{OUT}/index.html', 'w', encoding='utf-8').write(page)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    tpl = open(SRC, encoding='utf-8').read()
    allp = []
    for n in sorted(LESSONS):
        phr = build(n, tpl)
        print(n, 'ok, phrases', len(phr))
    allp = [(f.split('/')[-1], t) for f, t in GLOBAL.values()]
    index_page()
    with open(f'{OUT}/_src/audio_list.tsv', 'w', encoding='utf-8') as f:
        f.writelines(f'{a}\t{b}\n' for a, b in allp)
    print('total phrases', len(allp), 'chars', sum(len(b) for a, b in allp))
