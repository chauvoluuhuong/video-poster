#!/usr/bin/env bash
# Everything CI checks: manifests are valid JSON, scripts compile, unit + form end-to-end tests pass.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c "import json; [json.load(open(f)) for f in ('.claude-plugin/plugin.json', '.claude-plugin/marketplace.json')]"
python3 -m py_compile skills/post-video/scripts/*.py
grep -q '^name: post-video$' skills/post-video/SKILL.md
grep -q '^name: description-file$' skills/description-file/SKILL.md
grep -q '^model: sonnet$' agents/uploader.md
python3 -m unittest discover -s tests -v
