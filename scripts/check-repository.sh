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

credential_pattern='(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})'
if git grep -IEn "$credential_pattern" -- .; then
  echo "ERROR: probable credential detected" >&2
  exit 1
fi
credential_history=$(git log --all -G"$credential_pattern" --format='%H' -- .)
if [[ -n "$credential_history" ]]; then
  echo "ERROR: probable credential detected in Git history" >&2
  exit 1
fi

large_history_objects=$(
  git rev-list --objects --all |
    git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' |
    awk '$1 == "blob" && $2 > 10485760 { print $3 }'
)
if [[ -n "$large_history_objects" ]]; then
  echo "ERROR: blob larger than 10 MiB detected in Git history" >&2
  printf '%s\n' "$large_history_objects" >&2
  exit 1
fi

echo "repository privacy checks passed"
