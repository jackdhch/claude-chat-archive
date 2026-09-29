# claude-archive 卸载（Windows 原生 PowerShell 5.1+）。WSL / macOS / Linux 请用 uninstall.sh。
# 运行：powershell -ExecutionPolicy Bypass -File .\uninstall.ps1 [-Yes] [-PurgeConfig] [-PurgeOutput]
#   默认：删任务计划「claude-archive」，然后问要不要删配置和缓存
#   -Yes          不提问，按默认处理（保留配置和缓存）
#   -PurgeConfig  不问，直接删配置和缓存（缓存里有 AI 写的小标题和主题，删了要重新生成）
#   -PurgeOutput  连输出目录一起删；不加这个永远不删输出
# 仓库目录和 .venv 不动，不要了直接删整个仓库目录即可。可重复执行。
param([switch]$Yes, [switch]$PurgeConfig, [switch]$PurgeOutput)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$CfgDir = Join-Path $env:APPDATA 'claude-archive'
$DataDir = Join-Path $env:LOCALAPPDATA 'claude-archive'

# 先读输出目录（删配置之前）
if ($PurgeOutput) {
    $Out = $null
    $cfgFile = Join-Path $CfgDir 'config.json'
    $o = '~/claude-archive-output'
    if (Test-Path $cfgFile) { $c = Get-Content -Raw -Encoding UTF8 $cfgFile | ConvertFrom-Json; if ($c.out_dir) { $o = $c.out_dir } }
    $o = [Environment]::ExpandEnvironmentVariables($o)
    if ($o -match '^~[\\/]') { $o = Join-Path $env:USERPROFILE $o.Substring(2) }
    $Out = [IO.Path]::GetFullPath($o)
}

Write-Host '==> 定时任务'
if (Get-ScheduledTask -TaskName 'claude-archive' -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName 'claude-archive' -Confirm:$false; Write-Host '已删除任务计划「claude-archive」'
} else { Write-Host '没有 claude-archive 任务，跳过' }

Write-Host "==> 配置和缓存：$CfgDir  $DataDir"
if (-not $PurgeConfig -and -not $Yes -and -not [Console]::IsInputRedirected) {
    $a = Read-Host '删除配置和缓存？缓存里有 AI 写的小标题和主题，删了要重新生成 [y/N]'
    if ($a -match '^[Yy]') { $PurgeConfig = $true }
}
if ($PurgeConfig) { Remove-Item -Recurse -Force $CfgDir, $DataDir -ErrorAction SilentlyContinue; Write-Host '已删除' } else { Write-Host '保留' }

if ($PurgeOutput) {
    Write-Host "==> 输出目录：$Out"
    if (-not (Test-Path $Out)) { Write-Host '不存在，跳过' }
    elseif ($Out.TrimEnd('\') -eq $env:USERPROFILE.TrimEnd('\') -or $Out -eq [IO.Path]::GetPathRoot($Out) -or -not ((Test-Path (Join-Path $Out '.claude-archive')) -or (Test-Path (Join-Path $Out 'stats.json')))) {
        Write-Host "不像是本工具的输出目录（是盘符根/用户目录，或里面没有 .claude-archive 标记），为安全没删：$Out" -ForegroundColor Red; exit 1
    } else {
        Remove-Item -Recurse -Force $Out, "$Out.new", "$Out.prev" -ErrorAction SilentlyContinue; Write-Host '已删除（含 .new / .prev 临时目录）'
    }
}
Write-Host '完成。仓库目录没动，不要了可以整个删掉。'
