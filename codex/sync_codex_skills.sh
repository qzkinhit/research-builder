#!/usr/bin/env bash
# 将本仓库的 research-builder、paper-survey 与独立 paper-figure-pptx 同步给 Codex。
# 用法：bash codex/sync_codex_skills.sh [--pptx-only] [--target-root DIRECTORY]
# 做的事：
#   1. 旧的两个 skill 目录先备份到 ~/.codex/skill_backups/<时间戳>/(放在 skills 目录之外，免得被重复加载)
#   2. 仓库内容镜像到 skill 目录，保留各自的 agents/openai.yaml
#   3. SKILL.md 换成 Codex 版：description 裁到 1024 字符以内，加一段 Codex 适配说明，路径 ~/.claude/skills 改成 ~/.codex/skills
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PPTX_ONLY=0
TARGET_ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pptx-only) PPTX_ONLY=1; shift ;;
    --target-root)
      [ "$#" -ge 2 ] && [ -n "$2" ] || { echo "--target-root requires a directory" >&2; exit 2; }
      TARGET_ROOT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash codex/sync_codex_skills.sh [--pptx-only] [--target-root DIRECTORY]"
      echo "--target-root installs under DIRECTORY/.codex and DIRECTORY/.agents."
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
if [ -n "$TARGET_ROOT" ]; then
  mkdir -p "$TARGET_ROOT"
  TARGET_ROOT="$(cd "$TARGET_ROOT" && pwd)"
  CX="$TARGET_ROOT/.codex"
  DISCOVERY_ROOT="$TARGET_ROOT/.agents/skills"
else
  CX="${CODEX_HOME:-$HOME/.codex}"
  DISCOVERY_ROOT="$HOME/.agents/skills"
fi
# Resolve an absolute target so the discovery symlink also works with a relative CODEX_HOME.
mkdir -p "$CX"
CX="$(cd "$CX" && pwd)"
PPTX="$CX/skills/paper-figure-pptx"

install_pptx() {
  local stage backup="" backup_root link_path nested
  [ -f "$REPO/paper-figure-pptx/SKILL.md" ] || { echo "Missing paper-figure-pptx/SKILL.md" >&2; return 1; }
  mkdir -p "$CX/skills" "$CX/skill_install_staging"
  stage="$(mktemp -d "$CX/skill_install_staging/paper-figure-pptx.XXXXXX")"
  if ! rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude '.DS_Store' "$REPO/paper-figure-pptx/" "$stage/"; then
    rm -rf "$stage"; return 1
  fi
  if [ -e "$PPTX" ] || [ -L "$PPTX" ]; then
    mkdir -p "$CX/skill_backups"
    backup_root="$(mktemp -d "$CX/skill_backups/pptx_$(date +%Y%m%d_%H%M%S).XXXXXX")"
    backup="$backup_root/paper-figure-pptx"
    mv "$PPTX" "$backup"
  fi
  if ! mv "$stage" "$PPTX"; then
    [ -z "$backup" ] || mv "$backup" "$PPTX"
    rm -rf "$stage"; return 1
  fi
  mkdir -p "$DISCOVERY_ROOT"
  link_path="$DISCOVERY_ROOT/paper-figure-pptx"
  if [ "$DISCOVERY_ROOT" -ef "$CX/skills" ]; then
    echo "Codex discovery directory already points to $CX/skills"
  elif [ -L "$link_path" ] && [ "$link_path" -ef "$PPTX" ]; then
    : # The existing discovery alias already resolves to the single installed copy.
  else
    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
      mkdir -p "$CX/skill_backups"
      backup_root="$(mktemp -d "$CX/skill_backups/pptx_discovery_$(date +%Y%m%d_%H%M%S).XXXXXX")"
      mv "$link_path" "$backup_root/paper-figure-pptx"
      echo "previous discovery entry backup -> $backup_root/paper-figure-pptx"
    fi
    ln -s "$PPTX" "$link_path"
  fi
  # Retire only the obsolete nested PPT skill, keeping unrelated RB files intact.
  nested="$CX/skills/research-builder/paper-figure-pptx"
  if { [ -e "$nested" ] || [ -L "$nested" ]; } && ! [ "$nested" -ef "$REPO/paper-figure-pptx" ]; then
    mkdir -p "$CX/skill_backups"
    backup_root="$(mktemp -d "$CX/skill_backups/nested_pptx_$(date +%Y%m%d_%H%M%S).XXXXXX")"
    mv "$nested" "$backup_root/paper-figure-pptx"
    echo "previous nested PPT skill backup -> $backup_root/paper-figure-pptx"
  fi
  echo "synced paper-figure-pptx -> $PPTX"
  echo "Codex discovery alias -> $link_path"
  [ -z "$backup" ] || echo "previous PPT skill backup -> $backup"
}

[ -f "$REPO/paper-figure-pptx/SKILL.md" ] || { echo "Missing paper-figure-pptx/SKILL.md" >&2; exit 1; }
if [ "$PPTX_ONLY" -eq 1 ]; then
  install_pptx
  exit 0
fi
RB="$CX/skills/research-builder"
PS="$CX/skills/paper-survey"
mkdir -p "$CX/skill_backups"
BK="$(mktemp -d "$CX/skill_backups/$(date +%Y%m%d_%H%M%S).XXXXXX")"
mkdir -p "$RB" "$PS"
cp -R "$RB" "$BK/" 2>/dev/null || true
cp -R "$PS" "$BK/" 2>/dev/null || true

COMMON_EXCLUDES=(--exclude '.git' --exclude '.DS_Store' --exclude '__pycache__' --filter 'P agents/')
rsync -a --delete "${COMMON_EXCLUDES[@]}" \
  --exclude 'dist' --exclude 'codex' --exclude 'paper-survey' --exclude 'paper-figure-pptx' --exclude 'researched_papers/*.pdf' \
  "$REPO/" "$RB/"
rsync -a --delete "${COMMON_EXCLUDES[@]}" "$REPO/paper-survey/" "$PS/"
chmod +x "$PS/tools/"*.sh 2>/dev/null || true

RB_DESC='把调研好的相关论文、研究方向和用户自己的素材做成能跑的研究系统、忠实复现的 baseline、严谨的实验和回填好的中英文论文，并按用户已发表论文的风格写作、排实验表、画实验图、写本子与 rebuttal、去 AI 腔润色 Word 与 PPT、做投稿前检查。用户说「按 research-builder 启动」「改进我这篇论文」「复现这些 baseline」「回填实验章、排主表、画实验图」「润色、去 AI 味、投稿前检查」「写本子」「写 rebuttal」时使用。'
PS_DESC='LaTeX/HTML 优先的论文调研工作流。Use when the user wants to survey a research topic, find baselines and related work, prioritize arXiv source or ar5iv HTML over PDF, screen papers by CCF-A authority and open-source availability, download papers into researched_papers, produce survey.md, or continue into research-builder for writing.'
NOTE_RB='> **Codex 版说明**：本目录由 research-builder 仓库的 `codex/sync_codex_skills.sh` 生成，不要在这里手改。Codex 没有 Claude Code 的 subagent 与 Workflow，文中「派给 subagent」「并行派出」的步骤改为按顺序执行，或开多个 codex 会话手动并行。素材、手册与脚本路径都相对本目录，即 `~/.codex/skills/research-builder/`。'
NOTE_PS='> **Codex 版说明**：本目录由 research-builder 仓库的 `codex/sync_codex_skills.sh` 生成，不要在这里手改。Codex 没有子进程，「多子进程并行」的检索改为按顺序执行，或开多个 codex 会话手动并行。下载脚本在本目录的 `tools/fetch_arxiv.sh`。'

python3 - "$RB/SKILL.md" "$RB_DESC" "$NOTE_RB" "$PS/SKILL.md" "$PS_DESC" "$NOTE_PS" <<'PY'
import sys
def codexify(path, desc, note):
    L = open(path, encoding='utf-8').read().splitlines()
    for i, l in enumerate(L):
        if l.startswith('description:'):
            L[i] = 'description: ' + desc
            break
    # 适配说明放在第一个一级标题之后
    for i, l in enumerate(L):
        if l.startswith('# '):
            L[i + 1:i + 1] = ['', note]
            break
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
codexify(sys.argv[1], sys.argv[2], sys.argv[3])
codexify(sys.argv[4], sys.argv[5], sys.argv[6])
for d in (sys.argv[2], sys.argv[5]):
    assert len(d) <= 1024, len(d)
PY

# 文本里的 Claude 路径改成 Codex 路径
grep -rlF '.claude/skills/' "$RB" "$PS" --include='*.md' --include='*.py' --include='*.sh' 2>/dev/null | while read -r f; do
  python3 -c "import sys;p=sys.argv[1];s=open(p,encoding='utf-8').read();open(p,'w',encoding='utf-8').write(s.replace('.claude/skills/','.codex/skills/'))" "$f"
done

# agents/openai.yaml 缺失时补一个
[ -f "$RB/agents/openai.yaml" ] || { mkdir -p "$RB/agents"; cat > "$RB/agents/openai.yaml" <<'YAML'
interface:
  display_name: "Research Builder"
  short_description: "科研系统、实验论文、投稿审校、实验图与本子图工作流"
  default_prompt: "Use $research-builder to turn my research direction and related papers into a runnable system, faithful experiments, submission-ready writing, and figures in my house style."
YAML
}
[ -f "$PS/agents/openai.yaml" ] || { mkdir -p "$PS/agents"; cat > "$PS/agents/openai.yaml" <<'YAML'
interface:
  display_name: "Paper Survey"
  short_description: "LaTeX/HTML 优先调研论文、baseline 和相关工作"
  default_prompt: "Use $paper-survey to survey related work and baselines for my research topic with LaTeX/HTML-first paper reading."
YAML
}

install_pptx

echo "synced research-builder -> $RB"
echo "synced paper-survey     -> $PS"
echo "backup of the previous versions -> $BK"
