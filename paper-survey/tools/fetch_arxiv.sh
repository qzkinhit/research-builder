#!/usr/bin/env bash
# fetch_arxiv.sh — 把一篇 arXiv 论文按 "LaTeX 源 > HTML > PDF" 的优先级下载下来。
# 模型读 LaTeX/HTML 远好于 PDF，所以默认只下 LaTeX 源 + ar5iv HTML，不下 PDF。
#
#   bash fetch_arxiv.sh <arxiv_id|url> [out_dir] [--pdf]
#   例: bash fetch_arxiv.sh 2302.03169 researched_papers
#
# 产出 out_dir/<id>/ ：latex/(解开的 .tex 源) + <id>.ar5iv.html + meta.txt(标题/作者/摘要)
set -euo pipefail
RAW="${1:?用法: fetch_arxiv.sh <arxiv_id|url> [out_dir] [--pdf]}"
OUT="${2:-researched_papers}"
WANT_PDF="no"; [[ "${3:-}" == "--pdf" ]] && WANT_PDF="yes"
# 从 id 或各种 URL 里抠出 arXiv id
ID="$(printf '%s' "$RAW" | grep -oE '[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?' | head -1)"
[ -z "$ID" ] && { echo "无法识别 arXiv id: $RAW"; exit 2; }
D="$OUT/$ID"; mkdir -p "$D/latex"
UA="Mozilla/5.0 (research-builder fetch_arxiv)"

echo "[$ID] 1/3 元信息..."
curl -sL --max-time 30 -A "$UA" "https://arxiv.org/abs/$ID" -o "$D/_abs.html" || true
{ echo "id: $ID"; echo "url: https://arxiv.org/abs/$ID";
  grep -oE '<title>[^<]+' "$D/_abs.html" 2>/dev/null | sed 's/<title>//' | head -1 | sed 's/^/title: /';
} > "$D/meta.txt"

echo "[$ID] 2/3 LaTeX 源(首选)..."
if curl -sL --max-time 60 -A "$UA" "https://arxiv.org/e-print/$ID" -o "$D/_src.tar.gz" \
   && tar -xzf "$D/_src.tar.gz" -C "$D/latex" 2>/dev/null; then
  N=$(find "$D/latex" -name '*.tex' | wc -l | tr -d ' ')
  echo "    解开 $N 个 .tex"
  # 猜主文件(含 \documentclass)
  MAIN=$(grep -rl '\\documentclass' "$D/latex" 2>/dev/null | head -1)
  [ -n "$MAIN" ] && echo "main_tex: ${MAIN#$D/}" >> "$D/meta.txt"
else
  echo "    LaTeX 源不可用，转 HTML"
fi

echo "[$ID] 3/3 ar5iv HTML(LaTeX 渲染，模型好读)..."
curl -sL --max-time 45 -A "$UA" "https://ar5iv.org/abs/$ID" -o "$D/$ID.ar5iv.html" || \
curl -sL --max-time 45 -A "$UA" "https://ar5iv.labs.arxiv.org/html/$ID" -o "$D/$ID.ar5iv.html" || true

if [ "$WANT_PDF" = "yes" ]; then
  echo "[$ID] (额外)PDF..."; curl -sL --max-time 60 -A "$UA" "https://arxiv.org/pdf/$ID" -o "$D/$ID.pdf" || true
fi
rm -f "$D/_src.tar.gz" "$D/_abs.html"
echo "[$ID] 完成 -> $D"
ls -la "$D" | awk '{print "   ", $5, $9}'
