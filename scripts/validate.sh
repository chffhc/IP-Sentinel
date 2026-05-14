#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Running Python unittest suite"
python3 -m unittest discover -s tests -v

echo "==> Validating JSON files"
python3 - <<'PY'
import json
from pathlib import Path
for path in sorted(Path('.').rglob('*.json')):
    with path.open(encoding='utf-8') as fh:
        json.load(fh)
print('JSON validation passed')
PY

echo "==> Running bash syntax checks"
while IFS= read -r script; do
    bash -n "$script"
done < <(find . -type f -name '*.sh' -not -path './.git/*' | sort)

echo "==> Running optional shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck $(find . -type f -name '*.sh' -not -path './.git/*' | sort)
else
    echo "shellcheck not installed; skipping"
fi

echo "==> Running optional shfmt check"
if command -v shfmt >/dev/null 2>&1; then
    shfmt -d $(find . -type f -name '*.sh' -not -path './.git/*' | sort)
else
    echo "shfmt not installed; skipping"
fi

echo "==> Validation complete"
