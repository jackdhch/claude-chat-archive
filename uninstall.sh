#!/usr/bin/env bash
# claude-archive 卸载（macOS / Linux / WSL）。Windows 原生请用 uninstall.ps1。
# 用法：./uninstall.sh [--yes] [--purge-config] [--purge-output]
#   默认：只删 crontab 里带 "# claude-archive" 标记的那一行，别的行不动；然后问要不要删配置和缓存
#   --yes           不提问，按默认处理（保留配置和缓存）
#   --purge-config  不问，直接删配置和缓存（缓存里有 AI 写的小标题和主题，删了要重新生成）
#   --purge-output  连输出目录（导出的网页和文档）一起删；不加这个永远不删输出
# 仓库目录和 .venv 不动，不要了直接删整个仓库目录即可。可重复执行。
set -uo pipefail
MARK='# claude-archive'
YES=false; PCFG=false; POUT=false
for a in "$@"; do
  case $a in
    --yes|-y) YES=true ;;
    --purge-config) PCFG=true ;;
    --purge-output) POUT=true ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "未知参数：$a（看 --help）" >&2; exit 2 ;;
  esac
done
CFGDIR=${XDG_CONFIG_HOME:-$HOME/.config}/claude-archive
DATADIR=${XDG_DATA_HOME:-$HOME/.local/share}/claude-archive

# 先读输出目录（删配置之前）
OUT=
if $POUT; then
  for c in "$(dirname "$0")/.venv/bin/python" python3 python; do
    OUT=$("$c" -c 'import json,os,sys
try: c = json.load(open(sys.argv[1], encoding="utf-8"))
except OSError: c = {}
print(os.path.abspath(os.path.expandvars(os.path.expanduser(c.get("out_dir") or "~/claude-archive-output"))))' "$CFGDIR/config.json" 2>/dev/null) && break
  done
  [ -n "$OUT" ] || { echo "读不到输出目录（没有 Python？），没删任何东西" >&2; exit 1; }
fi

echo "==> 定时任务"
if command -v crontab >/dev/null 2>&1 && crontab -l 2>/dev/null | grep -qF -- "$MARK"; then
  crontab -l 2>/dev/null | grep -vF -- "$MARK" | crontab - && echo "已从 crontab 删掉 claude-archive 那一行，其他行没动"
else
  echo "crontab 里没有 claude-archive 的行，跳过"
fi

echo "==> 配置和缓存：$CFGDIR  $DATADIR"
if ! $PCFG && ! $YES && [ -t 0 ]; then
  read -r -p "删除配置和缓存？缓存里有 AI 写的小标题和主题，删了要重新生成 [y/N] " a
  [[ ${a:-n} == [Yy]* ]] && PCFG=true
fi
if $PCFG; then rm -rf -- "$CFGDIR" "$DATADIR" && echo "已删除"; else echo "保留"; fi

if $POUT; then
  echo "==> 输出目录：$OUT"
  R=$(cd "$OUT" 2>/dev/null && pwd -P) || R=
  if [ -z "$R" ]; then echo "不存在，跳过"
  elif [ "$R" = / ] || [ "$R" = "$(cd "$HOME" && pwd -P)" ] || { [ ! -e "$R/.claude-archive" ] && [ ! -f "$R/stats.json" ]; }; then
    echo "不像是本工具的输出目录（是根目录/家目录，或里面没有 .claude-archive 标记），为安全没删：$R" >&2; exit 1
  else
    rm -rf -- "$R" "$R.new" "$R.prev" && echo "已删除（含 .new / .prev 临时目录）"
  fi
fi
echo "完成。仓库目录没动，不要了可以整个删掉。"
