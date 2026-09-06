#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; docs=ROOT/'docs'
html=(docs/'index.html').read_text(encoding='utf-8'); app=(docs/'app-core.js').read_text(encoding='utf-8'); boot=(docs/'bootstrap.js').read_text(encoding='utf-8')
files={}
for p in (docs/'data').rglob('*.json'):
    rel='./'+p.relative_to(docs).as_posix(); files[rel]=json.loads(p.read_text(encoding='utf-8'))
payload=json.dumps(files,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
html=html.replace('<script src="./app-core.js"></script>','<script>'+app.replace('</','<\\/')+'</script>')
html=html.replace('<script src="./bootstrap.js"></script>',f'<script>window.__STATIC_FILES={payload};</script><script>'+boot.replace('</','<\\/')+'</script>')
out=ROOT/'STANDALONE_PREVIEW.html'; out.write_text(html,encoding='utf-8'); print(out)
