#!/bin/sh
set -eu

dir=$(cd "$(dirname "$0")/.." && pwd)
EXE="${EXE:-exploit}"
dev=/data/local/tmp

[ -f "$dir/$EXE" ] || { echo "missing $dir/$EXE — build it first (see README)" >&2; exit 1; }
adb push "$dir/$EXE" "$dev/$EXE" >/dev/null
adb shell chmod 755 "$dev/$EXE"
adb push "$dir/scripts/root_cmd.daemon" /tmp/root_cmd >/dev/null   # init-hook always runs it

echo "[run] bootstrap-daemon"
adb shell "$dev/$EXE"

sleep 1
status=$(adb shell 'cat /data/local/tmp/.rc/status 2>/dev/null' | tr -d '\r' | tr '\n' ' ')
echo "[run] root server: $status"
