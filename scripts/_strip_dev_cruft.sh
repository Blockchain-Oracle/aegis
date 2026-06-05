#!/usr/bin/env bash
# Idempotent dev-cruft sweeper.
#
# Walks a target directory and removes files / dirs the Splunkbase
# tarball must not ship. Patterns mirror _pack_tarball.py's
# DEV_CRUFT_PATTERNS for the case where a maintainer wants to clean
# the source tree before AppInspect runs.
#
# Idempotent: running twice produces the same result as running once.
# Logs what got removed for build-log auditability.
#
# Usage:
#   scripts/_strip_dev_cruft.sh splunk_apps/aegis_app
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <directory>" >&2
  exit 2
fi
TARGET="$1"
if [ ! -d "${TARGET}" ]; then
  echo "not a directory: ${TARGET}" >&2
  exit 2
fi

PATTERNS=(
  "__pycache__"
  ".pytest_cache"
  ".mypy_cache"
)
FILE_PATTERNS=(
  "*.pyc"
  "*.pyo"
  ".DS_Store"
  "appinspect-report.json"
  "appinspect-summary.txt"
  ".appinspect.expect.yaml.bak"
)

removed=0
for pat in "${PATTERNS[@]}"; do
  while IFS= read -r -d '' dir; do
    echo "  removing dir: ${dir}"
    rm -rf "${dir}"
    removed=$((removed + 1))
  done < <(find "${TARGET}" -type d -name "${pat}" -print0)
done
for pat in "${FILE_PATTERNS[@]}"; do
  while IFS= read -r -d '' f; do
    echo "  removing file: ${f}"
    rm -f "${f}"
    removed=$((removed + 1))
  done < <(find "${TARGET}" -type f -name "${pat}" -print0)
done

echo "stripped ${removed} entries from ${TARGET}"
