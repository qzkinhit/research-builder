# Third-party notices

## humanizer

`writing-deai.md` is adapted from [blader/humanizer](https://github.com/blader/humanizer), version 3.1.0. The
adaptation keeps its account of why AI text reads as AI text, its strength rule, its rewrite workflow and the
numbering of its patterns 1 to 26, replaces the examples with academic Chinese and English prose, tightens several
patterns to the hard rules of this skill, and adds patterns 27 to 32. The detectors in `tools/polish_check.py` and
`tools/audit_tex.py` implement some of these patterns. humanizer's patterns are based on Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI
Cleanup.

```
MIT License

Copyright (c) 2025 Siqi Chen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## TIME benchmark paper

`knowledge/benchmark-papers.md` describes the narrative of the TIME paper (arXiv:2602.12147) and links to it. No
part of that paper is redistributed here. Fetch it with `paper-survey/tools/fetch_arxiv.sh`.
