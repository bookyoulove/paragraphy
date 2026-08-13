#!/usr/bin/env bash
# Paragraphy 개발 서버 제어 스크립트
#
# 사용법:
#   ./manage.sh backend   {start|stop|restart|status}
#   ./manage.sh frontend  {start|stop|restart|status}   # 기존 UI (사이드바형), port 3000
#   ./manage.sh frontend2 {start|stop|restart|status}   # 원고지 워크스페이스 UI, port 3001
#   ./manage.sh all       {start|stop|restart|status}   # backend + 두 frontend 모두
#   ./manage.sh watchdog  {start|stop|restart|status}
#
# 예시:
#   ./manage.sh backend stop      # 백엔드만 끄기
#   ./manage.sh frontend2 restart # 새 UI만 재시작
#   ./manage.sh all restart       # 백엔드+프론트 둘 다 재시작
#   ./manage.sh all status        # 전체 상태 확인
#   ./manage.sh watchdog start    # 상시 구동 워치독 시작 (죽으면 자동 재시작)

set -euo pipefail
cd "$(dirname "$0")"

PID_DIR=".run"
mkdir -p "$PID_DIR"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
BACKEND_LOG_FILE="$PID_DIR/backend.log"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
FRONTEND_LOG_FILE="$PID_DIR/frontend.log"
FRONTEND2_PID_FILE="$PID_DIR/frontend2.pid"
FRONTEND2_LOG_FILE="$PID_DIR/frontend2.log"
WATCHDOG_PID_FILE="$PID_DIR/watchdog.pid"
WATCHDOG_LOG_FILE="$PID_DIR/watchdog.log"

is_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

stop_pid_file() {
  local pid_file="$1"
  local name="$2"
  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      echo "$name 종료됨 (PID $pid)"
    else
      echo "$name 이미 꺼져 있음 (오래된 pid 파일 정리)"
    fi
    rm -f "$pid_file"
  else
    echo "$name 은(는) 실행 중이 아닙니다."
  fi
}

start_backend() {
  if is_running "$BACKEND_PID_FILE"; then
    echo "backend 이미 실행 중 (PID $(cat "$BACKEND_PID_FILE"))"
    return
  fi
  nohup python3 -m uvicorn backend.routes:app --host 127.0.0.1 --port 8000 \
    > "$BACKEND_LOG_FILE" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
  sleep 1
  if is_running "$BACKEND_PID_FILE"; then
    echo "backend 시작됨 (PID $(cat "$BACKEND_PID_FILE")) — http://127.0.0.1:8000"
    echo "로그: $BACKEND_LOG_FILE"
  else
    echo "backend 시작 실패. 로그 확인: $BACKEND_LOG_FILE" >&2
    tail -n 30 "$BACKEND_LOG_FILE" >&2 || true
    exit 1
  fi
}

start_frontend() {
  if is_running "$FRONTEND_PID_FILE"; then
    echo "frontend 이미 실행 중 (PID $(cat "$FRONTEND_PID_FILE"))"
    return
  fi
  nohup python3 serve_frontend.py 3000 frontend \
    > "$FRONTEND_LOG_FILE" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
  sleep 1
  if is_running "$FRONTEND_PID_FILE"; then
    echo "frontend 시작됨 (PID $(cat "$FRONTEND_PID_FILE")) — http://127.0.0.1:3000"
  else
    echo "frontend 시작 실패. 로그 확인: $FRONTEND_LOG_FILE" >&2
    exit 1
  fi
}

start_frontend2() {
  if is_running "$FRONTEND2_PID_FILE"; then
    echo "frontend2 이미 실행 중 (PID $(cat "$FRONTEND2_PID_FILE"))"
    return
  fi
  nohup python3 serve_frontend.py 3001 frontend-v2 \
    > "$FRONTEND2_LOG_FILE" 2>&1 &
  echo $! > "$FRONTEND2_PID_FILE"
  sleep 1
  if is_running "$FRONTEND2_PID_FILE"; then
    echo "frontend2 시작됨 (PID $(cat "$FRONTEND2_PID_FILE")) — http://127.0.0.1:3001"
  else
    echo "frontend2 시작 실패. 로그 확인: $FRONTEND2_LOG_FILE" >&2
    exit 1
  fi
}

start_watchdog() {
  if is_running "$WATCHDOG_PID_FILE"; then
    echo "watchdog 이미 실행 중 (PID $(cat "$WATCHDOG_PID_FILE"))"
    return
  fi
  nohup ./watchdog.sh \
    > /dev/null 2>&1 &
  disown
  echo $! > "$WATCHDOG_PID_FILE"
  sleep 1
  if is_running "$WATCHDOG_PID_FILE"; then
    echo "watchdog 시작됨 (PID $(cat "$WATCHDOG_PID_FILE")) — 30초마다 backend/frontend/frontend2 상태를 확인해 죽어 있으면 자동으로 재시작합니다."
    echo "로그: $WATCHDOG_LOG_FILE"
    start_backend
    start_frontend
    start_frontend2
  else
    echo "watchdog 시작 실패." >&2
    exit 1
  fi
}

status_of() {
  local pid_file="$1"
  local name="$2"
  local port="$3"
  if is_running "$pid_file"; then
    echo "$name: 실행 중 (PID $(cat "$pid_file"), port $port)"
  else
    echo "$name: 꺼져 있음"
  fi
}

usage() {
  echo "사용법: ./manage.sh {backend|frontend|frontend2|all|watchdog} {start|stop|restart|status}" >&2
  exit 1
}

TARGET="${1:-}"
ACTION="${2:-}"
[ -n "$TARGET" ] && [ -n "$ACTION" ] || usage

run_one() {
  local target="$1"
  local action="$2"
  case "$target-$action" in
    backend-start)   start_backend ;;
    backend-stop)    stop_pid_file "$BACKEND_PID_FILE" "backend" ;;
    backend-restart) stop_pid_file "$BACKEND_PID_FILE" "backend"; start_backend ;;
    backend-status)  status_of "$BACKEND_PID_FILE" "backend" 8000 ;;
    frontend-start)   start_frontend ;;
    frontend-stop)    stop_pid_file "$FRONTEND_PID_FILE" "frontend" ;;
    frontend-restart) stop_pid_file "$FRONTEND_PID_FILE" "frontend"; start_frontend ;;
    frontend-status)  status_of "$FRONTEND_PID_FILE" "frontend" 3000 ;;
    frontend2-start)   start_frontend2 ;;
    frontend2-stop)    stop_pid_file "$FRONTEND2_PID_FILE" "frontend2" ;;
    frontend2-restart) stop_pid_file "$FRONTEND2_PID_FILE" "frontend2"; start_frontend2 ;;
    frontend2-status)  status_of "$FRONTEND2_PID_FILE" "frontend2" 3001 ;;
    watchdog-start)   start_watchdog ;;
    watchdog-stop)    stop_pid_file "$WATCHDOG_PID_FILE" "watchdog" ;;
    watchdog-restart) stop_pid_file "$WATCHDOG_PID_FILE" "watchdog"; start_watchdog ;;
    watchdog-status)  status_of "$WATCHDOG_PID_FILE" "watchdog" "-" ;;
    *) usage ;;
  esac
}

if [ "$TARGET" = "all" ]; then
  run_one backend "$ACTION"
  run_one frontend "$ACTION"
  run_one frontend2 "$ACTION"
else
  run_one "$TARGET" "$ACTION"
fi
