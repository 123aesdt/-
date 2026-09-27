#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODEL_FILE="$PROJECT_DIR/models/wav2lip.pth"
AVATAR_ID="${AVATAR_ID:-renhe_hospital_doctor}"
AVATAR_DIR="$PROJECT_DIR/data/avatars/$AVATAR_ID"
LOG_FILE="$PROJECT_DIR/livetalking.log"
TURN_LOG_FILE="$PROJECT_DIR/turnserver.log"
TURN_PID_FILE="$PROJECT_DIR/turnserver.pid"
TURN_URL="turn:127.0.0.1:3478?transport=tcp"

cd "$PROJECT_DIR"

if [[ ! -f "$MODEL_FILE" ]]; then
  echo "缺少模型文件：$MODEL_FILE" >&2
  exit 1
fi

if [[ ! -f "$AVATAR_DIR/coords.pkl" ]]; then
  echo "缺少数字人素材：$AVATAR_DIR" >&2
  exit 1
fi

python tools/validate_avatar_asset.py "$AVATAR_DIR" --min-frames 50

if ! command -v turnserver >/dev/null 2>&1; then
  echo "缺少 coturn，请先安装：apt-get install -y coturn" >&2
  exit 1
fi

if ! pgrep -f "turnserver .*--listening-port 3478" >/dev/null; then
  CLOUD_IP="$(hostname -I | awk '{print $1}')"
  nohup turnserver \
    --listening-port 3478 \
    --listening-ip 0.0.0.0 \
    --relay-ip "$CLOUD_IP" \
    --external-ip "$CLOUD_IP" \
    --min-port 49160 \
    --max-port 49200 \
    --lt-cred-mech \
    --realm livetalking.local \
    --user livetalking:livetalking-demo-only \
    --no-tls \
    --no-dtls \
    --no-cli \
    --fingerprint \
    --pidfile "$TURN_PID_FILE" \
    --log-file "$TURN_LOG_FILE" \
    >"$TURN_LOG_FILE" 2>&1 </dev/null &
  TURN_PID=$!
  sleep 2
  if ! kill -0 "$TURN_PID" 2>/dev/null; then
    echo "TURN 服务启动失败，最近日志：" >&2
    tail -n 30 "$TURN_LOG_FILE" >&2 || true
    exit 1
  fi
  echo "TURN/TCP 中继启动成功，PID：$TURN_PID"
fi

if pgrep -f "python .*app.py.*--model wav2lip.*--avatar_id $AVATAR_ID" >/dev/null; then
  echo "LiveTalking 已经在运行。"
  pgrep -af "python .*app.py.*--model wav2lip.*--avatar_id $AVATAR_ID"
  echo "访问端口：8010"
  exit 0
fi

nohup python app.py \
  --transport webrtc \
  --model wav2lip \
  --avatar_id "$AVATAR_ID" \
  --stun "$TURN_URL" \
  --listenport 8010 \
  >"$LOG_FILE" 2>&1 </dev/null &

PID=$!
sleep 3

if kill -0 "$PID" 2>/dev/null; then
  echo "LiveTalking 启动成功，PID：$PID"
  echo "访问端口：8010"
  echo "日志文件：$LOG_FILE"
else
  echo "LiveTalking 启动失败，最近日志：" >&2
  tail -n 30 "$LOG_FILE" >&2 || true
  exit 1
fi
