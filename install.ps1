# claude-archive 一键安装（Windows 原生 PowerShell 5.1+）。WSL / macOS / Linux 请用 install.sh。
# 运行：powershell -ExecutionPolicy Bypass -File .\install.ps1 [-Yes] [-NoSchedule] [-NoMarkdown] [-Time 19:00]
#   -Yes         不提问，全部按默认（会联网装 markdown-it-py、会加定时任务；不想要就同时加 -NoMarkdown -NoSchedule）
#   -NoMarkdown  不装 markdown-it-py（整个安装就完全不联网）
#   -NoSchedule  不碰定时任务
#   -Time HH:MM  每天几点更新（本机时区，默认 19:00）
# 做的事：检查 Python>=3.9 → 可选建 .venv 装 markdown-it-py → 生成配置（已有不覆盖）→ 体检 → 第一次导出 → 可选「任务计划程序」每日任务。
# 全程只在本机：不起服务、不上传；导出内容是你的原始对话，别提交、别上传。可重复执行。
param([switch]$Yes, [switch]$NoSchedule, [switch]$NoMarkdown, [string]$Time = '19:00')
$ErrorActionPreference = 'Continue'   # 5.1 里 Stop + 原生命令写 stderr 会误抛异常；原生命令一律看 $LASTEXITCODE
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$Repo = $PSScriptRoot
$Script = Join-Path $Repo 'claude_archive.py'
$TaskName = 'claude-archive'

function Say($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[提醒] $m" -ForegroundColor Yellow }
function Die($m, $code = 1) { Write-Host "[失败] $m" -ForegroundColor Red; exit $code }
function Ask($q, $def) {
    if ($Yes -or [Console]::IsInputRedirected) { $a = $def } else { $a = Read-Host $q; if (-not $a) { $a = $def } }
    return $a -match '^[Yy]'
}

if ($Time -notmatch '^([01]?\d|2[0-3]):([0-5]\d)$') { Die "-Time 要写成 HH:MM，例如 19:00，收到的是：$Time" 2 }
$At = [datetime]::ParseExact(('{0:D2}:{1}' -f [int]$Matches[1], $Matches[2]), 'HH:mm', $null)

Say '1/6 检查 Python（要求 3.9 以上）'
$SysPy = $null
# 注意：5.1 传参给原生程序会吞掉双引号，所以下面 -c 里的 Python 代码只用单引号
foreach ($c in 'py -3', 'python', 'python3') {
    $parts = $c -split ' '
    if (-not (Get-Command $parts[0] -ErrorAction SilentlyContinue)) { continue }
    $pre = @($parts | Select-Object -Skip 1)
    # 返回解释器真实路径；Windows 自带的 python.exe 商店占位程序会失败，自然跳过
    $p = & $parts[0] @pre -c 'import sys; print(sys.executable if sys.version_info >= (3, 9) else '''')' 2>$null
    if ($LASTEXITCODE -eq 0 -and $p) { $SysPy = "$p".Trim(); break }
}
if (-not $SysPy) { Die '没找到 Python 3.9+。请从 https://www.python.org/downloads/ 安装（勾选 Add to PATH），或 winget install Python.Python.3.12' 2 }
Write-Host "用 $SysPy（$(& $SysPy -V 2>&1)）"
if (-not (Test-Path $Script)) { Die "没找到 $Script，请在仓库目录里运行本脚本" 2 }

Say "2/6 可选：在 $Repo\.venv 装 markdown-it-py（让网页里的 Markdown 排版更好看；不装也能用）"
$VPy = Join-Path $Repo '.venv\Scripts\python.exe'
if (-not $NoMarkdown -and (Ask '装 markdown-it-py？[Y/n]' 'y')) {
    if (-not (Test-Path $VPy)) {
        & $SysPy -m venv (Join-Path $Repo '.venv')
        if ($LASTEXITCODE -ne 0) { Warn '建 .venv 失败，改用纯文本渲染'; Remove-Item -Recurse -Force (Join-Path $Repo '.venv') -ErrorAction SilentlyContinue }
    }
    if (Test-Path $VPy) {
        & $VPy -m pip install -q --disable-pip-version-check markdown-it-py
        if ($LASTEXITCODE -ne 0) { Warn 'markdown-it-py 安装失败（没网？），改用纯文本渲染，不影响导出' }
    }
}
$Py = $SysPy
if (Test-Path $VPy) { & $VPy -c 'pass' 2>$null; if ($LASTEXITCODE -eq 0) { $Py = $VPy } }
Write-Host "之后都用 $Py"

Say '3/6 生成配置'
$Cfg = Join-Path $env:APPDATA 'claude-archive\config.json'
if (Test-Path $Cfg) { Write-Host "配置已存在，不覆盖：$Cfg" }
else { & $Py $Script --config $Cfg --init-config; if ($LASTEXITCODE -ne 0) { Die '生成配置失败' 2 } }
Write-Host "要改数据源、输出目录、脱敏开关，编辑 $Cfg（说明见 docs\CONFIG.md），改完重跑本脚本即可。"

Say '4/6 体检（只检查，不导出）'
& $Py $Script --config $Cfg --doctor
if ($LASTEXITCODE -eq 2) { Die "配置有错（见上），改好 $Cfg 再重跑" 2 }
if ($LASTEXITCODE -ne 0) { Warn "体检退出码 $LASTEXITCODE，继续尝试导出" }

Say '5/6 第一次导出（会话多的话要几分钟）'
& $Py $Script --config $Cfg
$ExportRc = $LASTEXITCODE
if ($ExportRc -eq 1) { Warn '导出的检查没通过，旧输出没动；原因见上面的输出' }
elseif ($ExportRc -ne 0) { Warn "导出失败（退出码 $ExportRc），原因见上面的输出" }

Say '6/6 每日定时任务（任务计划程序）'
if ($NoSchedule) { Write-Host '按 -NoSchedule 跳过，定时任务没动' }
elseif (Ask "每天本机 $($At.ToString('HH:mm')) 自动更新一次？[Y/n]" 'y') {
    $Data = Join-Path $env:LOCALAPPDATA 'claude-archive'
    New-Item -ItemType Directory -Force $Data | Out-Null
    # 用 pythonw（不弹黑窗）跑一个小启动器，把输出写进日志
    $Runner = Join-Path $Data 'scheduled_run.py'
    $Log = Join-Path $Data 'scheduled.log'
    $j = { param($s) ConvertTo-Json $s -Compress }   # JSON 字符串字面量也是合法的 Python 字符串
    @"
import runpy, sys
sys.stdout = sys.stderr = open($(& $j $Log), 'a', encoding='utf-8')
sys.argv = [$(& $j $Script), '--config', $(& $j $Cfg)]
runpy.run_path(sys.argv[0], run_name='__main__')
"@ | Set-Content -Encoding UTF8 $Runner
    $PyW = Join-Path (Split-Path $Py) 'pythonw.exe'
    if (-not (Test-Path $PyW)) { $PyW = $Py }
    $Action = New-ScheduledTaskAction -Execute $PyW -Argument "-X utf8 `"$Runner`"" -WorkingDirectory $Repo
    $Trigger = New-ScheduledTaskTrigger -Daily -At $At
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -ErrorAction Stop -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description '每天更新 Claude 对话存档（仅本机）' -Force | Out-Null
    Write-Host "已登记任务计划「$TaskName」（重复运行会覆盖同名任务），日志：$Log"
}
else { Write-Host "没加定时任务。以后想加：重跑 install.ps1；想手动更新：& '$Py' '$Script'" }

$Out = & $Py -c 'import json,os,sys; print(os.path.abspath(os.path.expandvars(os.path.expanduser(json.load(open(sys.argv[1], encoding=''utf-8'')).get(''out_dir'') or ''~/claude-archive-output''))))' $Cfg 2>$null
if (-not $Out) { $Out = '(读不到配置里的 out_dir)' }
Say '完成'
Write-Host "输出目录：$Out"
Write-Host "  网页：$(Join-Path $Out 'index.html')"
Write-Host "  给 Claude 读的文档：$(Join-Path $Out 'docs\README.md')"
Write-Host "打开：start `"$(Join-Path $Out 'index.html')`""
Write-Host '提醒：输出是你的原始对话，只在本机看，别提交到 git、别放同步盘、别上传。'
exit $ExportRc
