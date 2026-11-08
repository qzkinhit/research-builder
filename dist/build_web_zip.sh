#!/usr/bin/env bash
# Build the claude.ai upload package dist/research-builder-web.zip and check the four upload rules:
#   exactly one SKILL.md, ASCII-only paths, description of at most 1024 characters, size under 30 MB.
# The local Claude Code and Codex versions are not affected, the transformation happens in a staging copy.
#   bash dist/build_web_zip.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STG="$(mktemp -d)/research-builder"; mkdir -p "$STG"

# 1) copy, leaving out git data, build outputs, the separate PPT skill and your own materials
rsync -a --exclude '.git' --exclude 'dist' --exclude '__pycache__' --exclude '*.pyc' --exclude '.DS_Store' \
  --exclude 'paper-figure-pptx' --exclude 'figure-style/examples/out' \
  --exclude 'researched_papers/*' --include 'materials/README.md' --include 'materials/**/README.md' --include 'materials/*/' \
  --exclude 'materials/**' \
  "$REPO/" "$STG/"

# 2) exactly one SKILL.md: each nested skill S becomes S/S.md
for S in paper-survey paper-rebuttal; do
  [ -f "$STG/$S/SKILL.md" ] && mv "$STG/$S/SKILL.md" "$STG/$S/$S.md"
  grep -rlF "$S/SKILL.md" "$STG" --include='*.md' 2>/dev/null | while read -r t; do
    python3 -c "import sys;p,n=sys.argv[1:3];s=open(p,encoding='utf-8').read();open(p,'w',encoding='utf-8').write(s.replace(n+'/SKILL.md',n+'/'+n+'.md'))" "$t" "$S"
  done || true
done

# 3) package with research-builder/ as the root
OUT="$REPO/dist/research-builder-web.zip"; rm -f "$OUT"
( cd "$STG/.." && zip -qr "$OUT" research-builder )

# 4) check the four rules
echo "== checks =="
echo "SKILL.md count (=1): $(unzip -Z1 "$OUT" | grep -c '/SKILL.md$')"
echo "non-ASCII paths (=0): $(unzip -Z1 "$OUT" | LC_ALL=C grep -c '[^ -~]' || true)"
DLEN=$(unzip -p "$OUT" research-builder/SKILL.md | python3 -c "import sys
for l in sys.stdin:
    if l.startswith('description:'):print(len(l[len('description: '):].rstrip('\n')));break")
echo "description length (<=1024): $DLEN"
echo "size (<30M): $(ls -lh "$OUT" | awk '{print $5}')"
rm -rf "$(dirname "$STG")"
echo "-> $OUT"
