#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Start AuditConsumer as background process
#
# Usage: ./scripts/start_audit.sh
#        ./scripts/start_audit.sh stop
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="/tmp/mems26_audit.pid"

cd "$REPO_ROOT"

# Load .env
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

case "${1:-start}" in
    stop)
        if [[ -f "$PID_FILE" ]]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "Audit consumer stopped (PID $PID)"
            else
                echo "Audit consumer not running (stale PID $PID)"
            fi
            rm -f "$PID_FILE"
        else
            echo "No PID file found"
        fi
        ;;
    start)
        # Check if already running
        if [[ -f "$PID_FILE" ]]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Audit consumer already running (PID $PID)"
                exit 0
            fi
            rm -f "$PID_FILE"
        fi

        echo "Starting AuditConsumer..."
        python3 -m backend.v9.audit.runner > /tmp/mems26_audit.log 2>&1 &
        echo $! > "$PID_FILE"
        echo "Audit consumer started (PID $(cat "$PID_FILE"))"
        echo "Log: /tmp/mems26_audit.log"
        ;;
    status)
        if [[ -f "$PID_FILE" ]]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Audit consumer running (PID $PID)"
            else
                echo "Audit consumer not running (stale PID)"
            fi
        else
            echo "Audit consumer not running"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
