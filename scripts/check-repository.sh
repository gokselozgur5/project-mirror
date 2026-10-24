#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"

forbidden_pattern='\.(mp4|mov|m4v|avi|wav|mp3|flac|onnx|engine|pth|safetensors)$'
repository_paths=$(
  {
    git ls-files
    git log --all --pretty=format: --name-only
  } | sort -u
)
if grep -Eiq "$forbidden_pattern" <<<"$repository_paths"; then
  echo "ERROR: private media or model artifact detected in Git history" >&2
  grep -Ei "$forbidden_pattern" <<<"$repository_paths" >&2
  exit 1
fi

if git grep -IEn '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})' -- .; then
  echo "ERROR: probable credential detected" >&2
  exit 1
fi

echo "repository privacy checks passed"
