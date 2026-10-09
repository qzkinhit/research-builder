#!/usr/bin/env python3
"""出稿排版体检:打开生成好的 .docx，揪出实战最常见的三类排版问题，不管它是哪个脚本生成的。
1) 表格单元格会首行缩进(正文有缩进、单元格却没显式清零 firstLineChars=0 -> 继承了缩进)。
2) 章节标题被居中(标题应左对齐)。
3) 提示参考文献是否可能没编号(粗查)。

  python docx_layout_check.py <file.docx>

只用标准库(zipfile+re),不依赖 python-docx。返回码非零表示有问题。
"""
import sys, re, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def body_indents(styles_xml):
    """正文(Normal 样式 / docDefaults)是否设了首行缩进。"""
    for m in re.finditer(r'<w:style\b[^>]*w:styleId="Normal".*?</w:style>', styles_xml, re.S):
        blk = m.group(0)
        ind = re.search(r'<w:ind\b([^>]*)/?>', blk)
        if ind and _has_firstline(ind.group(1)):
            return True
    dd = re.search(r'<w:docDefaults>.*?</w:docDefaults>', styles_xml, re.S)
    if dd:
        ind = re.search(r'<w:ind\b([^>]*)/?>', dd.group(0))
        if ind and _has_firstline(ind.group(1)):
            return True
    return False


def _has_firstline(attrs):
    fc = re.search(r'w:firstLineChars="(\d+)"', attrs)
    fl = re.search(r'w:firstLine="(\d+)"', attrs)
    return (fc and int(fc.group(1)) > 0) or (fl and int(fl.group(1)) > 0)


def _cell_para_indents(ppr):
    """给定单元格段落的 pPr 文本, 判断它会不会首行缩进(没显式清零就算会)。"""
    if not ppr:
        return True  # 无 pPr -> 继承正文缩进
    ind = re.search(r'<w:ind\b([^>]*)/?>', ppr)
    if not ind:
        return True  # 无 ind 覆盖 -> 继承
    a = ind.group(1)
    fc = re.search(r'w:firstLineChars="(\d+)"', a)
    fl = re.search(r'w:firstLine="(\d+)"', a)
    # 显式清零(firstLineChars=0)才算安全; 否则继承或有正值都算会缩进
    if fc and int(fc.group(1)) == 0:
        return False
    if _has_firstline(a):
        return True
    return fc is None and fl is None  # 只有别的属性没管首行 -> 仍继承


def main():
    if len(sys.argv) < 2:
        print("用法: python docx_layout_check.py <file.docx>"); return 2
    z = zipfile.ZipFile(sys.argv[1])
    doc = z.read("word/document.xml").decode("utf-8", "ignore")
    styles = z.read("word/styles.xml").decode("utf-8", "ignore") if "word/styles.xml" in z.namelist() else ""
    problems = 0

    # 1) 表格单元格首行缩进
    body_ind = body_indents(styles)
    bad_cells = 0
    for tc in re.findall(r"<w:tc>.*?</w:tc>", doc, re.S):
        for p in re.findall(r"<w:p\b.*?</w:p>", tc, re.S):
            ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
            if _cell_para_indents(ppr.group(0) if ppr else ""):
                if body_ind:  # 正文本身缩进, 单元格没清零才是真问题
                    bad_cells += 1
    if bad_cells:
        problems += bad_cells
        print(f"  [表格首行缩进] {bad_cells} 个单元格段会缩进 -> 每个单元格段设 w:ind firstLineChars=0 firstLine=0")
    elif body_ind:
        print("  [表格首行缩进] OK(单元格都已清零)")

    # 2) 标题居中
    centered_h = 0
    for p in re.findall(r"<w:p\b.*?</w:p>", doc, re.S):
        st = re.search(r'<w:pStyle w:val="(Heading\d|Title)"', p)
        if st and re.search(r'<w:jc w:val="center"', p):
            centered_h += 1
    if centered_h:
        problems += centered_h
        print(f"  [标题居中] {centered_h} 个标题居中 -> 章节标题应左对齐(jc=left)")

    # 3) 参考文献粗查
    if "参考文献" in doc or "References" in doc:
        tail = doc[doc.rfind("参考文献") if "参考文献" in doc else doc.rfind("References"):]
        if not re.search(r"\[\s*1\s*\]|^\s*1\.", tail, re.M):
            print("  [参考文献] 疑似没编号(没找到 [1]/1.) -> 确认文献列表编号且正文交叉引用得上")

    print("OK 排版无常见问题" if problems == 0 else f"共 {problems} 处排版问题")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
