#!/usr/bin/env bash
# run.sh LABEL MODEL [extra flywheel run args]: one subscription experiment over dataset.jsonl.
set -euo pipefail
cd "$(dirname "$0")"
. /home/user/ext/venv-sql/bin/activate
export LANGSMITH_TRACING=false FW_TRANSPORT=${FW_TRANSPORT:-subscription} FW_MODEL=$2
export SUBCHAT_USAGE_LOG=$PWD/runs/$1.usage.jsonl SUBCHAT_PARALLEL=4
label=$1; shift 2
flywheel run --label "$label" --out "runs/$label.json" --concurrency 4 "$@" > "runs/$label.log" 2>&1
echo "done $label"
