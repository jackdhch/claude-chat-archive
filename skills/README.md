# 用 Claude 补导航小标题和主题（可选）

导出工具 `claude_archive.py` 不需要 AI 也能用：没有小标题的提问会用首句截短，没有主题的会话就不显示主题标签。
想让右侧提问导航和首页分类更好用，可以让 Claude 帮你写小标题、打主题。有两条路线，产出完全一样，都通过
`claude_archive.py --merge-titles / --merge-topics` 写进本机缓存（`~/.local/share/claude-archive/`，Windows 是 `%LOCALAPPDATA%\claude-archive\`）。

> 隐私提示：两条路线都会把**提问原文前 400 字、会话标题、前几条提问的小标题**发给 Anthropic 处理（用的是你自己的 Claude 账号）。
> 导出本身始终只在本机、不联网。不想让这些内容再过一次模型，就别用这一步。

## 路线一：Claude Code 技能（推荐）

安装（把技能目录复制到 Claude Code 的个人技能目录）：

```bash
# macOS / Linux / WSL，在仓库根目录执行
mkdir -p ~/.claude/skills
cp -r skills/claude-archive ~/.claude/skills/
```

```powershell
# Windows PowerShell，在仓库根目录执行
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force skills\claude-archive "$HOME\.claude\skills\"
```

建议再设一个环境变量告诉技能仓库在哪（不设的话技能会在家目录下搜 `claude_archive.py`）：

```bash
export CLAUDE_ARCHIVE_DIR=/path/to/claude-chat-archive   # 写进 ~/.bashrc 或 ~/.zshrc
```

然后重开 Claude Code，说「更新我的对话存档」「补一下导航小标题和主题」或 “update my chat archive” 即可。
卸载：删掉 `~/.claude/skills/claude-archive`。

**额度**：用当前 Claude Code 会话的模型和额度。按中文 1 字约 1.5 token 粗算：
每 1000 条提问读入约 10–40 万 token；每 1000 个会话读入约 20–70 万 token；写出各约 4–6 万 token。
首次全量最贵，之后只处理新增的，通常很少。批次多时技能会分给 subagent 并行做。

## 路线二：命令行脚本 `scripts/enrich_with_claude.py`

需要已安装并登录 Claude Code 的 `claude` 命令（且支持 `--no-session-persistence`，否则脚本会拒绝运行，
因为每批请求会被存成新会话、下次导出又被当成提问）。没有 `claude` 命令时脚本会提示你改用路线一。

```bash
python3 scripts/enrich_with_claude.py                  # 默认 haiku；调用前会告诉你要调几次并询问
python3 scripts/enrich_with_claude.py --model sonnet   # 标题更准，额度更多
python3 scripts/enrich_with_claude.py --only titles    # 只补小标题（或 --only topics）
python3 scripts/enrich_with_claude.py --yes            # 不询问，适合放进定时任务
```

它依次做：导出 → `--dump-prompts` → 每批约 300 条调用一次 `claude -p` → 校验（缺的、超长的只重问这几条，最多 3 轮）→
`--merge-titles` → `--dump-convs` →（缓存里没有主题表就先定 8–14 个主题）→ 每批约 200 个会话调用一次 → 校验 → `--merge-topics` → 重新导出。
临时文件放在系统临时目录（权限 700），结束即删。

**额度**：token 量和路线一相当，但走的是 `claude -p` 的额度；haiku 比 sonnet 便宜得多，小标题这种短任务 haiku 够用。
调用次数 ≈ 提问批数 + 会话批数 + 1（首次定主题表）+ 少量重试。

## 两条路线共用的校验

```bash
python3 scripts/enrich_with_claude.py --check-titles prompts-00.jsonl titles-00.json
python3 scripts/enrich_with_claude.py --check-table  topics-table.json
python3 scripts/enrich_with_claude.py --check-tags   in-00.jsonl tags-00.json [topics-table.json]
```

要求：id 与输入完全一致（不漏、不多）；小标题 ≤12 字；主题表 8–14 个、名字 2–6 字、不重复、含「其他」；
每个会话 1–2 个主题且都在表内、总结 ≤30 字。退出码 0 = 通过。
