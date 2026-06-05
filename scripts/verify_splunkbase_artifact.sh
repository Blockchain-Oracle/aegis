#!/usr/bin/env bash
# Verify a Splunkbase artifact end-to-end.
#
# Used by:
#   - Local dev as the gate after `build_splunk_app_tgz.sh`
#   - CI release lane (story-cicd-08) before publishing a GitHub Release
#
# Steps:
#   1. tarball exists and is a valid gzip
#   2. extracts cleanly into a temp dir
#   3. top-level dir is aegis_app/ (Splunk convention)
#   4. required files present: default/app.conf, README, LICENSE,
#      META-INF/manifest.json
#   5. no dev cruft (no __pycache__, no .pyc, no tests/)
#   6. manifest.json info.version matches default/app.conf version
#   7. AppInspect (if installed) passes against the extracted tree
#
# Usage:
#   bash scripts/verify_splunkbase_artifact.sh dist/aegis_app-1.0.0.tgz
set -euo pipefail

ARTIFACT="${1:-}"
if [ -z "${ARTIFACT}" ] || [ ! -f "${ARTIFACT}" ]; then
  echo "usage: $0 <path/to/aegis_app-VERSION.tgz>" >&2
  exit 2
fi

# 1. gzip header check
file "${ARTIFACT}" | grep -q "gzip compressed" || {
  echo "${ARTIFACT} is not a gzip file" >&2
  exit 1
}

# 2. Extract into a temp dir we clean on exit.
TMPDIR_EXTRACT=$(mktemp -d)
trap 'rm -rf "${TMPDIR_EXTRACT}"' EXIT
tar -xzf "${ARTIFACT}" -C "${TMPDIR_EXTRACT}"

# 3. Top-level dir
APP_ROOT="${TMPDIR_EXTRACT}/aegis_app"
if [ ! -d "${APP_ROOT}" ]; then
  echo "artifact does not have aegis_app/ as top-level directory" >&2
  exit 1
fi

# 4. Required files
REQUIRED=(
  "default/app.conf"
  "README"
  "LICENSE"
  "META-INF/manifest.json"
)
for path in "${REQUIRED[@]}"; do
  if [ ! -f "${APP_ROOT}/${path}" ]; then
    echo "missing required file: aegis_app/${path}" >&2
    exit 1
  fi
done

# 5. No dev cruft
if find "${APP_ROOT}" \( -name "__pycache__" -o -name "*.pyc" -o -name ".DS_Store" -o -name "tests" \) | grep -q .; then
  echo "artifact contains dev cruft:" >&2
  find "${APP_ROOT}" \( -name "__pycache__" -o -name "*.pyc" -o -name ".DS_Store" -o -name "tests" \) >&2
  exit 1
fi

# 6. Manifest <-> app.conf version match
MANIFEST_VERSION=$(uv run python -c "import json; print(json.load(open('${APP_ROOT}/META-INF/manifest.json'))['info']['version'])")
APP_VERSION=$(awk -F= '/^version[[:space:]]*=/ {gsub(/[[:space:]]/,"",$2); print $2; exit}' "${APP_ROOT}/default/app.conf")
if [ "${MANIFEST_VERSION}" != "${APP_VERSION}" ]; then
  echo "manifest.json version '${MANIFEST_VERSION}' != app.conf version '${APP_VERSION}'" >&2
  exit 1
fi

# 7. AppInspect (best effort; only if installed locally)
if command -v splunk-appinspect >/dev/null 2>&1 || uv run splunk-appinspect --version >/dev/null 2>&1; then
  echo "running AppInspect on extracted tree..."
  APP_DIR="${APP_ROOT}" OUTPUT_DIR="${TMPDIR_EXTRACT}" \
    bash "${APP_ROOT}/scripts/run_appinspect.sh" || {
      echo "AppInspect failed on extracted tree" >&2
      exit 1
    }
fi

echo "OK: ${ARTIFACT} passed all checks"
