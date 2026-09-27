$ErrorActionPreference = 'Stop'

$project = Split-Path -Parent $PSScriptRoot
$startScript = Get-Content -LiteralPath (Join-Path $project 'start.sh') -Raw
$webPage = Get-Content -LiteralPath (Join-Path $project 'web\index.html') -Raw
$rtcManager = Get-Content -LiteralPath (Join-Path $project 'server\rtc_manager.py') -Raw
$launcher = Get-Content -LiteralPath (Join-Path $project '启动数字人.bat') -Raw

$checks = @(
    @{ Name = '云端启动 TURN 服务'; Text = $startScript; Fragment = 'turnserver' },
    @{ Name = 'TURN 使用长期凭据认证'; Text = $startScript; Fragment = '--lt-cred-mech' },
    @{ Name = 'TURN 配置独立 realm'; Text = $startScript; Fragment = '--realm livetalking.local' },
    @{ Name = 'TURN 创建本地用户'; Text = $startScript; Fragment = '--user livetalking:livetalking-demo-only' },
    @{ Name = '云端 WebRTC 使用 TURN/TCP'; Text = $startScript; Fragment = 'turn:127.0.0.1:3478?transport=tcp' },
    @{ Name = '浏览器使用 TURN/TCP'; Text = $webPage; Fragment = 'turn:127.0.0.1:3478?transport=tcp' },
    @{ Name = '浏览器提供 TURN 用户名'; Text = $webPage; Fragment = "username: 'livetalking'" },
    @{ Name = '浏览器提供 TURN 凭据'; Text = $webPage; Fragment = "credential: 'livetalking-demo-only'" },
    @{ Name = '浏览器强制中继'; Text = $webPage; Fragment = "iceTransportPolicy: 'relay'" },
    @{ Name = '云端 aiortc 提供 TURN 用户名'; Text = $rtcManager; Fragment = 'username="livetalking"' },
    @{ Name = '云端 aiortc 提供 TURN 凭据'; Text = $rtcManager; Fragment = 'credential="livetalking-demo-only"' },
    @{ Name = '桌面脚本转发 TURN 端口'; Text = $launcher; Fragment = '-L 3478:127.0.0.1:3478' }
)

foreach ($check in $checks) {
    if (-not $check.Text.Contains($check.Fragment)) {
        throw "失败：$($check.Name)，缺少：$($check.Fragment)"
    }
}

if ($startScript.Contains('--no-auth')) {
    throw '失败：TURN 不应以 --no-auth 运行，否则与浏览器的用户名/密码配置不一致'
}

Write-Output 'TURN/TCP 一键启动配置检查通过'
