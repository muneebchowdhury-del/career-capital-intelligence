from __future__ import annotations
from html.parser import HTMLParser
from urllib.parse import urljoin
import re

_IGNORE = {'script','style','noscript','svg','canvas','nav','header','footer','form'}
_WS = re.compile(r'\s+')

class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.depth=0; self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower() in _IGNORE: self.depth += 1
    def handle_endtag(self, tag):
        if tag.lower() in _IGNORE and self.depth: self.depth -= 1
    def handle_data(self, data):
        if self.depth == 0:
            x=_WS.sub(' ',data).strip()
            if x: self.parts.append(x)

def meaningful_text(html: str) -> str:
    p=VisibleTextParser(); p.feed(html); return _WS.sub(' ',' '.join(p.parts)).strip()

class LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True); self.base=base_url; self.links=[]; self.current=None
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='a':
            href=dict(attrs).get('href')
            if href: self.current=[urljoin(self.base,href),[]]
    def handle_data(self,data):
        if self.current is not None: self.current[1].append(data)
    def handle_endtag(self,tag):
        if tag.lower()=='a' and self.current is not None:
            url,parts=self.current; text=_WS.sub(' ',' '.join(parts)).strip(); self.links.append({'url':url,'text':text}); self.current=None

def extract_links(html: str, base_url: str):
    p=LinkParser(base_url); p.feed(html); seen=set(); out=[]
    for x in p.links:
        key=(x['url'],x['text'])
        if key not in seen: seen.add(key); out.append(x)
    return out
