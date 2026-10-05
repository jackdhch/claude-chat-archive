"""给 README 截静态图，覆盖 docs/screenshots/ 里的同名文件。先用 build_demo_site.py 造好演示存档。
用法：python3 assets/readme/source/shoot.py <演示存档目录 out>
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SHOTS = os.path.join(ROOT, 'docs', 'screenshots')

def href(out, sub, pick):
    s = open(f'{out}/{sub}data.js', encoding='utf-8').read(); rs = json.loads(re.search(r'window\.D=(.*?);?\s*$', s, re.S)[1])
    return sub + next(r for r in rs if pick(r))['href']

def main(out):
    out = os.path.abspath(out)
    sess = href(out, '', lambda r: r['t'].startswith('Add dark mode toggle'))
    s = open(f'{out}/chatgpt/data.js', encoding='utf-8').read(); g = max(json.loads(re.search(r'window\.D=(.*?);?\s*$', s, re.S)[1]), key=lambda r: (r.get('nq', 0), r.get('nmsg', 0)))
    gsess = 'chatgpt/' + g['href']   # 提问、消息最多的那个，截图不空
    jobs = [('home-light.png', 'index.html', 'light', 1440, 1000), ('home-dark-topics.png', 'index.html?group=topic', 'dark', 1440, 1000),
            ('session.png', sess, 'light', 1440, 1000), ('chatgpt-home-light.png', 'chatgpt/index.html', 'light', 1440, 1000),
            ('chatgpt-session-dark.png', gsess, 'dark', 1100, 900)]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, url, scheme, w, h in jobs:
            pg = b.new_page(viewport={'width': w, 'height': h}, color_scheme=scheme)
            pg.goto(f'file://{out}/{url}'); pg.wait_for_timeout(500); pg.screenshot(path=os.path.join(SHOTS, name)); pg.close()
            print(name, url)
        b.close()

if __name__ == '__main__': main(sys.argv[1])
