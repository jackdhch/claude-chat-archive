"""README 的图：标题图（hero）、桌面应用侧栏动画（sidebar）和流程图（flow，中英各一），浅色 / 深色各一套。
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
         # 字号按 GitHub 正文约 900px 宽（缩到 0.75）来定：要紧的字 ≥ 20，辅助的 ≥ 15
         f'<text x="64" y="90" font-family="{MONO}" font-size="19" fill="{c["acc"]}">claude-chat-archive</text>',
         f'<text x="64" y="148" font-size="44" font-weight="700" fill="{c["fg"]}">Your Claude history,</text>',
         f'<text x="64" y="202" font-size="44" font-weight="700" fill="{c["fg"]}">back where you can use it.</text>']
    for i, (k, t) in enumerate([('chat', 'Continue claude.ai chats in Claude Code'), ('code', 'Get lost sessions back in the desktop app'),
                                ('gpt', 'Search Claude Code, claude.ai and ChatGPT offline')]):
        y = 256 + i * 38
        s.append(f'<rect x="64" y="{y - 13}" width="14" height="14" rx="3.5" fill="{c[k]}"/><text x="92" y="{y}" font-size="21" fill="{c["fg2"]}">{t}</text>')
    s.append(f'<text x="64" y="370" font-family="{MONO}" font-size="15" fill="{c["mut"]}">Python 3.9+ · standard library only · nothing leaves your machine</text>')
    # 右侧：存档窗口
    s += [f'<rect x="700" y="48" width="436" height="308" rx="14" fill="{c["card"]}" stroke="{c["line"]}"/>',
          f'<path d="M700 84 H1136" stroke="{c["line"]}"/>'] + \
         [f'<circle cx="{722 + i * 16}" cy="66" r="5" fill="{c["line"]}"/>' for i in range(3)] + \
         [f'<text x="918" y="71" text-anchor="middle" font-family="{MONO}" font-size="14" fill="{c["mut"]}">archive · index.html</text>',
          f'<rect x="718" y="98" width="400" height="34" rx="8" fill="{c["sunk"]}" stroke="{c["line"]}"/>',
          f'<circle cx="737" cy="114" r="6" fill="none" stroke="{c["mut"]}" stroke-width="1.8"/><path d="M741.5 118.5 L746 123" stroke="{c["mut"]}" stroke-width="1.8" stroke-linecap="round"/>',
          f'<text x="756" y="121" font-size="16" fill="{c["mut"]}">Search all conversations</text>']
    for i, (k, t, src, d) in enumerate(ROWS):
        y = 146 + i * 34
        s.append(f'<g id="row{i}"><rect x="718" y="{y}" width="400" height="28" rx="6" fill="{c["card"]}"/>'
                 f'<circle cx="732" cy="{y + 14}" r="5" fill="{c[k]}"/><text x="746" y="{y + 20}" font-size="17" fill="{c["fg"]}">{esc(t)}</text>'
                 f'<text x="1046" y="{y + 20}" text-anchor="end" font-size="14" fill="{c[k]}">{src}</text>'
                 f'<text x="1108" y="{y + 20}" text-anchor="end" font-family="{MONO}" font-size="14" fill="{c["mut"]}">{d}</text></g>')
    s.append('<g id="heat">' + ''.join(f'<rect x="{718 + i * 15.4:.1f}" y="324" width="12" height="12" rx="2.5" fill="{c["h"][v]}"/>' for i, v in enumerate(HEAT)) + '</g>')
    return '\n'.join(s) + '\n</svg>\n'

HERO_MOTION = dict(w=1200, h=400, dur=6.0,   # 首尾都是完成画面：先停住，淡出，再依次滑入，停到结束
                   layers=[dict(id=f'row{i}', pre=(1.2, 1.6), enter=(1.9 + i * 0.28, 2.7 + i * 0.28), dx=-36) for i in range(5)]
                          + [dict(id='heat', pre=(1.2, 1.6), enter=(3.5, 4.2), dx=0)])

# ───────────── 侧栏动画 1200×520 ─────────────
GROUPS = [('demo-proj', [('Switch prints to logging', '09-02'), ('Unit tests for the parser', '08-27'), ('Refactor config loading', '08-19')]),
          ('claude-ai-chats', [('[claude.ai] Trip budget', '06-12'), ('[claude.ai] Python GIL', '04-21')]),
          ('notes', [('Weekly report template', '08-30')])]

def sidebar(c):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" width="1200" height="520" font-family="{SANS}">',
         '<title>Old sessions reappear in the desktop app\'s Code sidebar</title><desc>Mock-up with made-up titles: after running the register command and reopening the desktop app, old sessions appear grouped by folder</desc>',
         f'<rect x="0.5" y="0.5" width="1199" height="519" rx="18" fill="{c["bg"]}" stroke="{c["line"]}"/>',
         # 左：终端
         f'<text x="56" y="72" font-size="20" font-weight="600" fill="{c["fg"]}">1 · Run</text>',
         f'<rect x="56" y="90" width="446" height="160" rx="12" fill="{c["card"]}" stroke="{c["line"]}"/>',
         f'<g id="cmd1"><text x="76" y="132" font-family="{MONO}" font-size="17" fill="{c["fg"]}"><tspan fill="{c["acc"]}">$ </tspan>python3 claude_archive.py \\</text></g>',
         f'<g id="cmd2"><text x="116" y="160" font-family="{MONO}" font-size="17" fill="{c["fg"]}">--import-claude-ai --write</text></g>',
         f'<g id="cmd3"><text x="76" y="198" font-family="{MONO}" font-size="17" fill="{c["fg"]}"><tspan fill="{c["acc"]}">$ </tspan>python3 claude_archive.py \\</text>'
         f'<text x="116" y="226" font-family="{MONO}" font-size="17" fill="{c["fg"]}">--register-desktop --write</text></g>',
         f'<text x="56" y="306" font-size="20" font-weight="600" fill="{c["fg"]}">2 · Reopen the desktop app</text>',
         f'<text x="56" y="340" font-size="18" fill="{c["fg2"]}">Old sessions come back, grouped by folder.</text>',
         f'<text x="56" y="368" font-size="18" fill="{c["fg2"]}">claude.ai chats get their own group,</text>',
         f'<text x="56" y="396" font-size="18" fill="{c["fg2"]}">ready to continue.</text>',
         f'<text x="56" y="470" font-size="15" fill="{c["mut"]}">Mock-up with made-up titles</text>',
         # 右：桌面应用窗口（侧栏 340 宽，放得下 16px 的标题和日期）
         f'<rect x="540" y="40" width="604" height="440" rx="14" fill="{c["card"]}" stroke="{c["line"]}"/>',
         f'<path d="M540 76 H1144" stroke="{c["line"]}"/>'] + \
        [f'<circle cx="{562 + i * 16}" cy="58" r="5" fill="{c["line"]}"/>' for i in range(3)] + \
        [f'<text x="842" y="63" text-anchor="middle" font-size="15" fill="{c["mut"]}">Claude · Code</text>',
         f'<path d="M540 76 H880 V479 H554 Q541 479 541 466 V76" fill="{c["side"]}"/><path d="M880 76 V480" stroke="{c["line"]}"/>',
         f'<rect x="554" y="88" width="312" height="34" rx="8" fill="{c["card"]}" stroke="{c["line"]}"/>',
         f'<text x="570" y="111" font-size="16" fill="{c["fg"]}">＋  New session</text>']
    y = 148; n = 0
    for g, items in GROUPS:
        s.append(f'<g id="g{n}"><text x="566" y="{y}" font-size="14" fill="{c["mut"]}">{g}</text><text x="854" y="{y}" text-anchor="end" font-size="14" fill="{c["mut"]}">{len(items)}</text></g>')
        n += 1; y += 28
        for t, d in items:
            k = 'chat' if t.startswith('[claude.ai]') else 'code'
            s.append(f'<g id="g{n}"><circle cx="570" cy="{y - 5}" r="4" fill="{c[k]}"/><text x="584" y="{y}" font-size="16" fill="{c["fg"]}">{esc(t)}</text>'
                     f'<text x="854" y="{y}" text-anchor="end" font-family="{MONO}" font-size="14" fill="{c["mut"]}">{d}</text></g>')
            n += 1; y += 30
        y += 6
    s.append(f'<rect x="554" y="{y - 14}" width="312" height="30" rx="7" fill="{c["sel"]}"/><text x="570" y="{y + 7}" font-size="16" fill="{c["fg"]}">New session</text>'
             f'<text x="854" y="{y + 7}" text-anchor="end" font-size="14" fill="{c["mut"]}">now</text>')
    for i, w in enumerate((70, 92, 56)):
        s.append(f'<rect x="904" y="{104 + i * 22}" width="{w * 2.3:.0f}" height="9" rx="4.5" fill="{c["sunk"]}"/>')
    return '\n'.join(s) + '\n</svg>\n', n

def sidebar_motion(n):
    # 首尾都是完成画面：先停住，清空，命令逐行打出，会话依次出现，停到结束
    L = [dict(id='cmd1', pre=(1.4, 1.8), reveal=(2.1, 2.8)), dict(id='cmd2', pre=(1.4, 1.8), reveal=(2.8, 3.5)), dict(id='cmd3', pre=(1.4, 1.8), reveal=(3.8, 4.8))]
    L += [dict(id=f'g{i}', pre=(1.4, 1.8), enter=(5.1 + i * 0.16, 5.7 + i * 0.16), dx=-24) for i in range(n)]
    return dict(w=1200, h=520, dur=9.6, layers=L)

# ───────────── 流程图 1200×420（静态 SVG，替代 README 里的 mermaid）─────────────
FLOW = {
    'en': dict(title='How claude-chat-archive works', desc='Three sources go into claude_archive.py on your machine; out come an offline web archive, Markdown for Claude, and sessions in the Claude desktop app.',
               src=[('code', 'Claude Code sessions', '~/.claude/projects'), ('chat', 'claude.ai export', 'data-…-batch-0000.zip'), ('gpt', 'ChatGPT export', 'conversations.json · .zip')],
               mid=('runs on your machine', 'redaction on by default'),
               out=[('Offline web archive', 'filters · charts · search'), ('Markdown for Claude', 'chunks + monthly indexes'), ('Claude desktop app', '--register-desktop')]),
    'zh': dict(title='claude-chat-archive 工作原理', desc='三个来源交给本机上的 claude_archive.py，产出离线网页存档、给 Claude 读的 Markdown，以及桌面应用里的会话。',
               src=[('code', 'Claude Code 会话', '~/.claude/projects'), ('chat', 'claude.ai 导出包', 'data-…-batch-0000.zip'), ('gpt', 'ChatGPT 导出包', 'conversations.json · .zip')],
               mid=('只在你的电脑上跑', '默认打码敏感信息'),
               out=[('离线网页存档', '筛选 · 图表 · 全文搜索'), ('给 Claude 读的 Markdown', '分块 + 月索引'), ('Claude 桌面应用', '--register-desktop')]),
}

def flow(c, lang):
    t = FLOW[lang]
    sans = SANS + (', &quot;Microsoft YaHei&quot;, &quot;PingFang SC&quot;, sans-serif' if lang == 'zh' else '')
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 420" width="1200" height="420" font-family="{sans}" role="img" aria-labelledby="t d">',
         f'<title id="t">{t["title"]}</title><desc id="d">{t["desc"]}</desc>',
         f'<rect x="0.5" y="0.5" width="1199" height="419" rx="18" fill="{c["bg"]}" stroke="{c["line"]}"/>']
    ys = [48, 164, 280]   # 三行卡片的上沿，卡片高 92
    for i, (k, a, b) in enumerate(t['src']):   # 左：来源 → 中
        y = ys[i] + 46
        s.append(f'<path d="M348 {y} C 400 {y}, 400 210, 446 210" fill="none" stroke="{c[k]}" stroke-width="2.5"/>')
    for i in range(3):   # 中 → 右：输出
        y = ys[i] + 46
        s.append(f'<path d="M754 210 C 800 210, 800 {y}, 846 {y}" fill="none" stroke="{c["acc"]}" stroke-width="2.5"/>'
                 f'<circle cx="846" cy="{y}" r="4.5" fill="{c["acc"]}"/>')
    for i, (k, a, b) in enumerate(t['src']):
        y = ys[i]
        s.append(f'<rect x="48" y="{y}" width="300" height="92" rx="12" fill="{c["card"]}" stroke="{c["line"]}"/>'
                 f'<rect x="68" y="{y + 25}" width="14" height="14" rx="3.5" fill="{c[k]}"/>'
                 f'<text x="94" y="{y + 38}" font-size="21" font-weight="600" fill="{c["fg"]}">{a}</text>'
                 f'<text x="68" y="{y + 70}" font-family="{MONO}" font-size="16" fill="{c["mut"]}">{esc(b)}</text>')
    s.append(f'<rect x="446" y="140" width="308" height="140" rx="14" fill="{c["wash"]}" stroke="{c["acc"]}" stroke-width="2"/>'
             f'<text x="600" y="190" text-anchor="middle" font-family="{MONO}" font-size="23" font-weight="700" fill="{c["acc"]}">claude_archive.py</text>'
             f'<text x="600" y="228" text-anchor="middle" font-size="19" fill="{c["fg"]}">{t["mid"][0]}</text>'
             f'<text x="600" y="258" text-anchor="middle" font-size="17" fill="{c["fg2"]}">{t["mid"][1]}</text>')
    for i, (a, b) in enumerate(t['out']):
        y = ys[i]
        mono = b.startswith('--')
        s.append(f'<rect x="852" y="{y}" width="300" height="92" rx="12" fill="{c["card"]}" stroke="{c["line"]}"/>'
                 f'<text x="872" y="{y + 38}" font-size="21" font-weight="600" fill="{c["fg"]}">{a}</text>'
                 f'<text x="872" y="{y + 70}" font-size="{16 if mono else 18}" fill="{c["fg2"]}"' + (f' font-family="{MONO}"' if mono else '') + f'>{b}</text>')
    return '\n'.join(s) + '\n</svg>\n'

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
    if (l.pre && t < (l.enter || l.reveal)[0]) { o = 1 - ease((t - l.pre[0]) / (l.pre[1] - l.pre[0])); dx = 0; clip = 0; }
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
    pal = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)   # 第一帧是完成画面、颜色最全，拿它定调色板，所有帧共用
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
            for lang, suffix in (('en', ''), ('zh', '-zh')):
                open(f'{OUT}/flow{suffix}-{th}.svg', 'w', encoding='utf-8').write(flow(c, lang))
        b.close()

if __name__ == '__main__': main()
