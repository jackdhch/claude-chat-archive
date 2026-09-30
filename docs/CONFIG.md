# 配置说明

大多数人不需要手写配置：`bash install.sh`（Windows 上是 `install.ps1`）会调用 `python3 claude_archive.py --init-config`，自动探测本机的数据位置并写好配置文件。这份文档讲的是：配置文件在哪、每一项是什么意思、默认值是多少、各系统上的数据默认放在哪、claude.ai 的数据怎么导出。

## 配置文件和缓存放在哪

| 用途 | Linux / WSL / macOS | Windows（原生） |
|---|---|---|
| 配置文件 | `$XDG_CONFIG_HOME/claude-archive/config.json`，没设 `XDG_CONFIG_HOME` 时是 `~/.config/claude-archive/config.json` | `%APPDATA%\claude-archive\config.json` |
| 缓存（AI 写的提问小标题 `titles.json`、会话主题 `topics.json`） | `$XDG_DATA_HOME/claude-archive/`，默认 `~/.local/share/claude-archive/` | `%LOCALAPPDATA%\claude-archive\` |

- 用 `--config 路径` 可以指定别的配置文件。
- 没有配置文件时，直接运行也能用：所有配置项取下表的默认值（数据源自动探测）。
- 缓存文件里有你的提问摘要和会话摘要，属于个人数据，**不要提交到 git**，也不要放进同步盘。
- 配置文件本身只有路径和开关，但路径里通常含有你的系统用户名，同样不建议公开。

## 配置项

仓库里的 [`config.example.json`](../config.example.json) 是带默认值的完整样例。配置文件是标准 JSON；想写备注，用以 `_` 或 `//` 开头的键（例如 `"_备注": "…"`），会被忽略。拼错的配置项会直接报错（退出码 2），不会被悄悄忽略。路径里的 `~` 会展开成你的主目录，支持 `*`、`**` 通配符。

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `out_dir` | `~/claude-archive-output` | 输出目录：网页、给 Claude 读的文档、统计报告都在这里。**必须在本机硬盘上、不在 git 工作区里、不在同步盘里**，否则默认拒绝运行（见 [PRIVACY.md](PRIVACY.md)）。 |
| `claude_code_roots` | `["~/.claude/projects"]` | Claude Code 会话目录，按顺序读取，同一个会话 id 先读到的算数。WSL 下 `--init-config` 如果探测到 Windows 那边的 `/mnt/c/Users/<用户名>/.claude/projects` 也会加进来（会把 Windows 那边的全部会话一起收进来，不想要就删掉这一项）。`ssh-*` 开头的目录（远程会话的本机副本）照常读取，和别处重复的会话按“先读到的算数”去重。 |
| `extra_backup_roots` | `[]` | 你自己另外备份的会话目录（格式同上）。只用来补上源目录里已经被 Claude Code 自动清理掉的会话；源目录里还在的会话不会被备份覆盖。 |
| `claude_ai_zips` | `["~/Downloads/data-*-batch-*.zip"]` | claude.ai 官方导出包的位置（通配符）。WSL 下还会加 `/mnt/c/Users/<用户名>/Downloads/data-*-batch-*.zip`。可以同时放新旧多个导出包，会按消息合并（见下文）。 |
| `chatgpt_zips` | `["~/Downloads/*.zip"]` | 要检查是不是 ChatGPT 官方导出包的 zip（通配符）。WSL 下还会加 `/mnt/c/Users/<用户名>/Downloads/*.zip`。**不看文件名，看内容**：zip 里有 `conversations.json`（或拆分的 `conversations-000.json`……），且会话带 `mapping` 才收；claude.ai 的包（会话带 `chat_messages`）和别的 zip 自动跳过。可以同时放新旧多个包，同一个对话以 `update_time` 最新的为准（见下文）。没有 ChatGPT 包就不生成 `chatgpt/` 页面。 |
| `desktop_meta_globs` | 自动探测（见下表） | Claude 桌面应用的会话元数据，只读 5 个字段：会话 id、标题、标题来源（手动改的还是自动生成的）、是否星标、是否归档。用来让网页上的标题和星标与桌面应用一致。`--register-desktop --write` 也按这里找登记文件夹，往里新增登记文件（不改已有的）。没有桌面应用就留空列表。 |
| `redact` | `true` | 是否脱敏。开着时，读入数据的那一刻就把邮箱、手机号、密钥等换成占位符，最后还会把全部输出重扫一遍，有残留就不替换旧输出。规则和局限见 [PRIVACY.md](PRIVACY.md)。命令行 `--redact` / `--no-redact` 可以临时覆盖。 |
| `redact_literals` | `[]` | 精确脱敏值：你知道的、正则抓不到的敏感字符串（比如某个推送服务的 key、内部项目代号、家庭住址的一部分）。出现就替换成 `[已脱敏]`，也会匹配它的 URL 编码写法。少于 6 个字符的值会被忽略（太短会误伤正常文字）。 |
| `redact_literal_files` | `[]` | 从文件里读精确脱敏值：每个文件一行一个值。如果某一行是网址或路径，它的最后一段也会单独遮住（例如推送地址 `https://api.day.app/<key>` 里的 key，对话里常常单独出现）。适合“密钥本来就存在某个文件里、不想再抄一份进配置”的情况。文件只读进内存，不会被打印或输出。 |
| `doc_token_limit` | `15000` | 给 Claude 读的 Markdown 文档每一块的大小上限（估算的 token 数）。Claude Code 的 Read 工具一次最多读约 25000 token，留出余量。一般不用改。 |
| `timezone` | `"local"` | 网页和文档里显示时间用的时区。`"local"` 跟随本机；也可以写 UTC 偏移，如 `"+08:00"`、`"-05:00"`。 |
| `allow_synced_output` | `false` | 设为 `true` 等于每次都加 `--allow-synced-output`：允许输出目录位于 git 工作区或同步盘里。**不建议打开。** |
| `language` | `"zh"` | 界面语言。目前界面文字只有中文，这个字段先保留。 |

### 最小配置示例

```json
{
  "out_dir": "~/claude-archive-output",
  "claude_code_roots": ["~/.claude/projects"],
  "extra_backup_roots": [],
  "claude_ai_zips": ["~/Downloads/data-*-batch-*.zip"],
  "chatgpt_zips": ["~/Downloads/*.zip"],
  "desktop_meta_globs": [],
  "redact": true,
  "redact_literals": [],
  "redact_literal_files": [],
  "doc_token_limit": 15000,
  "timezone": "local",
  "language": "zh"
}
```

改完配置先跑 `python3 claude_archive.py --doctor`：它会列出每个数据源找到了多少文件、配置有没有问题、Markdown 渲染库能不能用，但不导出任何东西。

## 各系统上数据默认放在哪

| 数据 | Linux | macOS | Windows（原生） | WSL |
|---|---|---|---|---|
| Claude Code 会话 | `~/.claude/projects/` | `~/.claude/projects/` | `%USERPROFILE%\.claude\projects\` | WSL 里的 `~/.claude/projects/`，外加 Windows 侧的 `/mnt/c/Users/<用户名>/.claude/projects/`（如果你也在 Windows 上用 Claude Code） |
| claude.ai 导出包 | `~/Downloads/` | `~/Downloads/` | `%USERPROFILE%\Downloads\` | `/mnt/c/Users/<用户名>/Downloads/` |
| ChatGPT 导出包 | `~/Downloads/` | `~/Downloads/` | `%USERPROFILE%\Downloads\` | `/mnt/c/Users/<用户名>/Downloads/` |
| 桌面应用元数据 | 官方没有 Linux 版；如装了非官方移植版，默认找 `~/.config/Claude/claude-code-sessions/` | `~/Library/Application Support/Claude/claude-code-sessions/` | 商店版（MSIX）：`%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code-sessions\`；安装包版：`%APPDATA%\Claude\claude-code-sessions\` | 同 Windows，路径前面换成 `/mnt/c/Users/<用户名>/` |

说明：

- 商店版包名里 `Claude_` 后面那串字符每台机器可能不同，所以配置里用 `Claude_*` 通配。
- Claude Code 默认会删除 30 天前的会话记录。想长期保存，可以在 `~/.claude/settings.json` 里加 `"cleanupPeriodDays": 3650`（本工具不会替你改这个文件）。已经被删掉的会话找不回来。
- `~/.claude/sessions/` 以及文件名带 `token`、以 `.key` 结尾、`ssh-remote-server-state.json` 的文件属于凭据，工具碰到会直接中止，永远不读。

## claude.ai 的数据怎么导出

claude.ai 网页上的对话不在本机，需要先从官方导出：

1. 在网页版 claude.ai 或 Claude 桌面应用里，打开 **设置（Settings）→ 隐私（Privacy）→ 导出数据（Export data）**。手机 App 里不能导出。
2. 过一段时间你会收到一封邮件，里面有下载链接。**链接在发出后 24 小时内有效**，过期了就重新申请一次；下载时需要登录同一个账号。
3. 下载到的文件名形如 `data-<一串字符>-batch-0000.zip`。数据多时会拆成好几个 `batch-0000`、`batch-0001`……**要全部下载**：编号不连续时工具会报错退出，提示缺哪个包。
4. 放进 `claude_ai_zips` 能匹配到的位置（默认是下载文件夹），不用解压。

几点说明：

- 可以同时保留新旧多个导出包。工具按消息 id 合并，同一条消息以更新时间晚的为准；只出现在旧包里的对话（网页上可能已经删掉了）照样收录，并在页面上标注。
- 导出包里的 `users.json` 只用来读出你账号的邮箱和手机号，加进精确脱敏表，本身不输出。
- Team / Enterprise 账号只有组织的主所有者能导出，普通成员导不出来。
- 导出包本身就是你的全部原始对话，别把它提交到 git（仓库的 `.gitignore` 已经忽略了 `*.zip`）。

官方说明：[Export your Claude data](https://support.claude.com/en/articles/9450526-export-your-claude-data)

## ChatGPT 的数据怎么导出

1. 在 ChatGPT 网页里：右上角头像 → **设置（Settings）→ 数据控制（Data controls）→ 导出数据（Export data）**，确认导出。
2. 收到一封邮件，里面有下载链接（有有效期，过期就重新申请；下载需要登录同一个账号）。
3. 下载得到一个 zip（文件名没有固定格式，通常以一串哈希开头），放进 `chatgpt_zips` 能匹配到的位置（默认是下载文件夹），不用解压、不用改名。

几点说明：

- 导出包里工具会读的只有：`conversations.json`（大账号拆成 `conversations-000.json`、`conversations-001.json`……按文件名排序合并；也可能外面包了一层 `{"conversations": [...]}`）、`user.json`（只用来读出邮箱和电话，加进精确脱敏表，本身不输出）、以及图片文件（根目录的 `file-XXX-原名.png`、`dalle-generations/`、`user-*/` 子目录）。`chat.html`、`message_feedback.json`、`shared_conversations.json` 等直接忽略。
- 同一个对话出现在几个包里：按 `update_time` 取最新的那一份（整个对话替换，不按消息合并——ChatGPT 的对话是一棵树，混合两个版本可能拼出断裂的树）。包文件名以哈希开头，按名字排序不等于按时间，所以不靠顺序。
- 语音对话只收文字转写，音频文件本身不收；图片按资源 id 到包里找，找不到的在页面上标注“导出包里没有这个文件”。
- 输出在 `<out_dir>/chatgpt/`，见 [README](../README.md#chatgpt-历史)；格式细节见 [HOW-IT-WORKS.md](HOW-IT-WORKS.md#三chatgpt-导出包)。

官方说明：[How do I export my ChatGPT history and data?](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data)

## 命令行参数

```
python3 claude_archive.py [--config 路径] [--out 目录] [--redact | --no-redact] [--allow-synced-output]
python3 claude_archive.py --init-config      自动探测数据源，写默认配置，打印探测结果
python3 claude_archive.py --doctor           只检查、不导出（含：找到几个 ChatGPT 包、多少段对话）
python3 claude_archive.py --selftest         脱敏规则和分支树自检
python3 claude_archive.py --dump-prompts 目录  导出还没有小标题的提问（给 AI 写小标题用）
python3 claude_archive.py --dump-convs 目录    导出还没有主题标签的会话
python3 claude_archive.py --merge-titles 文件…  把 AI 写好的小标题合并进缓存
python3 claude_archive.py --merge-topics 文件…  把 AI 打好的主题标签合并进缓存
```

命令行参数优先于配置文件。

### AI 小标题和主题的文件格式

- `--dump-prompts 目录` 写出 `目录/prompts-00.jsonl`、`prompts-01.jsonl`……，每行 `{"id": "提问id", "t": "提问原文前 400 字"}`。终端打印的“待总结 N 条”就是还没有导航小标题的提问数。
- `--merge-titles` 读的文件是一个 JSON 对象：`{"提问id": "小标题", …}`，小标题建议不超过 12 个字。
- `--dump-prompts` 也会导出 ChatGPT 的提问（`id` 是消息 id）；`--dump-convs` 同时读 `data.js` 和 `chatgpt/data.js`，ChatGPT 会话的 key 是 `gpt-<对话id>`，`--merge-topics` 时照这个 key 写。
- `--dump-convs 目录` 读上次导出的 `data.js`，写出 `目录/in-00.jsonl`……，每行 `{"id", "src", "t", "proj", "month", "q", "as"}`，并打印当前主题表。
- `--merge-topics` 读的文件是一个 JSON 对象：`{"会话id": {"t": ["主题1", "主题2"], "s": "一句话总结"}, …}`；可以带 `"_topics": [{"name": "主题名", "desc": "说明"}, …]` 设定或替换主题表，也可以只含 `_topics`。

合并结果存在缓存目录的 `titles.json` / `topics.json`，下次导出生效。
`--allow-synced-output` 用来在你确认安全的情况下，允许输出到 git 工作区或同步盘里（不建议）。

退出码：

| 退出码 | 含义 |
|---|---|
| `0` | 成功，新输出已替换旧输出 |
| `1` | 导出做完了，但最后的检查没通过（比如脱敏残留、链接坏了、消息数对不上）。旧输出不动，新产物留在临时目录里，原因写在报告里 |
| `2` | 配置错误（配置文件不是合法 JSON、字段类型不对、输出目录不允许等） |
