# make test   导出脚本与全部检查脚本的自测
# make demo   在虚构示例上跑完整流程，产出 project/rebuttal_main.pdf、revision/revmark_demo.pdf 与 project/deliverables/
# make clean  删除全部生成文件，恢复到复制时的状态
# PDFPY 指向装有 pymupdf 的 Python，例如 make demo PDFPY=venv/bin/python

PYTHON ?= python3
PDFPY  ?= $(PYTHON)

.PHONY: test demo clean

test:
	$(MAKE) -C project test
	$(PYTHON) scripts/test_scripts.py

demo:
	$(MAKE) -C project check
	$(MAKE) -C project strict
	$(MAKE) -C project verify
	$(MAKE) -C project drafts
	$(MAKE) -C project drafts-check
	$(MAKE) -C project pdf
	cd revision && latexmk -xelatex -interaction=nonstopmode -halt-on-error revmark_demo.tex > /dev/null
	$(PYTHON) scripts/check_rounding.py --claims example/claims.csv --runs example/runs.csv --root .
	$(PYTHON) scripts/build_interval_map.py --config project/kit.json --runs example/runs.csv --comparisons example/comparisons.json --out project/interval_map.md
	$(PYTHON) scripts/check_glance_table.py --config project/kit.json --revision revision/revmark_demo.tex
	$(PYTHON) scripts/check_invariants.py dump project/invariants.json --config project/kit.json
	$(PYTHON) scripts/check_invariants.py compare project/invariants.json project/invariants.json
	$(PYTHON) scripts/check_invariants.py lint --config project/kit.json
	$(PYTHON) scripts/check_margin_tags.py --reviewers project/reviewers.tex --tex revision/revmark_demo.tex --reviews project/source/reviews.md --rebuttal project/rebuttal_main.tex
	@if $(PDFPY) -c "import pymupdf" 2>/dev/null; then \
	  $(PDFPY) scripts/check_margin_tags.py --reviewers project/reviewers.tex --pdf revision/revmark_demo.pdf --link-color 2F3FAF; \
	else echo "skip the PDF part of check_margin_tags.py, install pymupdf or set PDFPY"; fi
	$(PYTHON) scripts/build_deliverables.py --config project/kit.json --clean
	@echo "demo finished"

clean:
	$(MAKE) -C project clean
	rm -rf project/openreview project/deliverables project/drafts project/counts.tex project/interval_map.md project/invariants.json project/rebuttal_main.pdf
	cd revision && latexmk -C revmark_demo.tex > /dev/null 2>&1 || true
	rm -f revision/*.pdf revision/*.aux revision/*.log revision/*.out revision/*.fls revision/*.fdb_latexmk revision/*.xdv
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
