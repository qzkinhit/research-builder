#!/usr/bin/env python3
"""usage: sentcheck.py FILE...  Lists English sentences of 36 words or more and Chinese sentences of 85 characters or more."""
import re,sys
def clean(t):
    t=re.sub(r'(?m)(?<!\\)%.*$','',t)
    t=re.sub(r'\\begin\{(tabular|tabularx|equation|align|algorithm|algorithmic|rtable)\*?\}.*?\\end\{\1\*?\}',' ',t,flags=re.S)
    t=re.sub(r'\$[^$]*\$','X',t); t=re.sub(r'\\(?:cite[tp]?|ref|label|eqref)\{[^}]*\}','R',t)
    t=re.sub(r'\\num\{[^}]*\}','0',t); t=re.sub(r'\}\{(?:[A-Za-z]+-[A-Za-z0-9]+(?:, *)?)+\}',' ',t)
    t=re.sub(r'\\textbf\{([^}]*)\}',r' \1. ',t)
    t=re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?','',t); return re.sub(r'[{}~\\]',' ',t)
def cjk(s): return len(re.findall(r'[\u4e00-\u9fff]',s))
total=0
for f in sys.argv[1:]:
    raw=open(f,encoding='utf-8').read()
    for para in re.split(r'\n\s*\n',clean(raw)):
        para=re.sub(r'\s+',' ',para).strip()
        if not para: continue
        if cjk(para)>len(para)*0.2:
            for s in re.split(r'(?<=[。！？])',para):
                if cjk(s)>=85: total+=1; print(f'ZH {cjk(s)} | {s.strip()[:140]}')
        else:
            q=re.sub(r'\b(e\.g|i\.e|et al|Ref|vs|Fig|Eq|Sec|Tab|cf)\.',r'\1<D>',para); q=re.sub(r'(\d)\.(\d)',r'\1<D>\2',q)
            for s in re.split(r'(?<=[.?!])\s+(?=[A-Z(])',q):
                n=len(s.split())
                if n>=36: total+=1; print(f'EN {n} | {s.replace("<D>",".")[:140]}')
print('flagged',total)
