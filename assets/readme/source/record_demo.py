"""把存档网页的一段真实操作录成 GIF：首页 → 输入过滤 → 回车全文搜索 → 打开结果 → 会话页里 j / k 跳提问。
用法：python3 assets/readme/source/record_demo.py <导出目录> <输出.gif> [light|dark] [搜索词]
<导出目录> 用 make_demo_data.py 造的演示数据导出，别用真实对话。
"""
import io, os, sys
from PIL import Image
from playwright.sync_api import sync_playwright

W, H = 1120, 700

def main(out, gif, theme='light', query='config'):
    frames, durs = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_page(viewport={'width': W, 'height': H}, color_scheme=theme)
        def snap(ms):   # 截一帧，这一帧停 ms 毫秒；画面和上一帧一样就只把停留时间加到上一帧
            im = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
            if frames and im.tobytes() == frames[-1].tobytes(): durs[-1] += ms
            else: frames.append(im); durs.append(ms)
        def settle(n=6, ms=70):   # 滚动、展开这类过渡，连拍几帧
            for _ in range(n): page.wait_for_timeout(ms); snap(ms)
        page.goto('file://' + os.path.abspath(out) + '/index.html'); page.wait_for_timeout(500); snap(1400)
        page.click('#q'); snap(300)
        for ch in query: page.keyboard.type(ch); page.wait_for_timeout(140); snap(140)
        settle(); snap(1100)
        page.keyboard.press('Enter'); settle(); snap(1500)
        hit = page.locator('#ft a').first
        if hit.count():
            hit.click(); page.wait_for_load_state(); page.wait_for_timeout(400); settle(); snap(1200)
            for key in ('j', 'j', 'k'):
                page.keyboard.press(key); settle(8, 60); snap(900)
        snap(800)
        b.close()
    pal = max(frames, key=lambda f: len(f.resize((160, 95)).getcolors(160 * 95))).quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(gif, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True, disposal=1)
    print(f'{gif}: {len(frames)} 帧, {sum(durs) / 1000:.1f} 秒, {os.path.getsize(gif) // 1024} KB')

if __name__ == '__main__': main(*sys.argv[1:])
