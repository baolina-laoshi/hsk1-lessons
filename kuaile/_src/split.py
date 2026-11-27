"""Режет mp3 TTSMaker по паузам между строками и раскладывает по именам файлов."""
import subprocess, re, json, sys
src, idx, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
chunk = json.load(open('/home/claude/kl/chunks.json', encoding='utf-8'))[idx]
def silences(th):
    r = subprocess.run(['ffmpeg', '-i', src, '-af', f'silencedetect=noise=-40dB:d={th}', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
    return list(zip(st, en))
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
for th in [1.4, 1.2, 1.6, 1.0, 1.8]:
    sil = [s for s in silences(th) if s[0] > 0.05 and s[1] < dur - 0.05]
    if len(sil) == len(chunk) - 1:
        break
else:
    raise SystemExit(f'no threshold gives {len(chunk)-1} gaps; last found {len(sil)}')
bounds = [0.0] + [(a + b) / 2 for a, b in sil] + [dur]
for k, (f, t) in enumerate(chunk):
    a = max(0, bounds[k] if k == 0 else sil[k - 1][1] - 0.15)
    b = bounds[k + 1] if k == len(chunk) - 1 else sil[k][0] + 0.25
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-ac', '1', '-b:a', '64k', f'{out}/{f}'], check=True)
print('ok', len(chunk), 'th', th, 'dur', round(dur, 1))
