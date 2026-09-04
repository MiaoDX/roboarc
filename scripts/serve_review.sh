#!/usr/bin/env bash
set -euo pipefail

host="0.0.0.0"
web_port="5173"
artifact_port="8080"
artifact_dir="artifacts/tiago-proof-final"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) host="$2"; shift 2;;
    --web-port) web_port="$2"; shift 2;;
    --artifact-port) artifact_port="$2"; shift 2;;
    --artifacts) artifact_dir="$2"; shift 2;;
    *) echo "usage: $0 [--host HOST] [--web-port PORT] [--artifact-port PORT] [--artifacts DIR]" >&2; exit 2;;
  esac
done

artifact_dir="$(cd "$artifact_dir" 2>/dev/null && pwd)" || {
  echo "artifact directory not found: $artifact_dir" >&2
  exit 2
}
[[ -f "$artifact_dir/review.json" ]] || { echo "review manifest not found: $artifact_dir/review.json" >&2; exit 2; }
command -v python >/dev/null || { echo "python is required" >&2; exit 2; }
command -v npm >/dev/null || { echo "npm is required" >&2; exit 2; }
python "$repo_root/scripts/validate_review_artifacts.py" "$artifact_dir" >/dev/null

if [[ ! -f "$repo_root/web/dist/index.html" ]]; then
  npm --prefix "$repo_root/web" run build
fi

cleanup() {
  kill "${artifact_pid:-}" "${web_pid:-}" 2>/dev/null || true
  wait "${artifact_pid:-}" "${web_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python -m http.server "$artifact_port" --directory "$artifact_dir" --bind "$host" &
artifact_pid=$!
ROBOARC_ARTIFACT_TARGET="http://127.0.0.1:${artifact_port}" npm --prefix "$repo_root/web" run preview -- --host "$host" --port "$web_port" &
web_pid=$!
echo "Review URL: http://127.0.0.1:${web_port}/?review"
echo "LAN URL: http://<host-lan-ip>:${web_port}/?review"
wait "$web_pid"
