#!/usr/bin/env bash
set -euo pipefail

OUTPUT="review_packet2.txt"

write_file() {
  local file="$1"
  echo "---" >> "${OUTPUT}"
  echo "FILE: ${file}" >> "${OUTPUT}"
  echo "---" >> "${OUTPUT}"
  cat "${file}" >> "${OUTPUT}"
  echo "" >> "${OUTPUT}"
}

: > "${OUTPUT}"

if [ -d "spec" ]; then
  while IFS= read -r file; do
    write_file "${file}"
  done < <(find spec -type f | sort)
fi

for file in contracts/*.json; do
  if [ -f "${file}" ]; then
    write_file "${file}"
  fi
done

if [ -d "fixtures" ]; then
  while IFS= read -r file; do
    write_file "${file}"
  done < <(find fixtures -type f | sort)
fi

for file in rulecraft/serializer.py rulecraft/verifier.py rulecraft/policy.py; do
  if [ -f "${file}" ]; then
    write_file "${file}"
  fi
done

if [ -d "tests" ]; then
  while IFS= read -r file; do
    write_file "${file}"
  done < <(find tests -type f | sort)
fi
