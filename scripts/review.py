#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.store import FileStore

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('review_id'); ap.add_argument('decision',choices=['validated','published','rejected','duplicate','superseded']); ap.add_argument('--note',default='')
    a=ap.parse_args(); FileStore(ROOT).resolve_review(a.review_id,a.decision,a.note); print(f'{a.review_id}: {a.decision}')
if __name__=='__main__': main()
