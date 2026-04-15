#!/bin/bash
# Poll ntfy for messages. Two modes:
#   --log SELF_ID   : Append all non-self messages to a log file (runs forever)
#   --alert SELF_ID : Exit on first non-self message (triggers task notification)
#
# Usage:
#   bash tools/poll_ntfy.sh --log ORCHESTRATOR-B    # background logger
#   bash tools/poll_ntfy.sh --alert ORCHESTRATOR-B  # one-shot alert

MODE="${1:?Usage: poll_ntfy.sh --log|--alert SELF_ID}"
SELF_ID="${2:?Usage: poll_ntfy.sh --log|--alert SELF_ID}"
TOPIC="${CLAB_NTFY_TOPIC:-clement_research_supervisor}"
LOGFILE="/run/user/2011/ntfy_messages.log"
SEEN_FILE="/run/user/2011/ntfy_seen_ids.txt"

touch "$SEEN_FILE" "$LOGFILE"

filter_new_messages() {
  curl -s "ntfy.sh/$TOPIC/json?poll=1&since=2m" 2>/dev/null | python3 -c "
import json, sys
seen_file = '$SEEN_FILE'
self_prefix = '${SELF_ID}:'
try:
    seen = set(open(seen_file).read().split())
except:
    seen = set()
new_ids = []
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        obj = json.loads(line)
        mid = obj.get('id','')
        msg = obj.get('message','')
        if mid in seen: continue
        if msg and not msg.startswith(self_prefix):
            print(msg)
            new_ids.append(mid)
        # Always mark as seen (including own messages)
        new_ids.append(mid)
    except: pass
if new_ids:
    with open(seen_file, 'a') as f:
        for mid in set(new_ids):
            f.write(mid + '\n')
" 2>/dev/null
}

case "$MODE" in
  --log)
    while true; do
      result=$(filter_new_messages)
      if [ -n "$result" ]; then
        echo "[$(date '+%H:%M:%S')] $result" | tee -a "$LOGFILE"
      fi
      sleep 15
    done
    ;;
  --alert)
    while true; do
      result=$(filter_new_messages)
      if [ -n "$result" ]; then
        echo "NTFY MESSAGE: $result"
        exit 0
      fi
      sleep 15
    done
    ;;
  *)
    echo "Unknown mode: $MODE. Use --log or --alert"
    exit 1
    ;;
esac
