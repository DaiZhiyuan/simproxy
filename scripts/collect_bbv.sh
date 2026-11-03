#!/usr/bin/env bash
# Collect a SimPoint BBV from a binary using DynamoRIO.
#
# Usage: collect_bbv.sh <binary> [interval] [output.bbv]
# Env:   DRRUN   path to drrun (default: drrun)
#        CLIENT  DynamoRIO client name (default: drpoints)
set -euo pipefail

BIN="${1:?usage: collect_bbv.sh <binary> [interval] [output.bbv]}"
INTERVAL="${2:-100000000}"
OUT="${3:-}"
DRRUN="${DRRUN:-drrun}"
CLIENT="${CLIENT:-drpoints}"

if [[ ! -x "${BIN}" ]]; then
  echo "error: '${BIN}' is not executable" >&2
  exit 1
fi

if [[ "${CLIENT}" == "drpoints" ]]; then
  if [[ -n "${OUT}" ]]; then
    "${DRRUN}" -t drpoints -instr_interval "${INTERVAL}" -out_bbv_file "${OUT}" -- "${BIN}"
  else
    "${DRRUN}" -t drpoints -instr_interval "${INTERVAL}" -- "${BIN}"
  fi
else
  if [[ -n "${OUT}" ]]; then
    "${DRRUN}" -t "${CLIENT}" -instr_interval "${INTERVAL}" -out_file "${OUT}" -- "${BIN}"
  else
    "${DRRUN}" -t "${CLIENT}" -instr_interval "${INTERVAL}" -- "${BIN}"
  fi
fi
