// Render the exported OpenReview Markdown with markdown-it (CommonMark plus GFM tables, no math plugin), the
// way a site that runs Markdown before TeX would, and check that
//   (a) every table has the same number of cells in each row,
//   (b) every $...$ and $$...$$ span survives the Markdown pass unchanged,
//   (c) every span compiles in KaTeX,
//   (d) no LaTeX command is left outside math and no ** survives as literal text.
// Optional and needs node. Usage: NM=/path/to/node_modules node tools/render_check.js openreview/*.md
const path = require('path');
const fs = require('fs');
const NM = process.env.NM;
if (!NM) { console.error('set NM to a node_modules directory that holds markdown-it and katex'); process.exit(2); }
const MarkdownIt = require(path.join(NM, 'markdown-it'));
const katex = require(path.join(NM, 'katex'));
const md = new MarkdownIt('default', { html: false, linkify: false, typographer: false });

function unescapeHtml(s) {
  return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
}

function mathSpans(text) {
  // split into math spans, a backslash-escaped \$ is not a delimiter
  const spans = [];
  let i = 0;
  while (i < text.length) {
    if (text[i] === '\\' && text[i + 1] === '$') { i += 2; continue; }
    if (text.startsWith('$$', i)) {
      const j = text.indexOf('$$', i + 2);
      if (j < 0) { spans.push({ err: 'unclosed $$ at ' + i }); return spans; }
      spans.push({ s: i, e: j + 2, body: text.slice(i + 2, j), display: true });
      i = j + 2;
      continue;
    }
    if (text[i] === '$') {
      let j = i + 1;
      while (j < text.length && text[j] !== '$') { j += text[j] === '\\' ? 2 : 1; }
      if (j >= text.length) { spans.push({ err: 'unclosed $ at ' + i + ': ' + text.slice(i, i + 60) }); return spans; }
      spans.push({ s: i, e: j + 1, body: text.slice(i + 1, j), display: false });
      i = j + 1;
      continue;
    }
    i++;
  }
  return spans;
}

function braceBalance(s) {
  let d = 0;
  for (let i = 0; i < s.length; i++) {
    if (s[i] === '\\') { i++; continue; }
    if (s[i] === '{') d++;
    if (s[i] === '}') { d--; if (d < 0) return false; }
  }
  return d === 0;
}

const files = process.argv.slice(2);
let problems = 0;
for (const f of files) {
  const raw = fs.readFileSync(f, 'utf8');
  const name = path.basename(f);
  const html = md.render(raw);
  const plainHtml = unescapeHtml(html);
  // (a) tables
  const tokens = md.parse(raw, {});
  let rowCells = 0, counts = [], tableNo = 0;
  for (const t of tokens) {
    if (t.type === 'table_open') { counts = []; tableNo++; }
    if (t.type === 'tr_open') rowCells = 0;
    if (t.type === 'th_open' || t.type === 'td_open') rowCells++;
    if (t.type === 'tr_close') counts.push(rowCells);
    if (t.type === 'table_close') {
      const uniq = [...new Set(counts)];
      console.log(`${name}: table ${tableNo} rows=${counts.length} cells/row=${uniq.join(',')}`);
      if (uniq.length !== 1) { problems++; console.log('  PROBLEM inconsistent cells'); }
    }
  }
  // (b), (c) math
  const spans = mathSpans(raw);
  let nspan = 0;
  for (const sp of spans) {
    if (sp.err) { problems++; console.log(`  PROBLEM ${name}: ${sp.err}`); continue; }
    nspan++;
    const src = raw.slice(sp.s, sp.e);
    if (!plainHtml.includes(src)) { problems++; console.log(`  PROBLEM ${name}: math altered by Markdown: ${src}`); }
    if (!braceBalance(sp.body)) { problems++; console.log(`  PROBLEM ${name}: unbalanced braces: ${src}`); }
    try { katex.renderToString(sp.body, { throwOnError: true, strict: 'error', displayMode: sp.display }); }
    catch (e) { problems++; console.log(`  PROBLEM ${name}: KaTeX error in ${src}: ${e.message}`); }
  }
  // (d) outside math
  let outside = '';
  let last = 0;
  for (const sp of spans) { if (sp.err) continue; outside += raw.slice(last, sp.s) + ' '; last = sp.e; }
  outside += raw.slice(last);
  const cmds = outside.match(/\\[A-Za-z]+/g);
  if (cmds) { problems++; console.log(`  PROBLEM ${name}: LaTeX outside math: ${[...new Set(cmds)].join(' ')}`); }
  if (/\*\*/.test(html.replace(/<code>[\s\S]*?<\/code>/g, ''))) { problems++; console.log(`  PROBLEM ${name}: literal ** left in the rendered text`); }
  const em = (html.match(/<em>/g) || []).length, strong = (html.match(/<strong>/g) || []).length;
  console.log(`${name}: ${nspan} math spans, <em> ${em}, <strong> ${strong}, chars ${raw.replace(/\n$/, '').length}`);
}
console.log('TOTAL PROBLEMS', problems);
process.exit(problems ? 1 : 0);
