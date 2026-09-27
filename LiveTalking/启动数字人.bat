@echo off
chcp 65001 >nul
title LiveTalking 一键启动

echo [1/3] 正在启动算力云上的 LiveTalking...
ssh autodl-livetalking "cd /root/autodl-tmp/LiveTalking && ./start.sh"
if errorlevel 1 (
    echo.
    echo 启动失败，请检查算力云实例是否开机以及 SSH 是否可连接。
    pause
    exit /b 1
)

echo [2/3] 正在打开 SSH 隧道窗口...
start "LiveTalking SSH 隧道（请勿关闭）" powershell.exe -NoExit -Command "ssh -N -L 8010:127.0.0.1:8010 -L 3478:127.0.0.1:3478 autodl-livetalking"

echo [3/3] 正在打开 Demo 网页...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8010/index.html"

echo 完成。使用期间请保持 SSH 隧道窗口开启。
timeout /t 2 /nobreak >nul
