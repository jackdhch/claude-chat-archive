#!/usr/bin/env python3
"""生成一套全假的测试数据到 tests/fixtures/（结果也提交进仓库）。
用法：python3 tests/make_fixtures.py        重新生成（确定性：同样代码同样输出）
所有人名、路径、邮箱、手机号、身份证号、Bark key 都是编的；身份证号只是校验位算对了。
预期值（会话数、消息数……）按下面每一行的设计标注算出来，写进 fixtures/expected.json。"""
import base64, io, json, os, shutil, struct, uuid, zipfile, zlib
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, 'fixtures')
PROJ = '-home-alice-demo-proj'
CWD = '/home/alice/demo-proj'
NS = uuid.UUID('12345678-1234-5678-1234-567812345678')
def U(name): return str(uuid.uuid5(NS, name))

# ───────────── 假敏感值（run_tests.sh 用它们检查脱敏）─────────────
def id_check(s17):
    w = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    return '10X98765432'[sum(int(c) * k for c, k in zip(s17, w)) % 11]
ID17 = '11010519900101123'   # 用 3 结尾凑出数字校验位，避免 X 大小写问题
ID = ID17 + id_check(ID17)
assert ID[-1].isdigit(), ID
SECRETS = {
    'email': 'alice.fake@example.com',
    'user_email': 'demo.owner@example.org',       # 同时出现在 users.json（进精确脱敏表）和正文里
    'phone': '13912345678',
    'user_phone': '13700001111',                  # users.json 的 verified_phone_number = +8613700001111
    'idcard': ID,
    'card': '4111111111111111',                   # 公开的测试卡号，Luhn 校验通过
    'bark_key': 'FakeBarkKey9x8y7z6w',            # 写成 https://api.day.app/<key>/标题
    'literal_cfg': 'ZebraLiteralCfg7777',          # 配置 redact_literals 里的值，别的规则抓不到
    'literal_file': 'OtterLiteralFile8899',        # 配置 redact_literal_files 指向的文件里的值
}
SENSITIVE_TEXT = (f"我的邮箱 {SECRETS['email']}，备用 {SECRETS['user_email']}，手机{SECRETS['phone']}，"
                  f"另一个号 +86 {SECRETS['user_phone']}，身份证{SECRETS['idcard']}，卡号 {SECRETS['card']}。"
                  f"推送用 curl https://api.day.app/{SECRETS['bark_key']}/测试 ；内部代号 {SECRETS['literal_cfg']} 和 {SECRETS['literal_file']}。")

def png_1x1():
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\xff\x80\x00')) + chunk(b'IEND', b''))
PNG_B64 = base64.b64encode(png_1x1()).decode()

# ───────────── Claude Code 行构造 ─────────────
T0 = datetime(2026, 1, 5, 2, 0, tzinfo=timezone.utc)
CLK = [0]
def ts(step=37):
    CLK[0] += step; return (T0 + timedelta(seconds=CLK[0])).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

REG = {}   # uuid → 设计标注 {'k': u/a/res/x/drop, 'main': 是否在主会话文件, 'sid': 属于哪个文件}
class Sess:
    def __init__(s, sid, side=False, agent=None):
        s.sid, s.side, s.agent, s.rows, s.last = sid, side, agent, [], None
    def base(s, t, u, kind, stamp=None):
        r = {'parentUuid': s.last, 'isSidechain': s.side, 'userType': 'external', 'cwd': CWD, 'sessionId': s.sid,
             'version': '2.1.0', 'gitBranch': 'main', 'entrypoint': 'cli', 'type': t, 'uuid': u, 'timestamp': stamp or ts()}
        if s.agent: r['agentId'] = s.agent
        s.last = u; s.rows.append(r)
        REG.setdefault(u, {'k': kind, 'main': s.agent is None, 'sid': s.sid})
        return r
    def user(s, text, name, img=False, origin='human'):
        c = text if not img else [{'type': 'text', 'text': text}, {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': PNG_B64}}]
        r = s.base('user', U(name), 'u' if origin == 'human' else 'x')
        r['message'] = {'role': 'user', 'content': c}
        if origin: r['origin'] = {'kind': origin}
        r['promptId'] = U(name + '-p'); return r
    def task(s, text, name):   # 子 agent 第一行：没有 origin 的 user → 任务提示
        r = s.base('user', U(name), 'x'); r['message'] = {'role': 'user', 'content': text}; return r
    def asst(s, name, mid, blocks, model='claude-sonnet-4-5', kind='a'):
        r = s.base('assistant', U(name), kind)
        r['message'] = {'id': mid, 'type': 'message', 'role': 'assistant', 'model': model, 'content': blocks,
                        'stop_reason': None, 'usage': {'input_tokens': 10, 'output_tokens': 20}}
        r['requestId'] = 'req_' + mid[4:]; return r
    def result(s, name, tool_id, text, tur=None, err=False):
        r = s.base('user', U(name), 'res')
        r['message'] = {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool_id, 'content': text, 'is_error': err}]}
        r['toolUseResult'] = tur if tur is not None else {'stdout': text, 'stderr': '', 'interrupted': False}
        r['sourceToolAssistantUUID'] = s.rows[-2]['uuid'] if len(s.rows) > 1 else None
        return r
    def meta(s, text, name):
        r = s.base('user', U(name), 'drop'); r['message'] = {'role': 'user', 'content': text}; r['isMeta'] = True; return r
    def raw(s, extra): s.rows.append(extra)
    def dump(s, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            for r in s.rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')

def txt(t): return {'type': 'text', 'text': t}
def think(t): return {'type': 'thinking', 'thinking': t, 'signature': 'sig-fake'}
def tool(i, n, inp): return {'type': 'tool_use', 'id': i, 'name': n, 'input': inp}

PD = os.path.join(FX, 'home', '.claude', 'projects', PROJ)
SID = {k: U('session-' + k) for k in ('basic', 'compact', 'old', 'new', 'agents', 'long', 'backup_only')}

def build_cc():
    files = {}
    # S1 普通问答 + 工具 + thinking + 同一 message.id 拆多行 + 重复行 + 图片 + 敏感值 + 排队输入 + 标题行
    s = Sess(SID['basic'])
    s.raw({'type': 'file-history-snapshot', 'messageId': U('fh1'), 'snapshot': {}, 'isSnapshotUpdate': False})
    s.user('帮我看看 demo-proj 的 README 有没有写错字，顺便列一下目录结构', 'b-u1')
    s.asst('b-a1', 'msg_basic_A', [think('用户想检查 README，先列目录再读文件。')])
    s.asst('b-a2', 'msg_basic_A', [txt('好的，我先列一下目录。')])
    a3 = s.asst('b-a3', 'msg_basic_A', [tool('toolu_b1', 'Bash', {'command': 'ls -la', 'description': '列出目录'})])
    s.result('b-r1', 'toolu_b1', 'README.md\nsrc\ntests')
    s.raw(dict(a3))   # 文件内重复行（同一 uuid 又写了一遍）
    s.asst('b-a4', 'msg_basic_B', [txt('目录里有 README.md、src 和 tests。README 第 3 行 “recieve” 应为 “receive”。')])
    s.meta('<system-reminder>这是 isMeta 行，应被丢弃</system-reminder>', 'b-meta')
    s.asst('b-a5', 'msg_basic_C', [think('   ')], kind='drop')    # 只有空 thinking 的 assistant 行 → 丢弃
    s.user('截图在这里，另外这是我的联系方式：' + SENSITIVE_TEXT, 'b-u2', img=True)
    s.asst('b-a6', 'msg_basic_D', [txt('收到截图。联系方式我不会记录。')])
    q = s.base('attachment', U('b-q1'), 'u')
    q['attachment'] = {'type': 'queued_command', 'commandMode': 'prompt', 'prompt': '再顺手把 CHANGELOG 也检查一下（排队输入）'}
    s.asst('b-a7', 'msg_basic_E', [txt('CHANGELOG 没问题。')])
    s.raw({'type': 'custom-title', 'customTitle': '检查 README 错字', 'sessionId': s.sid})
    s.raw({'type': 'ai-title', 'aiTitle': 'README typo check', 'sessionId': s.sid})
    files[SID['basic']] = s
    s.dump(os.path.join(PD, SID['basic'] + '.jsonl'))

    # S2 压缩边界 + 压缩摘要 + 斜杠命令 + 本地命令输出
    s = Sess(SID['compact'])
    s.user('把 src/app.py 里的日志改成 logging 模块', 'c-u1')
    s.asst('c-a1', 'msg_c_A', [txt('已改好，用 logging.getLogger(__name__)。')])
    b = s.base('system', U('c-bound'), 'x'); b.update(subtype='compact_boundary', content='Conversation compacted', level='info', isMeta=False,
                                                  compactMetadata={'trigger': 'auto', 'preTokens': 150000}, logicalParentUuid=U('c-a1'))
    cs = s.base('user', U('c-sum'), 'x'); cs.update(isCompactSummary=True, isVisibleInTranscriptOnly=True,
                                                   message={'role': 'user', 'content': 'This session is being continued from a previous conversation. Summary: 改了日志。'})
    cm = s.base('user', U('c-cmd'), 'x'); cm['message'] = {'role': 'user', 'content': '<command-name>/model</command-name>\n<command-message>model</command-message>\n<command-args>opus</command-args>'}
    lo = s.base('user', U('c-stdout'), 'drop'); lo['message'] = {'role': 'user', 'content': '<local-command-stdout>Set model to opus</local-command-stdout>'}
    s.user('压缩之后继续：再加一个单元测试', 'c-u2')
    s.asst('c-a2', 'msg_c_B', [txt('加了 tests/test_app.py。')], model='claude-opus-4-1')
    files[SID['compact']] = s
    s.dump(os.path.join(PD, SID['compact'] + '.jsonl'))

    # S3 旧会话 + S4 续接：S4 开头复制了 S3 的前 4 行；S3 自己还有独有尾巴（时间早于 S4 新内容）
    s3 = Sess(SID['old'])
    s3.user('PREFIX-MARK-1 设计一个缓存层', 'o-u1')
    s3.asst('o-a1', 'msg_o_A', [txt('PREFIX-MARK-2 建议用 LRU。')])
    s3.user('PREFIX-MARK-3 容量设多少', 'o-u2')
    s3.asst('o-a2', 'msg_o_B', [txt('PREFIX-MARK-4 先设 1000。')])
    s3.raw({'type': 'custom-title', 'customTitle': '缓存层设计（旧）', 'sessionId': s3.sid})   # 标题不含标记，方便数标记出现次数
    prefix = [dict(r) for r in s3.rows if r.get('uuid')]
    s3.user('OLD-TAIL-MARK-1 旧会话里后来又问了一句', 'o-u3')
    s3.asst('o-a3', 'msg_o_C', [txt('OLD-TAIL-MARK-2 旧会话的回答')])
    s3.dump(os.path.join(PD, SID['old'] + '.jsonl'))
    s4 = Sess(SID['new'])
    for r in prefix: s4.raw(r)
    s4.last = prefix[-1]['uuid']
    CLK[0] += 3600
    s4.user('NEW-MARK-1 续接后：缓存要不要加过期时间', 'n-u1')
    s4.asst('n-a1', 'msg_n_A', [txt('NEW-MARK-2 加 TTL，默认 300 秒。')])
    s4.raw({'type': 'custom-title', 'customTitle': '缓存层设计（续接）', 'sessionId': s4.sid})
    s4.dump(os.path.join(PD, SID['new'] + '.jsonl'))

    # S5 子 agent + workflow
    s = Sess(SID['agents'])
    s.user('派个子 agent 查一下依赖，再跑个 workflow 审代码', 'g-u1')
    s.asst('g-a1', 'msg_g_A', [tool('toolu_ag1', 'Agent', {'description': '查依赖', 'prompt': '列出 requirements.txt 的依赖', 'subagent_type': 'Explore'})])
    AG, WA = 'a1b2c3d4e5f60718', 'b9c8d7e6f5a40312'
    RUN = 'wf_0a1b2c3d-4e5'
    s.result('g-r1', 'toolu_ag1', '依赖有 requests 和 click。', tur={'status': 'completed', 'agentId': AG, 'content': [txt('依赖有 requests 和 click。')]})
    s.asst('g-a2', 'msg_g_B', [tool('toolu_wf1', 'Workflow', {'name': 'code-review', 'description': '审代码'})])
    s.result('g-r2', 'toolu_wf1', 'workflow 完成：没有发现问题。', tur={'status': 'completed', 'runId': RUN})
    s.asst('g-a3', 'msg_g_C', [txt('子 agent 和 workflow 都跑完了。')])
    s.dump(os.path.join(PD, SID['agents'] + '.jsonl'))
    sd = os.path.join(PD, SID['agents'])
    a = Sess(SID['agents'], side=True, agent=AG)
    a.task('列出 requirements.txt 的依赖', 'ag-t1')
    a.asst('ag-a1', 'msg_ag_A', [tool('toolu_ag_r', 'Read', {'file_path': CWD + '/requirements.txt'})])
    a.result('ag-r1', 'toolu_ag_r', 'requests\nclick')
    a.asst('ag-a2', 'msg_ag_B', [txt('依赖有 requests 和 click。')])
    a.dump(os.path.join(sd, 'subagents', f'agent-{AG}.jsonl'))
    json.dump({'agentType': 'Explore', 'description': '查依赖', 'toolUseId': 'toolu_ag1', 'spawnDepth': 1}, open(os.path.join(sd, 'subagents', f'agent-{AG}.meta.json'), 'w'))
    w = Sess(SID['agents'], side=True, agent=WA)
    w.task('审查 src/ 下的代码', 'wa-t1')
    w.asst('wa-a1', 'msg_wa_A', [txt('src/ 没有发现问题。')])
    w.dump(os.path.join(sd, 'subagents', 'workflows', RUN, f'agent-{WA}.jsonl'))
    json.dump({'agentType': 'workflow-agent', 'description': '审代码', 'workflowPhase': 'review', 'toolUseId': 'toolu_wf1'},
              open(os.path.join(sd, 'subagents', 'workflows', RUN, f'agent-{WA}.meta.json'), 'w'))
    os.makedirs(os.path.join(sd, 'workflows'), exist_ok=True)
    json.dump({'runId': RUN, 'workflowName': 'code-review', 'status': 'completed', 'agentCount': 1, 'summary': '审代码，没有问题',
               'result': {'ok': True}, 'phases': ['review'], 'startTime': '2026-01-05T03:00:00Z'},
              open(os.path.join(sd, 'workflows', RUN + '.json'), 'w'), ensure_ascii=False)

    # S6 长会话：让文档切块（run_tests.sh 用较小 doc_token_limit）
    s = Sess(SID['long'])
    para = '这是一段用来撑长度的说明文字，讨论缓存、日志、测试和部署的各种细节。' * 18
    for i in range(12):
        s.user(f'LONG-Q{i:02d} 第 {i} 个问题：{para[:120]}', f'l-u{i}')
        s.asst(f'l-a{i}', f'msg_l_{i}', [txt(f'LONG-A{i:02d} ' + para)])
    s.dump(os.path.join(PD, SID['long'] + '.jsonl'))

    # 备份目录：S1 的同名副本（应被跳过）+ 只在备份里的会话（源目录已删）
    bd = os.path.join(FX, 'home', 'session-backup', PROJ)
    os.makedirs(bd, exist_ok=True)
    shutil.copy(os.path.join(PD, SID['basic'] + '.jsonl'), bd)
    s = Sess(SID['backup_only'])
    s.user('BACKUP-MARK 这个会话只在备份里', 'k-u1')
    s.asst('k-a1', 'msg_k_A', [txt('好的。')])
    s.raw({'type': 'custom-title', 'customTitle': '只在备份里的会话', 'sessionId': s.sid})
    s.dump(os.path.join(bd, SID['backup_only'] + '.jsonl'))

    # Claude Code 记忆文件 + 桌面应用元数据（给 S2 一个手动标题、加星标）
    md = os.path.join(FX, 'home', '.claude', 'projects', PROJ, 'memory')
    os.makedirs(md, exist_ok=True)
    open(os.path.join(md, 'MEMORY.md'), 'w', encoding='utf-8').write('# Memory Index\n\n- 这是假的记忆文件，演示用。\n')
    dd = os.path.join(FX, 'home', 'desktop-meta', 'claude-code-sessions', 'acct', 'org')
    os.makedirs(dd, exist_ok=True)
    json.dump({'cliSessionId': SID['compact'], 'title': '日志改 logging（桌面手动标题）', 'titleSource': 'user', 'isStarred': True, 'isArchived': False},
              open(os.path.join(dd, 'local_0001.json'), 'w'), ensure_ascii=False)

# ───────────── claude.ai 导出包 ─────────────
PH = 'This block is not supported on your current device yet.'
AI = {k: U('conv-' + k) for k in ('branch', 'tools', 'legacy')}
PROJ_ID = U('ai-project')
AIREG = {}
def am(conv, name, parent, sender, t, content, text=None, att=None, files=None):
    u = U(conv + name); AIREG[u] = {'conv': conv, 'who': sender}
    return {'uuid': u, 'text': text if text is not None else ''.join(b.get('text', '') for b in content if b['type'] == 'text'),
            'content': content, 'sender': sender, 'created_at': t, 'updated_at': t, 'attachments': att or [], 'files': files or [],
            'parent_message_uuid': parent}
ROOT = '00000000-0000-4000-8000-000000000000'
def at(h, m): return f'2026-02-10T{h:02d}:{m:02d}:00.000000Z'

def build_ai():
    # C1 分支树：m3 被改写成 m3b，m4b 又被重新生成成 m4c
    c = 'branch'
    m1 = am(c, 'm1', ROOT, 'human', at(1, 0), [txt('BRANCH-Q1 解释一下 Python 的 GIL')])
    m2 = am(c, 'm2', m1['uuid'], 'assistant', at(1, 1), [txt('GIL 是全局解释器锁。![示意图](https://example.com/gil.png)')])
    m3 = am(c, 'm3', m2['uuid'], 'human', at(1, 2), [txt('BRANCH-OLD-Q 那多进程呢')])
    m4 = am(c, 'm4', m3['uuid'], 'assistant', at(1, 3), [txt('多进程绕开 GIL。')])
    m3b = am(c, 'm3b', m2['uuid'], 'human', at(1, 4), [txt('BRANCH-EDIT-Q 那 asyncio 呢（改写后）')])
    m4b = am(c, 'm4b', m3b['uuid'], 'assistant', at(1, 5), [txt('asyncio 是单线程并发（第一版）。')])
    m4c = am(c, 'm4c', m3b['uuid'], 'assistant', at(1, 6), [think('重新组织一下回答。'), txt('asyncio 是单线程事件循环（重新生成）。')])
    conv1 = {'uuid': AI['branch'], 'name': 'GIL 与并发', 'summary': '讨论 GIL、多进程和 asyncio。', 'created_at': at(1, 0), 'updated_at': at(1, 6),
             'account': {'uuid': U('acct')}, 'chat_messages': [m1, m2, m3, m4, m3b, m4b, m4c]}
    # C2 工具：create_file + str_replace、artifacts、show_widget、knowledge 搜索、附件、敏感值
    c = 'tools'
    html0 = '<!doctype html><html><body><h1>Hello v1</h1></body></html>'
    t1 = am(c, 't1', ROOT, 'human', at(2, 0), [txt('做一个网页，再画个图。' + SENSITIVE_TEXT)],
            att=[{'file_name': 'notes.txt', 'file_size': 20, 'file_type': 'text/plain', 'extracted_content': 'ATTACH-MARK 附件里的文字'}],
            files=[{'file_name': 'photo.png', 'file_uuid': U('f1')}])
    t2 = am(c, 't2', t1['uuid'], 'assistant', at(2, 1), [
        tool('tu1', 'project_knowledge_search', {'query': '网页模板'}),
        {'type': 'tool_result', 'tool_use_id': 'tu1', 'name': 'project_knowledge_search', 'is_error': False,
         'content': [{'type': 'knowledge', 'title': '模板说明.md', 'url': 'https://example.com/kb/1', 'text': '模板正文'}]},
        tool('tu2', 'create_file', {'path': '/mnt/user-data/outputs/page.html', 'file_text': html0, 'description': '建网页'}),
        {'type': 'tool_result', 'tool_use_id': 'tu2', 'name': 'create_file', 'is_error': False, 'content': [txt('File created')]},
        tool('tu3', 'str_replace', {'path': '/mnt/user-data/outputs/page.html', 'old_str': 'Hello v1', 'new_str': 'REPLAYED-V2', 'description': '改标题'}),
        {'type': 'tool_result', 'tool_use_id': 'tu3', 'name': 'str_replace', 'is_error': False, 'content': [txt('ok')]},
        txt('网页做好了。'),
    ], text='网页做好了。' + PH)
    t3 = am(c, 't3', t2['uuid'], 'human', at(2, 2), [txt('再给一个 artifact 和一张图')])
    t4 = am(c, 't4', t3['uuid'], 'assistant', at(2, 3), [
        tool('tu4', 'artifacts', {'id': 'demo-md', 'type': 'text/markdown', 'title': '说明文档', 'command': 'create', 'content': '# 说明\n初版 ART-V1'}),
        tool('tu5', 'artifacts', {'id': 'demo-md', 'command': 'update', 'old_str': 'ART-V1', 'new_str': 'ART-V2'}),
        tool('tu6', 'visualize:show_widget', {'title': '柱状图', 'widget_code': '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>', 'i_have_seen_read_me': True}),
        txt('都放好了。'),
    ])
    conv2 = {'uuid': AI['tools'], 'name': '网页和图表', 'summary': '', 'created_at': at(2, 0), 'updated_at': at(2, 3),
             'account': {'uuid': U('acct')}, 'chat_messages': [t1, t2, t3, t4]}
    # C3 老格式：content 为空，只有 text（含占位符）
    c = 'legacy'
    l1 = am(c, 'l1', ROOT, 'human', at(3, 0), [], text='LEGACY-Q 老格式的问题')
    l2 = am(c, 'l2', l1['uuid'], 'assistant', at(3, 1), [], text='LEGACY-A 先调工具 ' + PH + ' 然后回答。')
    conv3 = {'uuid': AI['legacy'], 'name': '', 'summary': '一段老格式对话。', 'created_at': at(3, 0), 'updated_at': at(3, 1),
             'account': {'uuid': U('acct')}, 'chat_messages': [l1, l2]}
    convs = [conv1, conv2, conv3]
    zp = os.path.join(FX, 'Downloads', 'data-00000000-0000-4000-8000-000000000000-1700000000-deadbeef-batch-0000.zip')
    os.makedirs(os.path.dirname(zp), exist_ok=True)
    J = lambda o: json.dumps(o, ensure_ascii=False, indent=1)
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, o in [('users.json', [{'uuid': U('acct'), 'full_name': 'Alice Demo', 'email_address': SECRETS['user_email'], 'verified_phone_number': '+86' + SECRETS['user_phone']}]),
                     ('memories.json', [{'conversations_memory': '用户是演示账号 Alice，喜欢简洁的回答。', 'project_memories': {PROJ_ID: '演示项目的记忆。'}, 'account_uuid': U('acct')}]),
                     (f'projects/{PROJ_ID}.json', {'uuid': PROJ_ID, 'name': '演示项目', 'description': '', 'is_private': True, 'docs': [], 'created_at': at(0, 0), 'updated_at': at(0, 0)}),
                     ('conversations.json', convs)]:
            zi = zipfile.ZipInfo(n, (2026, 2, 10, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, J(o))
    return convs

def expected(convs):
    shown = {u: v for u, v in REG.items() if v['k'] != 'drop'}
    main_items = {u: v for u, v in shown.items() if v['main']}
    main_sids = sorted({v['sid'] for v in REG.values() if v['main']})
    return {
        '_说明': '由 tests/make_fixtures.py 按设计算出；run_tests.sh 用它对账。cc_* 是去重之后的数。',
        'cc_sessions': len(main_sids),
        'cc_subagents': 2, 'cc_workflows': 1,
        'cc_shown_rows': len(shown),                                              # 对应 stats.json 的 CC显示
        'cc_msgs': sum(v['k'] in ('u', 'a') for v in main_items.values()),        # data.js 里 cc 会话 nmsg 之和
        'cc_prompts': sum(v['k'] == 'u' for v in main_items.values()),            # data.js 里 cc 会话 nq 之和
        'ai_convs': len(convs),
        'ai_msgs': sum(len(c['chat_messages']) for c in convs),
        'ai_prompts': sum(v['who'] == 'human' for v in AIREG.values()),
        'ai_branches': {AI['branch']: 2},
        'ai_files': {AI['tools']: 3},
        'session_ids': SID, 'ai_ids': AI,
        'once_markers': ['PREFIX-MARK-1', 'PREFIX-MARK-2', 'PREFIX-MARK-3', 'PREFIX-MARK-4', 'OLD-TAIL-MARK-1', 'OLD-TAIL-MARK-2', 'NEW-MARK-1', 'NEW-MARK-2', 'BACKUP-MARK'],
        'prefix_uuids': [U(n) for n in ('o-u1', 'o-a1', 'o-u2', 'o-a2')],
        'must_contain': ['REPLAYED-V2', 'ART-V2', 'ATTACH-MARK', 'LEGACY-A'],
        'secrets': SECRETS,
        'placeholder': PH,
    }

if __name__ == '__main__':
    if os.path.exists(FX): shutil.rmtree(FX)
    os.makedirs(FX)
    build_cc(); convs = build_ai()
    json.dump(expected(convs), open(os.path.join(FX, 'expected.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 给 redact_literal_files 用的文件
    open(os.path.join(FX, 'literals.txt'), 'w', encoding='utf-8').write(SECRETS['literal_file'] + '\n')
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(FX) for f in fs)
    assert size < 1_000_000, size
    print(f'fixtures 已生成 → {FX}（{size} 字节）')
