#!/bin/bash
# Poll ntfy for supervisor messages, ignoring messages starting with "claude:"
# Usage: bash tools/ntfy_poll.sh

TIMESTAMP=$(date +%s)
while true; do
    msg=$(curl -s "ntfy.sh/$CLAB_NTFY_TOPIC/json?poll=1&since=${TIMESTAMP}" \
        | tail -1 \
        | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    m = d.get('message', '')
    if m and not m.lower().startswith('claude:'):
        print(m)
except: pass
" 2>/dev/null)
    if [ -n "$msg" ]; then
        echo "Supervisor: $msg"
        break
    fi
    sleep 15
done
