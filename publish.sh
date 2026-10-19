#!/bin/bash
# Rebuild data.json from the master list and publish to GitHub Pages.
# Usage: /workspace/nerd-liquor-site/publish.sh ["commit message"]
set -e
cd /workspace/nerd-liquor-site
python3 build_data.py /workspace/nerd-liquor-master-list.md
git add -A
git commit -m "${1:-Update nerd liquor list $(date +%F)}" || echo "nothing to commit"
git push origin main
echo "Live (after ~1 min): https://r2m5bp7nkz-svg.github.io/nerd-liquor/"
