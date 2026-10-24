#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"

forbidden_pattern='\.(mp4|mov|m4v|avi|wav|mp3|flac|onnx|engine|pth|safetensors)$'
if git ls-files | grep -Eiq "$forbidden_pattern"; then
  echo "ERROR: tracked private media or model artifact detected" >&2
  git ls-files | grep -Ei "$forbidden_pattern" >&2
  exit 1
fi

if git grep -IEn '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})' -- .; then
  echo "ERROR: probable credential detected" >&2
  exit 1
fi

echo "repository privacy checks passed"
