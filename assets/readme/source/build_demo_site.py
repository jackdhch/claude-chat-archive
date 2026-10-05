"""造演示数据 → 英文界面导出 → 按规则打主题 → 再导出。README 的截图和动画都用它的产物。
用法：python3 assets/readme/source/build_demo_site.py <工作目录>     # 产物在 <工作目录>/out
全程用假 HOME，不读真实 ~/.claude。
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PROJ_TOPIC = {'web-dashboard': 'Frontend', 'ml-experiments': 'Machine learning', 'infra': 'DevOps',
              'rust-cli': 'Rust', 'dotfiles': 'Tooling', 'blog': 'Writing'}
WORDS = [('Writing', r'email|letter|readme|cover|interview|translate|essay|blog|post|draft|toast'),
         ('Planning', r'trip|plan|budget|schedule|itinerary|names'),
         ('Learning', r'explain|learn|lifetimes|gradient|what is|how does|understand'),
         ('Programming', r'postgres|mysql|sql|regex|python|script|code|api|bug|csv|json')]
TOPICS = [{'name': n} for n in ['Frontend', 'Machine learning', 'DevOps', 'Rust', 'Tooling', 'Writing', 'Learning', 'Planning', 'Programming', 'Other']]

def run(*args, env):
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'claude_archive.py'), *args], env=env, capture_output=True, text=True)
    if r.returncode: sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
    return r.stdout

def rows(path):
    s = open(path, encoding='utf-8').read(); return json.loads(re.search(r'window\.D=(.*?);?\s*$', s, re.S)[1])

def main(work):
    work = os.path.abspath(work)
    subprocess.run([sys.executable, os.path.join(HERE, 'make_demo_data.py'), work], check=True, capture_output=True)
    cfg = os.path.join(work, 'config.json'); c = json.load(open(cfg)); c['language'] = 'en'; json.dump(c, open(cfg, 'w'), indent=1)
    env = {k: v for k, v in os.environ.items() if k not in ('APPDATA', 'LOCALAPPDATA')}
    env.update(HOME=work + '/home', XDG_CONFIG_HOME=work + '/xdg/config', XDG_DATA_HOME=work + '/xdg/data')
    run('--config', cfg, env=env)
    out = c['out_dir'] if os.path.isabs(c['out_dir']) else os.path.join(work, c['out_dir'])
    tags = {'_topics': TOPICS}
    for p in (out + '/data.js', out + '/chatgpt/data.js'):
        if not os.path.exists(p): continue
        for r in rows(p):
            t = PROJ_TOPIC.get(os.path.basename(r.get('proj') or '')) if r.get('src') == 'cc' else None
            t = t or next((n for n, w in WORDS if re.search(w, r.get('t', ''), re.I)), 'Other')
            tags[r['id']] = {'t': [t], 's': ''}   # 一句话总结留空：列表第二行显示提问开头
    tf = os.path.join(work, 'topics-demo.json'); json.dump(tags, open(tf, 'w'), ensure_ascii=False)
    run('--config', cfg, '--merge-topics', tf, env=env)
    print(run('--config', cfg, env=env).strip().splitlines()[-1])
    print(f'{len(tags) - 1} conversations tagged → {out}/index.html')

if __name__ == '__main__': main(sys.argv[1])
