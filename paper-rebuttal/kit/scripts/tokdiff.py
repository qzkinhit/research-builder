#!/usr/bin/env python3
"""usage: tokdiff.py BEFORE AFTER  Compares numbers, citations, references, macros and marks, and reports new banned punctuation."""
import re,sys,collections as C
a,b=[open(f,encoding='utf-8').read() for f in sys.argv[1:3]]
pats={'number':r'\d+(?:[.,]\d+)*','cite/ref/label':r'\\(?:cite[tp]?|ref|eqref|label)\{[^}]*\}','num macro':r'\\num\{[^}]*\}','rev macros':r'\\(?:rev|revcap|revred|revnote)\b','tags':r'\}\{[A-Za-z0-9]+-[WQS][A-Za-z0-9, \-]*\}','env':r'\\(?:begin|end)\{[^}]*\}'}
ok=True
for k,p in pats.items():
    x,y=C.Counter(re.findall(p,a)),C.Counter(re.findall(p,b))
    if x!=y: ok=False; print(k,'REMOVED',dict(list((x-y).items())[:12]),'ADDED',dict(list((y-x).items())[:12]))
for ch in ['——','—','–',';','；']:
    if b.count(ch)>a.count(ch): ok=False; print('new',repr(ch),b.count(ch)-a.count(ch))
print('tokens identical' if ok else 'TOKEN DIFFERENCES','| chars',len(a),'->',len(b))
