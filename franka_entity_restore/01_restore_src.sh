#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_FILE="${1:-${SCRIPT_DIR}/franka_ws_src_backup.tar.gz}"
WS_DIR="${HOME}/franka_ws"

echo "== Franka workspace source restore =="
echo "backup file: ${BACKUP_FILE}"
echo "workspace:   ${WS_DIR}"

if [ ! -f "${BACKUP_FILE}" ]; then
  FOUND="$(find /media "${HOME}" -type f -name 'franka_ws_src_backup.tar.gz' 2>/dev/null | head -n 1 || true)"
  if [ -n "${FOUND}" ]; then
    BACKUP_FILE="${FOUND}"
    echo "Automatically found backup: ${BACKUP_FILE}"
  else
    echo "ERROR: cannot find franka_ws_src_backup.tar.gz"
    echo "Expected beside this script: ${SCRIPT_DIR}/franka_ws_src_backup.tar.gz"
    exit 1
  fi
fi

mkdir -p "${WS_DIR}"

if [ -d "${WS_DIR}/src" ]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  echo "Existing ${WS_DIR}/src found. Backing it up to ${WS_DIR}/src.backup_${TS}"
  mv "${WS_DIR}/src" "${WS_DIR}/src.backup_${TS}"
fi

tar -xzf "${BACKUP_FILE}" -C "${WS_DIR}"

echo
echo "Restored source folders:"
ls "${WS_DIR}/src"

echo
echo "Done."
