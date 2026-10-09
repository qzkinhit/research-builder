#!/usr/bin/env bash
# Install the research-builder skill (kit) into ~/.claude/skills/research-builder/.
# Run from a clone of this repo: `bash install.sh` or `bash install.sh --pptx-only`.
# Copies the skill files, knowledge/, templates/ and the user's own materials/ (if any);
# researched_papers/ stays a local dropbox.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
PPTX_ONLY=0
TARGET_ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pptx-only) PPTX_ONLY=1; shift ;;
    --target-root)
      [ "$#" -ge 2 ] && [ -n "$2" ] || { echo "--target-root requires a directory" >&2; exit 2; }
      TARGET_ROOT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash install.sh [--pptx-only] [--target-root DIRECTORY]"
      echo "--target-root installs under DIRECTORY/.claude for isolated verification."
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
CL="${TARGET_ROOT:-$HOME}/.claude"
DEST="$CL/skills/research-builder"
PPTX="$CL/skills/paper-figure-pptx"

install_pptx() {
  local stage backup="" backup_root nested
  [ -f "$SRC/paper-figure-pptx/SKILL.md" ] || { echo "Missing paper-figure-pptx/SKILL.md" >&2; return 1; }
  mkdir -p "$CL/skills" "$CL/skill_install_staging"
  stage="$(mktemp -d "$CL/skill_install_staging/paper-figure-pptx.XXXXXX")"
  if ! rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude '.DS_Store' "$SRC/paper-figure-pptx/" "$stage/"; then
    rm -rf "$stage"; return 1
  fi
  if [ -e "$PPTX" ] || [ -L "$PPTX" ]; then
    mkdir -p "$CL/skill_backups"
    backup_root="$(mktemp -d "$CL/skill_backups/pptx_$(date +%Y%m%d_%H%M%S).XXXXXX")"
    backup="$backup_root/paper-figure-pptx"
    mv "$PPTX" "$backup"
  fi
  if ! mv "$stage" "$PPTX"; then
    [ -z "$backup" ] || mv "$backup" "$PPTX"
    rm -rf "$stage"; return 1
  fi
  # Retire only the obsolete nested PPT skill, keeping unrelated RB files intact.
  nested="$CL/skills/research-builder/paper-figure-pptx"
  if { [ -e "$nested" ] || [ -L "$nested" ]; } && ! [ "$nested" -ef "$SRC/paper-figure-pptx" ]; then
    mkdir -p "$CL/skill_backups"
    backup_root="$(mktemp -d "$CL/skill_backups/nested_pptx_$(date +%Y%m%d_%H%M%S).XXXXXX")"
    mv "$nested" "$backup_root/paper-figure-pptx"
    echo "previous nested PPT skill backup -> $backup_root/paper-figure-pptx"
  fi
  echo "installed paper-figure-pptx -> $PPTX"
  [ -z "$backup" ] || echo "previous PPT skill backup -> $backup"
}

# Validate the independent source before changing any installed skills.
[ -f "$SRC/paper-figure-pptx/SKILL.md" ] || { echo "Missing paper-figure-pptx/SKILL.md" >&2; exit 1; }
if [ "$PPTX_ONLY" -eq 1 ]; then
  install_pptx
  exit 0
fi
mkdir -p "$DEST"
if [ "$SRC" -ef "$DEST" ]; then
  echo "research-builder source already at $DEST"
else
  rsync -a --exclude '.git' --exclude 'paper-figure-pptx' --exclude 'dist' "$SRC/" "$DEST/"
fi
echo "installed research-builder -> $DEST"
echo "  skill:     SKILL.md + writing-playbook.md + writing-deai.md + diagnostic-playbook.md + knowledge/ + templates/"
echo "  materials: $(find "$DEST/materials" -type f ! -name 'README.md' ! -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ') user files (see materials/README.md)"

# 把 paper-survey 部署成独立可发现 skill
PS="$CL/skills/paper-survey"
rm -rf "$PS" && cp -R "$SRC/paper-survey" "$PS" && chmod +x "$PS/tools/"*.sh 2>/dev/null || true
echo "installed paper-survey  -> $PS"
install_pptx
echo ""
echo "用法: 「按 research-builder 启动」(科研、写论文、画图、润色) 或 「按 paper-survey 调研」(LaTeX 与 HTML 优先)"
echo "Codex 版见 $DEST/codex/README.md，完整说明见 $DEST/USAGE.md"
