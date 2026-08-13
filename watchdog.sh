#!/usr/bin/env bash
# 백엔드/프론트 상시 구동 워치독.
# 일정 주기로 두 서버가 살아있는지 확인하고, 죽어 있으면 manage.sh로 재시작한다.
# 직접 실행하지 말고 `./manage.sh watchdog start`로 켜는 것을 권장한다.

set -uo pipefail
cd "$(dirname "$0")"

INTERVAL="${WATCHDOG_INTERVAL:-30}"
LOG=".run/watchdog.log"
mkdir -p .run

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

log "watchdog 시작 (PID $$, ${INTERVAL}초 주기)"

while true; do
  if ! ./manage.sh backend status | grep -q "실행 중"; then
    log "backend 다운 감지 -> 재시작"
    ./manage.sh backend start >> "$LOG" 2>&1
  fi
  if ! ./manage.sh frontend status | grep -q "실행 중"; then
    log "frontend 다운 감지 -> 재시작"
    ./manage.sh frontend start >> "$LOG" 2>&1
  fi
  sleep "$INTERVAL"
done
