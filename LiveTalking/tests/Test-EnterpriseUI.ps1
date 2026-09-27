param(
    [string]$Url = 'http://127.0.0.1:8010/index.html'
)

$ErrorActionPreference = 'Stop'

$response = Invoke-WebRequest -UseBasicParsing -Uri $Url
if ($response.StatusCode -ne 200) {
    throw "主页无法访问，HTTP 状态：$($response.StatusCode)"
}

$html = $response.Content
$required = @(
    '<header class="topbar"',
    'AI 数字人智能交互平台',
    '实时语音识别 · 智能对话 · 语音合成 · 数字人驱动',
    '<aside class="sidebar"',
    '数字人对话',
    '会话记录',
    '知识库',
    '语音设置',
    '模型设置',
    'id="avatarStage"',
    'id="conversationPanel"',
    'id="composer"',
    'id="holdToTalk"',
    'id="txtMessage"',
    'id="sendButton"',
    'id="txtType" value="chat"',
    '已收到问题，正在生成并播报回答。',
    '/assets/doctor-li-yanyan.png',
    '李思妍医生',
    '[hidden] { display: none !important; }',
    '--app-bg: #f6f8fb',
    '--primary: #2563eb',
    '支持语音输入或文字输入，Shift + Enter 换行'
)

foreach ($fragment in $required) {
    if (-not $html.Contains($fragment)) {
        throw "企业级数字人页面缺少必需结构或文案：$fragment"
    }
}

Write-Output '企业级数字人主页结构检查通过'
