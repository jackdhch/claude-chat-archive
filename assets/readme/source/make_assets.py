"""README 的图：标题图（hero）和桌面应用侧栏动画（sidebar），浅色 / 深色各一套。
每张图先写成静态 SVG（最终画面），再用浏览器逐帧截图合成 GIF（GitHub 不播放 SVG 里的动画）。
需要：Python + Pillow + Playwright（chromium）。字体借用 Windows 的 Segoe UI / Cascadia（WSL 下 /mnt/c/Windows/Fonts），没有就退回系统字体。
用法：python3 assets/readme/source/make_assets.py        # 在仓库根目录运行，输出到 assets/readme/
图里的会话标题都是编的，配色取自 web/style.css。
"""
import io, os, sys
from PIL import Image
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FPS = 20
SANS = '-apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, &quot;Helvetica Neue&quot;, Arial, sans-serif'
MONO = '&quot;Cascadia Mono&quot;, &quot;SF Mono&quot;, Consolas, ui-monospace, monospace'
THEMES = {   # 取自 web/style.css 的浅色 :root 和深色重定义
    'light': dict(bg='#fcfcfd', card='#ffffff', side='#f6f6f8', sunk='#f2f2f5', line='#e2e3ea', fg='#1b1c21', fg2='#55586a', mut='#858898',
                  acc='#4b56d2', wash='#eef0fc', code='#4b56d2', chat='#d86a30', gpt='#b8398f', h=['#ececf0', '#66c3a4', '#27a180', '#007c60', '#005742'], sel='#e9eaf2'),
    'dark': dict(bg='#131417', card='#1d1e23', side='#16171b', sunk='#1a1b20', line='#2c2e36', fg='#e9eaf0', fg2='#a7aabb', mut='#7c7f90',
                 acc='#7f89ee', wash='#23263a', code='#7f89ee', chat='#d9692f', gpt='#d0509f', h=['#212227', '#1f5c4a', '#2a8a6c', '#3fb08c', '#6fd3ae'], sel='#272932'),
}

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ───────────── 标题图 1200×400 ─────────────
ROWS = [('code', 'Refactor config loading', 'Claude Code', '09-27'), ('chat', 'Trip budget spreadsheet', 'claude.ai', '06-12'),
        ('gpt', 'Regex for log parsing', 'ChatGPT', '05-03'), ('code', 'Fix flaky upload test', 'Claude Code', '09-18'),
        ('chat', 'Explain the Python GIL', 'claude.ai', '04-21')]
HEAT = [0, 1, 2, 1, 0, 3, 2, 4, 1, 0, 2, 3, 1, 0, 0, 2, 4, 3, 1, 2, 0, 1, 3, 2, 4, 1]

def hero(c):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400" font-family="{SANS}">',
         '<title>claude-chat-archive</title><desc>Claude Code, claude.ai and ChatGPT conversations merged into one offline archive</desc>',
         f'<rect x="0.5" y="0.5" width="1199" height="399" rx="18" fill="{c["bg"]}" stroke="{c["line"]}"/>',
         f'<text x="64" y="92" font-family="{MONO}" font-size="16" fill="{c["acc"]}">claude-chat-archive</text>',
         f'<text x="64" y="146" font-size="40" font-weight="700" fill="{c["fg"]}">Your Claude history,</text>',
         f'<text x="64" y="196" font-size="40" font-weight="700" fill="{c["fg"]}">back where you can use it.</text>']
    for i, (k, t) in enumerate([('chat', 'Continue claude.ai chats in Claude Code'), ('code', 'Get lost sessions back in the desktop app'),
                                ('gpt', 'Search Claude Code, claude.ai and ChatGPT offline')]):
        y = 250 + i * 34
        s.append(f'<rect x="64" y="{y - 11}" width="12" height="12" rx="3" fill="{c[k]}"/><text x="88" y="{y}" font-size="18" fill="{c["fg2"]}">{t}</text>')
    s.append(f'<text x="64" y="366" font-family="{MONO}" font-size="13" fill="{c["mut"]}">Python 3.9+ · standard library only · nothing leaves your machine</text>')
    # 右侧：存档窗口
    s += [f'<rect x="700" y="48" width="436" height="308" rx="14" fill="{c["card"]}" stroke="{c["line"]}"/>',
          f'<path d="M700 84 H1136" stroke="{c["line"]}"/>'] + \
         [f'<circle cx="{722 + i * 16}" cy="66" r="5" fill="{c["line"]}"/>' for i in range(3)] + \
         [f'<text x="918" y="71" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{c["mut"]}">archive · index.html</text>',
          f'<rect x="718" y="98" width="400" height="34" rx="8" fill="{c["sunk"]}" stroke="{c["line"]}"/>',
          f'<circle cx="737" cy="114" r="6" fill="none" stroke="{c["mut"]}" stroke-width="1.8"/><path d="M741.5 118.5 L746 123" stroke="{c["mut"]}" stroke-width="1.8" stroke-linecap="round"/>',
          f'<text x="756" y="120" font-size="14" fill="{c["mut"]}">Search all conversations</text>']
    for i, (k, t, src, d) in enumerate(ROWS):
        y = 146 + i * 34
        s.append(f'<g id="row{i}"><rect x="718" y="{y}" width="400" height="28" rx="6" fill="{c["card"]}"/>'
                 f'<circle cx="732" cy="{y + 14}" r="4.5" fill="{c[k]}"/><text x="746" y="{y + 19}" font-size="14" fill="{c["fg"]}">{esc(t)}</text>'
                 f'<text x="1024" y="{y + 19}" text-anchor="end" font-size="12" fill="{c[k]}">{src}</text>'
                 f'<text x="1106" y="{y + 19}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{c["mut"]}">{d}</text></g>')
    s.append('<g id="heat">' + ''.join(f'<rect x="{718 + i * 15.4:.1f}" y="324" width="12" height="12" rx="2.5" fill="{c["h"][v]}"/>' for i, v in enumerate(HEAT)) + '</g>')
    return '\n'.join(s) + '\n</svg>\n'

HERO_MOTION = dict(w=1200, h=400, dur=5.6,
                   layers=[dict(id=f'row{i}', enter=(0.5 + i * 0.28, 1.3 + i * 0.28), dx=-36, exit=(4.9, 5.5)) for i in range(5)]
                          + [dict(id='heat', enter=(2.2, 2.9), dx=0, exit=(4.9, 5.5))])

# ───────────── 侧栏动画 1200×520 ─────────────
GROUPS = [('demo-proj', [('Switch prints to logging', '09-02'), ('Unit tests for the parser', '08-27'), ('Refactor config loading', '08-19')]),
          ('claude-ai-chats', [('[claude.ai] Trip budget', '06-12'), ('[claude.ai] Python GIL', '04-21')]),
          ('notes', [('Weekly report template', '08-30')])]

def sidebar(c):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" width="1200" height="520" font-family="{SANS}">',
         '<title>Old sessions reappear in the desktop app\'s Code sidebar</title><desc>Mock-up with made-up titles: after running the register command and reopening the desktop app, old sessions appear grouped by folder</desc>',
         f'<rect x="0.5" y="0.5" width="1199" height="519" rx="18" fill="{c["bg"]}" stroke="{c["line"]}"/>',
         # 左：终端
         f'<text x="56" y="70" font-size="15" font-weight="600" fill="{c["fg"]}">1 · Run</text>',
         f'<rect x="56" y="88" width="430" height="150" rx="12" fill="{c["card"]}" stroke="{c["line"]}"/>',
         f'<g id="cmd1"><text x="78" y="128" font-family="{MONO}" font-size="15" fill="{c["fg"]}"><tspan fill="{c["acc"]}">$ </tspan>python3 claude_archive.py \\</text></g>',
         f'<g id="cmd2"><text x="114" y="154" font-family="{MONO}" font-size="15" fill="{c["fg"]}">--import-claude-ai --write</text></g>',
         f'<g id="cmd3"><text x="78" y="190" font-family="{MONO}" font-size="15" fill="{c["fg"]}"><tspan fill="{c["acc"]}">$ </tspan>python3 claude_archive.py \\</text>'
         f'<text x="114" y="216" font-family="{MONO}" font-size="15" fill="{c["fg"]}">--register-desktop --write</text></g>',
         f'<text x="56" y="290" font-size="15" font-weight="600" fill="{c["fg"]}">2 · Reopen the desktop app</text>',
         f'<text x="56" y="318" font-size="14" fill="{c["fg2"]}">Old sessions come back, grouped by folder.</text>',
         f'<text x="56" y="342" font-size="14" fill="{c["fg2"]}">claude.ai chats get their own group, ready to continue.</text>',
         f'<text x="56" y="468" font-size="12" fill="{c["mut"]}">Mock-up with made-up titles</text>',
         # 右：桌面应用窗口
         f'<rect x="560" y="40" width="584" height="440" rx="14" fill="{c["card"]}" stroke="{c["line"]}"/>',
         f'<path d="M560 76 H1144" stroke="{c["line"]}"/>'] + \
        [f'<circle cx="{582 + i * 16}" cy="58" r="5" fill="{c["line"]}"/>' for i in range(3)] + \
        [f'<text x="852" y="63" text-anchor="middle" font-size="13" fill="{c["mut"]}">Claude · Code</text>',
         f'<path d="M560 76 H860 V479 H574 Q561 479 561 466 V76" fill="{c["side"]}"/><path d="M860 76 V480" stroke="{c["line"]}"/>',
         f'<rect x="574" y="90" width="272" height="34" rx="8" fill="{c["card"]}" stroke="{c["line"]}"/>',
         f'<text x="590" y="112" font-size="14" fill="{c["fg"]}">＋  New session</text>']
    y = 150; n = 0
    for g, items in GROUPS:
        s.append(f'<g id="g{n}"><text x="586" y="{y}" font-size="12" fill="{c["mut"]}">{g}</text><text x="834" y="{y}" text-anchor="end" font-size="12" fill="{c["mut"]}">{len(items)}</text></g>')
        n += 1; y += 26
        for t, d in items:
            k = 'chat' if t.startswith('[claude.ai]') else 'code'
            s.append(f'<g id="g{n}"><circle cx="590" cy="{y - 5}" r="3.5" fill="{c[k]}"/><text x="602" y="{y}" font-size="13.5" fill="{c["fg"]}">{esc(t)}</text>'
                     f'<text x="834" y="{y}" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{c["mut"]}">{d}</text></g>')
            n += 1; y += 28
        y += 10
    s.append(f'<rect x="574" y="{y - 12}" width="272" height="30" rx="7" fill="{c["sel"]}"/><text x="590" y="{y + 8}" font-size="13.5" fill="{c["fg"]}">New session</text>'
             f'<text x="834" y="{y + 8}" text-anchor="end" font-size="11.5" fill="{c["mut"]}">now</text>')
    for i, w in enumerate((70, 92, 56)):
        s.append(f'<rect x="884" y="{104 + i * 22}" width="{w * 2.6:.0f}" height="9" rx="4.5" fill="{c["sunk"]}"/>')
    return '\n'.join(s) + '\n</svg>\n', n

def sidebar_motion(n):
    L = [dict(id='cmd1', reveal=(0.3, 1.0)), dict(id='cmd2', reveal=(1.0, 1.7)), dict(id='cmd3', reveal=(2.0, 3.0))]
    L += [dict(id=f'g{i}', enter=(3.3 + i * 0.16, 3.9 + i * 0.16), dx=-24, exit=(7.2, 7.8)) for i in range(n)]
    for l in L[:3]: l['exit'] = (7.2, 7.8)
    return dict(w=1200, h=520, dur=7.9, layers=L)

# ───────────── 逐帧截图 → GIF ─────────────
FONTS = ''.join(f"@font-face{{font-family:'{f}';src:url('file://{p}')}}" for f, p in
                [('Segoe UI', '/mnt/c/Windows/Fonts/segoeui.ttf'), ('Cascadia Mono', '/mnt/c/Windows/Fonts/CascadiaMono.ttf')] if os.path.exists(p)) + \
        (f"@font-face{{font-family:'Segoe UI';font-weight:600 700;src:url('file:///mnt/c/Windows/Fonts/segoeuib.ttf')}}" if os.path.exists('/mnt/c/Windows/Fonts/segoeuib.ttf') else '')
JS = """window.setT = (t, layers) => {
  const ease = p => 1 - Math.pow(1 - Math.min(Math.max(p, 0), 1), 3);
  for (const l of layers) {
    const e = document.getElementById(l.id); let o = 1, dx = 0, clip = 0;
    if (l.enter) { const p = ease((t - l.enter[0]) / (l.enter[1] - l.enter[0])); o = p; dx = (1 - p) * (l.dx || 0); }
    if (l.reveal) { const p = Math.min(Math.max((t - l.reveal[0]) / (l.reveal[1] - l.reveal[0]), 0), 1); clip = 100 - 100 * p; o = p > 0 ? 1 : 0; }
    if (l.exit) { const p = ease((t - l.exit[0]) / (l.exit[1] - l.exit[0])); o *= 1 - p; }
    e.style.opacity = o; e.style.transform = `translate(${dx}px,0)`; e.style.clipPath = clip ? `inset(0 ${clip}% 0 0)` : '';
  }
};"""

def gif(page, svg, m, path):
    page.set_viewport_size({'width': m['w'], 'height': m['h']})
    tmp = os.path.join(OUT, 'source', '_frame.html')   # 存成文件再打开：about:blank 里不让加载本机字体文件
    open(tmp, 'w', encoding='utf-8').write(f'<!doctype html><meta charset="utf-8"><style>{FONTS}html,body{{margin:0;background:transparent}}</style>{svg}<script>{JS}</script>')
    page.goto('file://' + tmp); page.evaluate('document.fonts.ready'); os.remove(tmp)
    page.wait_for_timeout(300)
    frames = []
    for i in range(int(m['dur'] * FPS)):
        page.evaluate('([t, l]) => setT(t, l)', [i / FPS, m['layers']])
        frames.append(Image.open(io.BytesIO(page.screenshot(clip={'x': 0, 'y': 0, 'width': m['w'], 'height': m['h']}))).convert('RGB'))
    pal = frames[len(frames) // 2].quantize(colors=256, method=Image.Quantize.MEDIANCUT)   # 画面最满的一帧定调色板，所有帧共用
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=1000 // FPS, loop=0, optimize=True, disposal=1)
    return len(frames), os.path.getsize(path)

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_page()
        for th, c in THEMES.items():
            h = hero(c); open(f'{OUT}/hero-{th}.svg', 'w', encoding='utf-8').write(h)
            print('hero', th, gif(page, h, HERO_MOTION, f'{OUT}/hero-{th}.gif'))
            sb, n = sidebar(c); open(f'{OUT}/sidebar-{th}.svg', 'w', encoding='utf-8').write(sb)
            print('sidebar', th, gif(page, sb, sidebar_motion(n), f'{OUT}/sidebar-{th}.gif'))
        b.close()

if __name__ == '__main__': main()
