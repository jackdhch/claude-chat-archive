#!/usr/bin/env bash
# claude-archive 一键安装（macOS / Linux / WSL）。Windows 原生请用 install.ps1。
# 做的事：检查 Python>=3.9 → 可选建 .venv 装 markdown-it-py → 生成配置（已有不覆盖）→ 体检 → 第一次导出 → 可选每日定时任务。
# 全程只在本机：不起服务、不上传；导出内容是你的原始对话，别提交、别上传。
# 用法：./install.sh [--yes] [--no-schedule] [--no-markdown] [--time HH:MM]
#   --yes          不提问，全部按默认（会联网装 markdown-it-py、会加定时任务；不想要就同时加下面两个参数）
#   --no-markdown  不装 markdown-it-py（整个安装就完全不联网）
#   --no-schedule  不碰定时任务
#   --time HH:MM   定时任务时间（本机时区，默认 19:00）
# 可重复执行：配置不覆盖；定时任务按标记 "# claude-archive" 先删旧行再写新行，别的行不动。
set -uo pipefail
umask 077
REPO=$(cd "$(dirname "$0")" && pwd -P)
MARK='# claude-archive'
YES=false; SCHED=true; MD=true; TIME=19:00
while [ $# -gt 0 ]; do
  case $1 in
    --yes|-y) YES=true ;;
    --no-schedule) SCHED=false ;;
    --time) TIME=${2:-}; shift ;;
    --time=*) TIME=${1#--time=} ;;
    --no-markdown) MD=false ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "未知参数：$1（看 --help）" >&2; exit 2 ;;
  esac
  shift
done
[[ $TIME =~ ^([01]?[0-9]|2[0-3]):([0-5][0-9])$ ]] || { echo "--time 要写成 HH:MM，例如 19:00，收到的是：$TIME" >&2; exit 2; }
HH=$((10#${BASH_REMATCH[1]})); MM=$((10#${BASH_REMATCH[2]}))

say() { printf '\n==> %s\n' "$*"; }
warn() { printf '[提醒] %s\n' "$*" >&2; }
die() { printf '[失败] %s\n' "$*" >&2; exit "${2:-1}"; }
ask() {  # ask "问题" 默认(y/n)；--yes 或没有终端时取默认
  local a
  if $YES || [ ! -t 0 ]; then a=$2; else read -r -p "$1 " a; a=${a:-$2}; fi
  [[ $a == [Yy]* ]]
}

case $(uname -s) in
  Darwin) OS=mac ;;
  Linux) grep -qi microsoft /proc/version 2>/dev/null && OS=wsl || OS=linux ;;
  MINGW*|MSYS*|CYGWIN*) die "Windows 请在 PowerShell 里运行 install.ps1" 2 ;;
  *) OS=linux ;;
esac

say "1/6 检查 Python（要求 3.9 以上）"
SYSPY=
for c in python3 python; do
  p=$(command -v "$c" 2>/dev/null) || continue
  "$p" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null && { SYSPY=$p; break; }
done
[ -n "$SYSPY" ] || die "没找到 Python 3.9+。macOS: brew install python；Debian/Ubuntu: sudo apt install python3" 2
echo "用 $SYSPY（$("$SYSPY" -V 2>&1)）"
[ -f "$REPO/claude_archive.py" ] || die "没找到 $REPO/claude_archive.py，请在仓库目录里运行本脚本" 2

say "2/6 可选：在 $REPO/.venv 装 markdown-it-py（让网页里的 Markdown 排版更好看；不装也能用）"
VPY=$REPO/.venv/bin/python
if $MD && ask "装 markdown-it-py？[Y/n]" y; then
  if [ ! -x "$VPY" ]; then
    "$SYSPY" -m venv "$REPO/.venv" || { warn "建 .venv 失败（Debian/Ubuntu 需 sudo apt install python3-venv），改用纯文本渲染"; rm -rf "$REPO/.venv"; }
  fi
  [ -x "$VPY" ] && { "$VPY" -m pip install -q --disable-pip-version-check markdown-it-py || warn "markdown-it-py 安装失败（没网？），改用纯文本渲染，不影响导出"; }
fi
PY=$SYSPY
[ -x "$VPY" ] && "$VPY" -c '' 2>/dev/null && PY=$VPY
echo "之后都用 $PY"

say "3/6 生成配置"
CFG=${XDG_CONFIG_HOME:-$HOME/.config}/claude-archive/config.json
if [ -f "$CFG" ]; then
  echo "配置已存在，不覆盖：$CFG"
else
  "$PY" "$REPO/claude_archive.py" --config "$CFG" --init-config || die "生成配置失败" 2
fi
echo "要改数据源、输出目录、脱敏开关，编辑 $CFG（说明见 docs/CONFIG.md），改完重跑本脚本即可。"

say "4/6 体检（只检查，不导出）"
"$PY" "$REPO/claude_archive.py" --config "$CFG" --doctor
rc=$?; [ $rc -eq 2 ] && die "配置有错（见上），改好 $CFG 再重跑" 2
[ $rc -ne 0 ] && warn "体检退出码 $rc，继续尝试导出"

say "5/6 第一次导出（会话多的话要几分钟）"
"$PY" "$REPO/claude_archive.py" --config "$CFG"
EXPORT_RC=$?
case $EXPORT_RC in
  0) ;;
  1) warn "导出的检查没通过，旧输出没动；原因见上面的输出" ;;
  *) warn "导出失败（退出码 $EXPORT_RC），原因见上面的输出" ;;
esac

say "6/6 每日定时任务"
if ! $SCHED; then
  echo "按 --no-schedule 跳过，定时任务没动"
elif ! command -v crontab >/dev/null 2>&1; then
  warn "没有 crontab 命令，跳过。想每天自动更新请装 cron（Debian/Ubuntu: sudo apt install cron）后重跑"
elif ask "每天本机 $(printf %02d:%02d "$HH" "$MM") 自动更新一次？[Y/n]" y; then
  LOGF=${XDG_DATA_HOME:-$HOME/.local/share}/claude-archive/cron.log
  mkdir -p "$(dirname "$LOGF")"
  q() { printf %q "$1" | sed 's/%/\\%/g'; }   # cron 里 % 是特殊字符
  LINE="$MM $HH * * * cd $(q "$REPO") && $(q "$PY") claude_archive.py --config $(q "$CFG") >> $(q "$LOGF") 2>&1 $MARK"
  { crontab -l 2>/dev/null | grep -vF -- "$MARK"; echo "$LINE"; } | crontab - || die "写 crontab 失败"
  echo "已写入 crontab（旧的 claude-archive 行已替换，其他行没动）："; echo "  $LINE"
  echo "日志：$LOGF"
  case $OS in
    mac) echo "macOS 用的是 crontab（没用 launchd）。cron 读 ~/Library、~/Downloads 需要权限：系统设置 → 隐私与安全性 → 完全磁盘访问权限，加入 /usr/sbin/cron。" ;;
    wsl) pgrep -x cron >/dev/null 2>&1 || pgrep -x crond >/dev/null 2>&1 || \
           warn "WSL 里 cron 没在运行：先 sudo service cron start；想开机自启，在 /etc/wsl.conf 写 [boot] 一节 command=\"service cron start\"。另外 WSL 没开着时定时任务不会跑。" ;;
    linux) pgrep -x cron >/dev/null 2>&1 || pgrep -x crond >/dev/null 2>&1 || warn "cron 服务好像没在运行（sudo systemctl enable --now cron 或 crond）" ;;
  esac
else
  echo "没加定时任务。以后想加：重跑 ./install.sh；想手动更新：$PY $REPO/claude_archive.py"
fi

OUT=$("$PY" -c 'import json,os,sys; print(os.path.abspath(os.path.expandvars(os.path.expanduser(json.load(open(sys.argv[1], encoding="utf-8")).get("out_dir") or "~/claude-archive-output"))))' "$CFG" 2>/dev/null) || OUT="(读不到配置里的 out_dir)"
say "完成"
echo "输出目录：$OUT"
echo "  网页：$OUT/index.html"
echo "  给 Claude 读的文档：$OUT/docs/README.md"
case $OS in
  wsl) echo "打开：explorer.exe \"\$(wslpath -w '$OUT/index.html')\"" ;;
  mac) echo "打开：open '$OUT/index.html'" ;;
  *) echo "打开：xdg-open '$OUT/index.html'" ;;
esac
echo "提醒：输出是你的原始对话，只在本机看，别提交到 git、别放同步盘、别上传。"
exit $EXPORT_RC
