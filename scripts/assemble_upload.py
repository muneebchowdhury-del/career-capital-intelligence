#!/usr/bin/env python3
from __future__ import annotations
import hashlib, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=ROOT/'upload_parts'
TARGETS={
 'data/recommendation_latest.json':(['recommendation.00.part','recommendation.01.part','recommendation.02.part','recommendation.03.part','recommendation.04.part','recommendation.05.part'],'765087c795e1dbe5ad1a94aa58b8c9ade9c334539bd8440847a02396d1a64e9c'),
 'docs/app-core.js':(['app.00.part','app.01.part'],'afab8abbb0a81cf9a119b924c9dafc422f32e26fe8dddd5b63dffb8d31b8d84e'),
 'docs/index.html':(['index.00.part','index.01.part'],'56f2216525a560023df19719e950592fbc162dec10ce19467082f795314cb6b8'),
 'docs/bootstrap.js':(['bootstrap.00.part'],'1e3fab749332e668a05c5fc1879c2a50a5141fe35a7859ea39ce049f58d44dc9'),
 'config/sources.json':(['sources.00.part','sources.01.part'],'bc06f647f401e2d90bc152a27b462e9065ae0ba9139054037f0dcee709372284'),
}
for target,(names,expected) in TARGETS.items():
    chunks=[(PARTS/n).read_bytes() for n in names]
    # The first HTML upload included a duplicated continuation after the known
    # 12 KB split marker. Cut at the original split boundary; the unchanged
    # expected SHA-256 below still proves the reconstructed file is exact.
    if target=='docs/index.html':
        marker=b'<select id="xMetric"></'
        pos=chunks[0].find(marker)
        if pos<0: raise SystemExit('HTML split marker not found')
        chunks[0]=chunks[0][:pos+len(marker)]
    data=b''.join(chunks)
    got=hashlib.sha256(data).hexdigest()
    print(f'{target}: {got}')
    if got!=expected: raise SystemExit(f'hash mismatch for {target}: expected {expected}, got {got}')
    out=ROOT/target;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
(ROOT/'docs/.nojekyll').write_text('',encoding='utf-8')
# Remove abandoned archive bootstrap and transparent upload staging files.
for p in [ROOT/'project.tar.gz',ROOT/'.github/workflows/bootstrap.yml']:
    if p.exists(): p.unlink()
if PARTS.exists(): shutil.rmtree(PARTS)
# Remove this one-time mechanism from the clean project after it has done its job.
for p in [ROOT/'.github/workflows/assemble-staging.yml',ROOT/'scripts/assemble_upload.py']:
    if p.exists(): p.unlink()
print('Assembly and hash verification complete.')
