# make              导出 OpenReview 文本与字符数，再 xelatex 两遍
# make check        只导出并统计字符数
# make strict       导出，超限、有 \pending、有待填写回复块、(k of n) 标签或审稿人列表不一致、Markdown 有隐患时返回非零
# make test         导出脚本自测
# make verify       核对 reviews_bilingual.tex 中的英文原文与 source/reviews.md 逐字一致
# make drafts       把主文件各节写成 drafts/<节>.tex
# make drafts-check 核对 drafts 与主文件一致
# make render       用 markdown-it 与 KaTeX 渲染导出文本，需要 NM=<node_modules 目录>
# make clean        删除编译中间文件

PYTHON ?= python3
MAIN   := $(shell $(PYTHON) -c "import json,os;print(os.path.splitext(json.load(open('kit.json'))['main'])[0])")
LATEX  := xelatex -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: all check strict test verify pdf drafts drafts-check render clean

all: check pdf

check:
	$(PYTHON) tools/export_openreview.py

strict:
	$(PYTHON) tools/export_openreview.py --strict
	$(PYTHON) tools/check_markdown.py --strict

pdf:
	$(LATEX) $(MAIN).tex > /dev/null || (tail -n 40 $(MAIN).log; exit 1)
	$(LATEX) $(MAIN).tex > /dev/null || (tail -n 40 $(MAIN).log; exit 1)
	@grep -E "^(LaTeX|Package).*(Warning|Error)|Missing character" $(MAIN).log || true
	@echo "PDF: $(MAIN).pdf"

test:
	$(PYTHON) tools/test_export_openreview.py

verify:
	$(PYTHON) tools/check_reviews.py

drafts:
	$(PYTHON) tools/sync_drafts.py

drafts-check:
	$(PYTHON) tools/sync_drafts.py --check

render:
	NM=$(NM) node tools/render_check.js openreview/*.md

clean:
	rm -f $(MAIN).aux $(MAIN).log $(MAIN).out $(MAIN).toc $(MAIN).xdv
