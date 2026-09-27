$ErrorActionPreference = 'Stop'

$launcher = Join-Path $PSScriptRoot '..\启动数字人.bat'
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "启动脚本不存在：$launcher"
}

$content = Get-Content -LiteralPath $launcher -Raw
$bytes = [System.IO.File]::ReadAllBytes($launcher)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
if (-not $text.Contains("`r`n")) {
    throw '启动脚本必须使用 Windows CRLF 换行，否则 cmd.exe 会错误拆分命令'
}

$requiredFragments = @(
    'ssh autodl-livetalking "cd /root/autodl-tmp/LiveTalking && ./start.sh"',
    'ssh -N -L 8010:127.0.0.1:8010 -L 3478:127.0.0.1:3478 autodl-livetalking',
    'http://127.0.0.1:8010/index.html'
)

foreach ($fragment in $requiredFragments) {
    if (-not $content.Contains($fragment)) {
        throw "启动脚本缺少必要命令：$fragment"
    }
}

Write-Output 'Windows 一键启动脚本检查通过'
