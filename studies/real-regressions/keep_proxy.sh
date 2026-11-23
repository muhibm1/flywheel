#!/usr/bin/env bash
# Keep the endpoint up: start proxy.py detached (so a stopped watchdog does not take it down) and
# restart it whenever it stops answering. Usage: bash keep_proxy.sh
cd "$(dirname "$0")" || exit 1
export PROXY_USAGE_LOG=/tmp/rr-usage.jsonl PROXY_PARALLEL=6
up() { curl -s -m 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/v1/models | grep -q 200; }
while true; do
  if ! up; then
    sleep 3
    if ! up; then
      echo "$(date -u +%FT%TZ) endpoint down, starting" >> /tmp/rr-keep-proxy.log
      setsid nohup python3 proxy.py --port 8765 >> /tmp/rr-proxy.log 2>&1 < /dev/null &
      sleep 8
    fi
  fi
  sleep 10
done
