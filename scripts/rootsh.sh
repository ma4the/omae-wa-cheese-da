#!/bin/sh
set -eu

rc=/data/local/tmp/.rc
cmd="${*:-}"
[ -n "$cmd" ] || cmd="$(cat)"

if ! adb shell "[ -p $rc/in ]" 2>/dev/null; then
    echo "root server FIFO $rc/in not present; run run.sh first" >&2
    exit 1
fi

sentinel="__RC_DONE_$$_$(adb shell 'echo $RANDOM' | tr -d '\r')"
adb shell "printf '%s\n' '$cmd; echo $sentinel' > $rc/in"

i=0
while [ "$i" -lt 50 ]; do
    out="$(adb shell "cat $rc/out 2>/dev/null" | tr -d '\r')"
    case "$out" in
        *"$sentinel"*) printf '%s\n' "$out" | sed "/$sentinel/d"; exit 0 ;;
    esac
    i=$((i + 1)); sleep 0.2
done

echo "timeout waiting for root server output" >&2
exit 2
