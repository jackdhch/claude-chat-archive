#!/usr/bin/env bash
# 用 tests/fixtures 的假数据在临时 HOME 下跑 claude_archive.py，逐项断言。
# 用法：bash tests/run_tests.sh        （KEEP=1 保留临时目录便于排查；PYTHON=python3.9 指定解释器）
# 不联网、不碰真实 HOME：HOME / XDG_* 全指向临时目录。
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
FX="$ROOT/tests/fixtures"
[ -f "$FX/expected.json" ] || { echo "缺 $FX/expected.json，先跑 python3 tests/make_fixtures.py"; exit 1; }
T=$(mktemp -d "${TMPDIR:-/tmp}/claude-archive-test.XXXXXX")
[ "${KEEP:-0}" = 1 ] && echo "临时目录：$T" || trap 'rm -rf "$T"' EXIT

export HOME="$T/home" XDG_CONFIG_HOME="$T/xdg/config" XDG_DATA_HOME="$T/xdg/data"
unset APPDATA LOCALAPPDATA
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
cp -R "$FX/home/." "$HOME/"; cp -R "$FX/Downloads" "$HOME/Downloads"; cp "$FX/literals.txt" "$HOME/literals.txt"

LIT_CFG=$("$PY" -c "import json;print(json.load(open('$FX/expected.json'))['secrets']['literal_cfg'])")
CFG="$T/config.json"
cat > "$CFG" <<EOF
{
  "out_dir": "$T/out",
  "claude_code_roots": ["~/.claude/projects"],
  "extra_backup_roots": ["~/session-backup"],
  "claude_ai_zips": ["~/Downloads/data-*-batch-*.zip"],
  "chatgpt_zips": ["~/Downloads/*.zip"],
  "desktop_meta_globs": ["~/desktop-meta/claude-code-sessions/**/local_*.json"],
  "redact": true,
  "redact_literals": ["$LIT_CFG"],
  "redact_literal_files": ["~/literals.txt"],
  "doc_token_limit": 4000
}
EOF

PASS=0; FAIL=0; FAILS=()
ok()   { PASS=$((PASS + 1)); echo "  通过  $1"; }
bad()  { FAIL=$((FAIL + 1)); FAILS+=("$1"); echo "  失败  $1"; }
run()  { "$PY" "$ROOT/claude_archive.py" "$@" >"$T/last.log" 2>&1; echo $?; }
expect_code() {   # 期望退出码 名字 参数...
  local want=$1 name=$2; shift 2; local got; got=$(run "$@")
  if [ "$want" = "!0" ]; then [ "$got" != 0 ] && ok "$name（退出码 $got）" || { bad "$name：期望非 0，实际 0"; tail -5 "$T/last.log"; }
  else [ "$got" = "$want" ] && ok "$name" || { bad "$name：期望退出码 $want，实际 $got"; tail -15 "$T/last.log"; }; fi
}
# 检查一份导出产物：check_out 目录 redact|raw
check_out() {
  "$PY" - "$1" "$2" "$FX/expected.json" <<'PY'
import glob, html, json, os, re, stat, sys
out, mode, E = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3], encoding='utf-8'))
res = []
def chk(name, cond, detail=''): res.append((bool(cond), name + ('' if cond else f'：{detail}')))
def rd(p): return open(p, encoding='utf-8', errors='replace').read()
def jsarr(p, var):
    s = rd(p); m = re.search(r'window\.' + var + r'=(.*?);\n', s, re.S); return json.loads(m[1])
# 统计与自查
st = json.load(open(out + '/stats.json', encoding='utf-8'))
for k, e in [('CC主会话', 'cc_sessions'), ('ai会话', 'ai_convs'), ('ai消息', 'ai_msgs'), ('CC显示', 'cc_shown_rows'),
             ('子agent总数', 'cc_subagents'), ('workflow', 'cc_workflows'), ('独立重数·人工提问', 'cc_prompts'), ('网页·用户块', 'cc_prompts')]:
    chk(f'stats.json {k} = {E[e]}', st.get(k) == E[e], f'实际 {st.get(k)}')
chk('子 agent 全部挂上', st.get('子agent·未挂上', 0) == 0, st.get('子agent·未挂上'))
chk('report.txt 写着检查全部通过', '检查全部通过' in rd(out + '/report.txt'), rd(out + '/report.txt')[-300:])
# 首页数据
D = jsarr(out + '/data.js', 'D'); cc = [d for d in D if d['src'] == 'cc']; ai = [d for d in D if d['src'] == 'ai']
for name, got, want in [('data.js cc 会话数', len(cc), E['cc_sessions']), ('data.js cc 消息数', sum(d['nmsg'] for d in cc), E['cc_msgs']),
                        ('data.js cc 提问数', sum(d['nq'] for d in cc), E['cc_prompts']), ('data.js ai 会话数', len(ai), E['ai_convs']),
                        ('data.js ai 消息数', sum(d['nmsg'] for d in ai), E['ai_msgs']), ('data.js ai 提问数', sum(d['nq'] for d in ai), E['ai_prompts'])]:
    chk(f'{name} = {want}', got == want, f'实际 {got}')
byid = {d['id']: d for d in D}
for u, n in E['ai_branches'].items(): chk(f'claude.ai 分支段数 = {n}', byid.get('ai-' + u, {}).get('branches') == n, byid.get('ai-' + u, {}).get('branches'))
for u, n in E['ai_files'].items():
    fs = glob.glob(f'{out}/files/ai-{u}/*'); chk(f'claude.ai 产出文件 = {n} 个', len(fs) == n, [os.path.basename(f) for f in fs])
chk('桌面应用手动标题生效', any('桌面手动标题' in d['t'] and d.get('star') for d in cc), [d['t'] for d in cc])
# 续接去重：前缀每条在网页里只有一个锚点，在 docs 里只出现一次
pages = glob.glob(out + '/s/**/*.html', recursive=True); allh = ''.join(rd(p) for p in pages)
for u in E['prefix_uuids']: chk(f'续接前缀 {u[:8]} 网页里只渲染一次', allh.count(f'id="m-{u}"') == 1, allh.count(f'id="m-{u}"'))
mdcc = ''.join(rd(p) for p in glob.glob(out + '/docs/cc/*.md'))
for m in E['once_markers']: chk(f'docs 里 {m} 恰好出现 1 次', mdcc.count(m) == 1, mdcc.count(m))
md_all = glob.glob(out + '/docs/**/*.md', recursive=True)
chk('docs 没有未填充的 {ch}/{pq} 模板占位', not [p for p in md_all if '{ch}' in rd(p) or '{pq}' in rd(p)], [os.path.relpath(p, out) for p in md_all if '{ch}' in rd(p)][:3])
# 文档大小
lim = 4000
def est(s): n = sum(1 for c in s if ord(c) > 127); return n * 1.5 + (len(s) - n) / 3 + s.count('\n') * 3
over = [(os.path.relpath(p, out), round(est(rd(p)))) for p in md_all if est(rd(p)) > lim]
chk(f'docs 每个 md 估算 token ≤ {lim}', not over, over[:5])
chk('长会话被切成多块（存在 -p2.md）', glob.glob(out + '/docs/cc/*-p2.md'), '没有')
# claude.ai 内容
aih = ''.join(rd(p) for p in glob.glob(out + '/s/ai-*.html')) + ''.join(rd(p) for p in glob.glob(out + '/docs/ai/*.md'))
chk('占位符已替换', E['placeholder'] not in aih, '仍有残留')
fz = ''.join(rd(p) for p in glob.glob(out + '/files/**/*', recursive=True) if os.path.isfile(p))
for m in E['must_contain']: chk(f'产物里能找到 {m}', m in fz or m in aih, '找不到')
chk('粘贴的图片落盘到 img/', glob.glob(out + '/img/*.png'), '没有')
# 脱敏
texts = {os.path.relpath(p, out): rd(p) for p in glob.glob(out + '/**/*', recursive=True)
         if os.path.isfile(p) and p.endswith(('.html', '.js', '.md', '.txt', '.json', '.svg', '.css'))}
for k, v in E['secrets'].items():
    hit = [f for f, s in texts.items() if v in s or v in html.unescape(s)]
    if mode == 'redact': chk(f'脱敏后扫不到 {k}', not hit, hit[:3])
    else: chk(f'不脱敏时能扫到 {k}', hit, '一处都没有')
# ChatGPT（chatgpt/ 目录）：按 make_fixtures.py 的设计对账
G = jsarr(out + '/chatgpt/data.js', 'D'); gid = E['gpt_ids']
chk('根目录 data.js 里没有 gpt 会话', not [d for d in D if d['src'] == 'gpt'], [d['id'] for d in D if d['src'] == 'gpt'][:3])
for k, e in [('gpt会话', 'gpt_convs'), ('gpt导出包', 'gpt_zips'), ('gpt原始会话(含跨包重复)', 'gpt_raw'), ('gpt节点', 'gpt_nodes'), ('gpt空节点(message为null)', 'gpt_null'), ('gpt显示', 'gpt_shown'),
             ('gpt提问', 'gpt_prompts'), ('gpt主线显示', 'gpt_main_shown'), ('gpt自定义指令(页首)', 'gpt_ctx'), ('网页·ChatGPT用户块', 'gpt_prompts')]:
    chk(f'stats.json {k} = {E[e]}', st.get(k) == E[e], f'实际 {st.get(k)}')
for r, n in E['gpt_hidden'].items(): chk(f'stats.json 隐藏「{r}」= {n}', st.get('gpt隐藏:' + r) == n, st.get('gpt隐藏:' + r))
chk(f'隐藏合计 = {E["gpt_hidden_total"]}', sum(v for k, v in st.items() if k.startswith('gpt隐藏:')) == E['gpt_hidden_total'], '')
chk('全部节点 = 显示 + 各类隐藏 + 自定义指令 + null', st['gpt节点'] == st['gpt显示'] + st['gpt自定义指令(页首)'] + st['gpt空节点(message为null)'] + E['gpt_hidden_total'], '')
chk('chatgpt/data.js 会话数、来源、消息数、提问数', len(G) == E['gpt_convs'] and all(d['src'] == 'gpt' for d in G) and sum(d['nmsg'] for d in G) == E['gpt_shown'] and sum(d['nq'] for d in G) == E['gpt_prompts'],
    (len(G), sum(d['nmsg'] for d in G), sum(d['nq'] for d in G)))
gb = {d['id']: d for d in G}
chk(f'ChatGPT 分支段数 = 2', gb.get('gpt-' + gid['full'], {}).get('branches') == 2, gb.get('gpt-' + gid['full'], {}).get('branches'))
chk('自定义 GPT（gizmo_id）当项目', gb.get('gpt-' + gid['plain'], {}).get('proj') == 'GPT g-p-fakegizmo123456', gb.get('gpt-' + gid['plain'], {}).get('proj'))
chk('title 为 null 时用第一问做标题', gb.get('gpt-' + gid['plain'], {}).get('t', '').startswith('GPT-G2-Q'), gb.get('gpt-' + gid['plain'], {}).get('t'))
chk('create/update_time 为 null 时用消息时间', gb.get('gpt-' + gid['plain'], {}).get('start', '').startswith('2026-03-'), gb.get('gpt-' + gid['plain'], {}).get('start'))
chk('模型来自消息的 model_slug', gb.get('gpt-' + gid['full'], {}).get('models') == ['gpt-5', 'gpt-5-thinking'], gb.get('gpt-' + gid['full'], {}).get('models'))
gpages = {k: out + f'/chatgpt/s/gpt-{v}.html' for k, v in gid.items()}
chk('每个 ChatGPT 会话一个页面', all(os.path.exists(p) for p in gpages.values()), [k for k, p in gpages.items() if not os.path.exists(p)])
gall = ''.join(rd(p) for p in gpages.values()) + ''.join(rd(p) for p in glob.glob(out + '/docs/gpt/*.md')) + ''.join(rd(p) for p in glob.glob(out + '/files/gpt-*/*'))
for m in E['gpt_must_contain']: chk(f'ChatGPT 产物里能找到 {m}', m in gall, '找不到')
alltxt = ''.join(texts.values())
for m in E['gpt_must_not']: chk(f'{m} 不出现（隐藏 / 被新版覆盖）', m not in alltxt, '出现了')
fh = rd(gpages['full'])
chk('自定义指令在会话页只出现一次', fh.count('CUSTOM-INSTR-MARK') == 1, fh.count('CUSTOM-INSTR-MARK'))
chk('current_node 指向的那条是主线，最新的重新生成版在分支里', re.search(r'class="br">(?:(?!</details>).)*GPT-A2-REGEN', fh, re.S) and not re.search(r'class="br">(?:(?!</details>).)*GPT-A2 收到', fh, re.S), '分支/主线颠倒')
chk('编辑重发的旧问法在分支里', re.search(r'class="br">(?:(?!</details>).)*GPT-OLD-Q', fh, re.S), '')
chk('代码 / 执行结果 / 思考做成折叠条', all(f'<span class="tn">{t}</span>' in fh for t in ('代码', '执行结果', '思考', 'Canvas', '网页引用')), '')
im = re.findall(r'<img src="\.\./img/([0-9a-f]+\.png)"', fh) + re.findall(r'<img src="\.\./img/([0-9a-f]+\.png)"', rd(gpages['plain']))
chk('图片出现在会话页（含 dalle-generations 里的）且文件存在', len(im) == 2 and all(os.path.exists(out + '/chatgpt/img/' + f) for f in im), im)
cf = glob.glob(out + f'/files/gpt-{gid["full"]}/*')
chk('Canvas 文件存在且是文档正文', len(cf) == E['gpt_files'][gid['full']] and 'CANVAS-MARK' in rd(cf[0]) and cf[0].endswith('.md'), cf)
chk('docs/gpt 每个对话一份、有月索引', len(glob.glob(out + '/docs/gpt/*.md')) >= E['gpt_convs'] and os.path.exists(out + '/docs/index/gpt-2026-03.md') and 'ChatGPT' in rd(out + '/docs/README.md'), '')
chk('两个首页互相有链接', 'chatgpt/index.html' in rd(out + '/index.html') and '../index.html' in rd(out + '/chatgpt/index.html'), '')
ch = rd(out + '/chatgpt/index.html')
chk('ChatGPT 首页标题、样式脚本引用上一级、数据文件在本目录', '<title>ChatGPT 对话存档</title>' in ch and 'href="../style.css"' in ch and 'src="../app.js"' in ch and 'src="data.js"' in ch, '')
chk('ChatGPT 会话页的返回链接回 chatgpt 首页', '<a href="../index.html">← ChatGPT 对话存档</a>' in fh and 'href="../../style.css"' in fh, '')
chk('chatgpt/ 下没有复制一份 css/js', not [f for f in ('style.css', 'app.js', 'theme.js', 'nav.js') if os.path.exists(out + '/chatgpt/' + f)], '')
chk('chatgpt/search.js 只含 ChatGPT 页', 'GPT-Q1' in rd(out + '/chatgpt/search.js') and 'GPT-Q1' not in rd(out + '/search.js') and 'BRANCH-Q1' not in rd(out + '/chatgpt/search.js'), '')
# 仅限本机：权限、无外链脚本
chk('输出目录权限 700', stat.S_IMODE(os.stat(out).st_mode) == 0o700, oct(stat.S_IMODE(os.stat(out).st_mode)))
loose = [f for f in texts if stat.S_IMODE(os.stat(os.path.join(out, f)).st_mode) & 0o077]
chk('输出文件对其他用户不可读', not loose, loose[:3])
ext = [f for f, s in texts.items() if f.endswith('.html') and not f.startswith('files/') and re.search(r'<(?:script|link)[^>]+(?:src|href)="(?:https?:)?//', s)]
chk('网页不加载外部脚本/样式', not ext, ext[:3])
remote = [f for f, s in texts.items() if f.endswith('.html') and not f.startswith('files/') and re.search(r'<(?:img|iframe|video|audio|source)[^>]+src="(?:https?:)?//', s)]
chk('对话里的远程图片不会被自动加载', not remote, remote[:3])
nocsp = [f for f, s in texts.items() if f.endswith('.html') and not f.startswith('files/') and 'Content-Security-Policy' not in s]
chk('每个网页都带 CSP（不许连外网）', not nocsp, nocsp[:3])
empty = [f for f, s in texts.items() if f.startswith('docs/') and f.endswith('.md') and ('{pq}' in s or s.rstrip().endswith('{ch}'))]
chk('docs 里的 md 都有正文（没有字面 {pq}/{ch}）', not empty, empty[:3])
arts = [f for f in texts if f.startswith('files/') and '说明文档' in f]
chk('artifact 更新后文件名仍是创建时的标题', arts, [f for f in texts if f.startswith('files/')][:5])
for ok, name in res: print(('  通过  ' if ok else '  失败  ') + name)
sys.exit(0 if all(ok for ok, _ in res) else 1)
PY
}
tally() { while IFS= read -r l; do echo "$l"; case "$l" in "  通过  "*) PASS=$((PASS + 1));; "  失败  "*) FAIL=$((FAIL + 1)); FAILS+=("${l#  失败  }");; esac; done; }

echo "== 1. 自检 / 配置 / 体检"
expect_code 0 "--selftest" --selftest
expect_code 0 "--init-config 写默认配置" --init-config
grep -Eq "探测到 ChatGPT 导出包 [0-9]+ 个" "$T/last.log" && ok "--init-config 报告探测到几个 ChatGPT 包" || bad "--init-config 没报告 ChatGPT 包"
[ -f "$XDG_CONFIG_HOME/claude-archive/config.json" ] && "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));assert '~/.claude/projects' in d['claude_code_roots'] and d['redact'] is True" "$XDG_CONFIG_HOME/claude-archive/config.json" \
  && ok "默认配置在 XDG 路径，含 ~/.claude/projects 且 redact=true" || bad "默认配置位置或内容不对"
expect_code 0 "--doctor" --doctor --config "$CFG"
grep -q "markdown" "$T/last.log" && ok "--doctor 报告 markdown-it 状态" || bad "--doctor 输出里没提 markdown-it"
grep -q "找到 ChatGPT 导出包 2 个，共 5 段对话" "$T/last.log" && ok "--doctor 报告 ChatGPT 包 2 个、5 段对话（claude.ai 的 zip 按内容被排除）" || { bad "--doctor 的 ChatGPT 包数量不对"; grep ChatGPT "$T/last.log"; }
echo '{"out_dir": 1}' > "$T/badcfg.json"; expect_code 2 "类型错误的配置 → 退出码 2" --doctor --config "$T/badcfg.json"
expect_code 2 "不存在的配置 → 退出码 2" --config "$T/nope.json"

echo "== 2. 正式导出（redact=true）"
expect_code 0 "导出 redact=true" --config "$CFG" --out "$T/out_r"
[ -d "$T/out_r" ] && tally < <(check_out "$T/out_r" redact)

echo "== 3. 正式导出（--no-redact）"
expect_code 0 "导出 --no-redact" --config "$CFG" --out "$T/out_n" --no-redact
[ -d "$T/out_n" ] && tally < <(check_out "$T/out_n" raw)

echo "== 4. 重复导出同一目录（旧产物进 .prev）"
expect_code 0 "再导出一次 out_r" --config "$CFG" --out "$T/out_r"
[ -d "$T/out_r.prev" ] && ok "上一版留在 .prev" || bad "没有 .prev"

echo "== 5. 同步盘 / git 工作区保护"
if command -v git >/dev/null; then
  mkdir -p "$T/repo" && git -C "$T/repo" init -q
  expect_code '!0' "输出目录在 git 工作区里被拒绝" --config "$CFG" --out "$T/repo/out"
  [ ! -e "$T/repo/out/index.html" ] && ok "git 工作区里没写出产物" || bad "git 工作区里写出了产物"
else echo "  跳过  没有 git"; fi
expect_code '!0' "路径含 OneDrive 被拒绝" --config "$CFG" --out "$T/OneDrive/out"
expect_code '!0' "路径含 坚果云 被拒绝" --config "$CFG" --out "$T/我的坚果云/out"
mkdir -p "$T/OneDrive" && ln -s "$T/OneDrive" "$T/link-to-sync"
expect_code '!0' "经符号链接指进 OneDrive 也被拒绝" --config "$CFG" --out "$T/link-to-sync/out2"
[ ! -e "$T/OneDrive/out2" ] && ok "同步盘里没写出产物" || bad "经符号链接写进了同步盘"
mkdir -p "$T/shell/.git/info"
expect_code 0 "只有空壳 .git（不是仓库）不误拒" --config "$CFG" --out "$T/shell/out"
expect_code 0 "--allow-synced-output 可强制" --config "$CFG" --out "$T/OneDrive/out" --allow-synced-output
mkdir -p "$T/notours" && echo keep > "$T/notours/keep.txt"
expect_code '!0' "不是本工具产物的非空目录被拒绝" --config "$CFG" --out "$T/notours"
[ -f "$T/notours/keep.txt" ] && ok "别人的文件没被动" || bad "别人的文件被删/移走了"

echo "== 5b. 没有 ChatGPT 包时不生成 chatgpt/"
sed 's#"~/Downloads/\*.zip"#"~/Downloads/data-*-batch-*.zip"#' "$CFG" > "$T/cfg_nogpt.json"   # 通配只匹配到 claude.ai 的包：内容不是 ChatGPT，必须被排除
expect_code 0 "只有 claude.ai 包时导出" --config "$T/cfg_nogpt.json" --out "$T/out_g0"
expect_code 0 "--doctor（没有 ChatGPT 包）" --doctor --config "$T/cfg_nogpt.json"
grep -q "找到 ChatGPT 导出包 0 个" "$T/last.log" && ok "--doctor 报告 0 个 ChatGPT 包" || bad "--doctor 没报告 0 个"
[ ! -e "$T/out_g0/chatgpt" ] && ! ls "$T/out_g0/docs/gpt" "$T/out_g0/files"/gpt-* >/dev/null 2>&1 && ok "没有 chatgpt/、docs/gpt、files/gpt-*" || bad "没有 ChatGPT 包却生成了 ChatGPT 产物"
! grep -q "chatgpt/index.html" "$T/out_g0/index.html" && ok "Claude 首页不显示 ChatGPT 链接" || bad "Claude 首页多了 ChatGPT 链接"
grep -q "检查全部通过" "$T/out_g0/report.txt" && ok "没有 ChatGPT 包时检查也全过" || bad "没有 ChatGPT 包时检查没过"

echo "== 6. AI 标题 / 主题缓存"
SID1=$("$PY" -c "import json;print(json.load(open('$FX/expected.json'))['session_ids']['basic'])")
expect_code 0 "--dump-prompts" --config "$CFG" --dump-prompts "$T/dump"
ls "$T/dump"/prompts-*.jsonl >/dev/null 2>&1 && ok "写出 prompts-*.jsonl" || bad "没有 prompts-*.jsonl"
U1=$(head -1 "$T/dump"/prompts-00.jsonl 2>/dev/null | "$PY" -c "import json,sys;print(json.loads(sys.stdin.read())['id'])" 2>/dev/null)
grep -q GPT-Q1 "$T/dump"/prompts-*.jsonl && ok "--dump-prompts 含 ChatGPT 的提问" || bad "--dump-prompts 没有 ChatGPT 的提问"
GU=$(grep -h GPT-Q1 "$T/dump"/prompts-*.jsonl | head -1 | "$PY" -c "import json,sys;print(json.loads(sys.stdin.read())['id'])")
GID=$("$PY" -c "import json;print(json.load(open('$FX/expected.json'))['gpt_ids']['full'])")
echo "{\"$U1\": \"TITLE-MERGE-MARK\", \"$GU\": \"GPT-TITLE-MERGE-MARK\"}" > "$T/titles.json"
echo "{\"cc-$SID1\": {\"t\": [\"演示主题\"], \"s\": \"TOPIC-MERGE-MARK\"}, \"gpt-$GID\": {\"t\": [\"演示主题\"], \"s\": \"GPT-TOPIC-MERGE-MARK\"}, \"_topics\": [{\"name\": \"演示主题\"}]}" > "$T/topics.json"
expect_code 0 "--merge-titles" --config "$CFG" --merge-titles "$T/titles.json"
expect_code 0 "--merge-topics" --config "$CFG" --merge-topics "$T/topics.json"
expect_code 0 "合并后再导出" --config "$CFG" --out "$T/out_r"
grep -q TITLE-MERGE-MARK -r "$T/out_r/s" "$T/out_r/data.js" && ok "AI 小标题进了产物" || bad "AI 小标题没进产物"
grep -q TOPIC-MERGE-MARK "$T/out_r/data.js" && ok "主题总结进了 data.js" || bad "主题总结没进 data.js"
grep -q GPT-TITLE-MERGE-MARK -r "$T/out_r/chatgpt/s" && ok "ChatGPT 提问的 AI 小标题进了会话页" || bad "ChatGPT 的 AI 小标题没生效"
grep -q GPT-TOPIC-MERGE-MARK "$T/out_r/chatgpt/data.js" && ! grep -q GPT-TOPIC-MERGE-MARK "$T/out_r/data.js" && ok "ChatGPT 主题总结进了 chatgpt/data.js（不在根 data.js）" || bad "ChatGPT 主题总结位置不对"
expect_code 0 "--dump-convs" --config "$CFG" --out "$T/out_r" --dump-convs "$T/dump2"
ls "$T/dump2"/in-*.jsonl >/dev/null 2>&1 && ! grep -q "cc-$SID1" "$T/dump2"/in-*.jsonl && ok "dump-convs 跳过已打标签的会话" || bad "dump-convs 结果不对"
grep -q '"id": "gpt-' "$T/dump2"/in-*.jsonl && ! grep -q "gpt-$GID" "$T/dump2"/in-*.jsonl && ok "dump-convs 含 ChatGPT 会话（key 是 gpt-<id>），已打标签的跳过" || bad "dump-convs 的 ChatGPT 会话不对"
[ -z "$(ls -A "$T/xdg/data/claude-archive" 2>/dev/null | grep -v -E '^(titles|topics)\.json$')" ] && [ -f "$T/xdg/data/claude-archive/titles.json" ] && ok "缓存在 XDG_DATA_HOME/claude-archive/" || bad "缓存位置不对"

echo "== 7. 补登记到桌面应用 Code 界面"
# 造一个续接会话：整份复制 basic 再加一行更晚的提问 → basic 被它完整包含，它也有九成以上和 basic 相同（互相包含）
"$PY" - "$HOME/.claude/projects" "$FX/expected.json" <<'PY'
import glob, json, sys
E = json.load(open(sys.argv[2], encoding='utf-8'))['session_ids']; src = glob.glob(f"{sys.argv[1]}/*/{E['basic']}.jsonl")[0]
rows = [json.loads(l) for l in open(src, encoding='utf-8') if l.strip()]; cwd = next(r['cwd'] for r in rows if r.get('cwd'))
rows.append({'type': 'user', 'uuid': '00000000-0000-4000-8000-00000000c0de', 'timestamp': '2099-01-01T00:00:00.000Z', 'sessionId': 'cont-basic',
             'cwd': cwd, 'isSidechain': False, 'message': {'role': 'user', 'content': 'CONT-MARK 接着聊'}})
with open(src.rsplit('/', 1)[0] + '/5e55c0de-0000-4000-8000-000000000001.jsonl', 'w', encoding='utf-8') as f: f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
PY
DM="$HOME/desktop-meta/claude-code-sessions"; nreg() { find "$DM" -name 'local_*.json' | wc -l | tr -d ' '; }
N0=$(nreg)
expect_code 0 "--register-desktop（只列出）" --config "$CFG" --register-desktop
N=$(sed -n 's/.*还没登记 \([0-9]*\) 个.*/\1/p' "$T/last.log")
[ "$(nreg)" = "$N0" ] && ok "不加 --write 不写文件" || bad "不加 --write 也写了文件"
[ "${N:-0}" -gt 0 ] && ok "列出 $N 个未登记会话" || bad "没列出未登记会话"
expect_code 0 "--register-desktop --write" --config "$CFG" --register-desktop --write
[ "$(nreg)" = "$((N0 + N))" ] && ok "写入 $N 个登记文件" || bad "登记文件数不对：$(nreg)，期望 $((N0 + N))"
"$PY" - "$DM" "$HOME/.claude/projects" "$FX/expected.json" <<'PY' && ok "登记文件字段齐全、指向本机会话、不重复；被续接的旧会话登记为归档" || bad "登记文件内容不对"
import glob, json, os, sys
js = [json.load(open(p, encoding='utf-8')) for p in glob.glob(sys.argv[1] + '/**/local_*.json', recursive=True)]
ids = [j['cliSessionId'] for j in js]; assert len(ids) == len(set(ids)), ids
for j in js:
    if 'sessionId' not in j: continue   # 假数据里原有的那条
    assert j['sessionId'].startswith('local_') and j['cwd'] and j['createdAt'] <= j['lastActivityAt'] and j['title'], j
    assert glob.glob(f"{sys.argv[2]}/*/{j['cliSessionId']}.jsonl"), j   # 不登记备份目录里的
E = json.load(open(sys.argv[3], encoding='utf-8'))['session_ids']
arch = {j['cliSessionId'] for j in js if j.get('isArchived')}
assert arch == {E['basic']}, arch   # 被完整包含的 basic 归档；互相包含时更晚结束的续接会话留着；old 有独有结尾，不归档
PY
expect_code 0 "再跑一次" --config "$CFG" --register-desktop --write
grep -q "还没登记 0 个" "$T/last.log" && [ "$(nreg)" = "$((N0 + N))" ] && ok "重复跑不会重复登记" || bad "重复跑又登记了"
! find "$DM" -name '*.tmp' | grep -q . && ok "没留下 .tmp 临时文件" || bad "留下了 .tmp"

echo
echo "合计：通过 $PASS，失败 $FAIL"
[ "$FAIL" = 0 ] || { printf '  - %s\n' "${FAILS[@]}"; exit 1; }
