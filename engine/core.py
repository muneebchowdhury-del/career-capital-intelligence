from __future__ import annotations
import hashlib, ipaddress, json, re, socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

MAX_BODY_BYTES = 5_000_000
SAFE_PATTERN_RE = re.compile(r"^[\w\s\-–—./:$%+()'&,.*]{1,180}$", re.UNICODE)
SOURCE_REGISTRY_FILES = ('sources.json', 'labor-sources.json')


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def deterministic_id(*parts: object, prefix: str = '') -> str:
    raw = '\x1f'.join('' if p is None else str(p) for p in parts)
    h = sha256_text(raw)[:24]
    return f"{prefix}{h}"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write('\n')
    tmp.replace(path)


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(canonical_json(record) + '\n')


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open('r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path}:{i}: {e}") from e


def load_source_registry(root: Path) -> list[dict]:
    root = Path(root)
    out = []
    seen = set()
    for name in SOURCE_REGISTRY_FILES:
        payload = load_json(root / 'config' / name, {}) or {}
        rows = payload.get('sources', [])
        if not isinstance(rows, list):
            raise ValueError(f'{name}: sources must be a list')
        for src in rows:
            if not isinstance(src, dict) or not src.get('id'):
                raise ValueError(f'{name}: invalid source entry')
            sid = src['id']
            if sid in seen:
                raise ValueError(f'duplicate source id across registries: {sid}')
            seen.add(sid)
            out.append(src)
    return out


def safe_pattern_match(pattern: str, text: str) -> bool:
    if not isinstance(pattern, str) or not SAFE_PATTERN_RE.fullmatch(pattern):
        raise ValueError(f"Unsafe/unsupported discovery pattern: {pattern!r}")
    remainder = pattern.replace('.*', '')
    if any(ch in remainder for ch in '[](){}+?|^$\\'):
        raise ValueError(f"Unsupported pattern metacharacter: {pattern!r}")
    parts = pattern.split('.*')
    pos = 0
    hay = text.casefold()
    for part in parts:
        if not part:
            continue
        needle = part.casefold()
        idx = hay.find(needle, pos)
        if idx < 0:
            return False
        pos = idx + len(needle)
    return True


def is_public_https_url(url: str, resolve_dns: bool = True) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme.lower() != 'https' or not p.hostname or p.username or p.password:
        return False
    host = p.hostname.rstrip('.').lower()
    if host in {'localhost', 'localhost.localdomain'} or host.endswith('.local'):
        return False
    try:
        literal = ipaddress.ip_address(host)
        return not (literal.is_private or literal.is_loopback or literal.is_link_local or literal.is_reserved or literal.is_multicast or literal.is_unspecified)
    except ValueError:
        pass
    if not resolve_dns:
        return True
    try:
        infos = socket.getaddrinfo(host, p.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return True


def validate_dashboard(db: dict) -> list[str]:
    errs = []
    if not isinstance(db, dict):
        return ['dashboard must be an object']
    nodes = db.get('nodes')
    sources = db.get('sources')
    if not isinstance(nodes, list) or not nodes:
        errs.append('nodes must be a non-empty list')
        nodes = []
    if not isinstance(sources, list) or not sources:
        errs.append('sources must be a non-empty list')
        sources = []
    source_ids = set()
    for s in sources:
        sid = s.get('id') if isinstance(s, dict) else None
        if not sid or sid in source_ids:
            errs.append(f'invalid/duplicate source id: {sid!r}')
        else:
            source_ids.add(sid)
        url = s.get('url') if isinstance(s, dict) else None
        if url and not is_public_https_url(url, resolve_dns=False):
            errs.append(f'unsafe source url for {sid}: {url}')
    node_ids = set()
    score_fields = ['capital','capitalQuality','momentum','durability','scarcity','income','aiResilience','businessValue','entrepreneurship','defensibility','accessibility','proofAccessibility','valueCapture','transferability','optionValue','hypeRisk','crowdingRisk']
    for n in nodes:
        if not isinstance(n, dict):
            errs.append('node must be object'); continue
        nid = n.get('id')
        if not nid or nid in node_ids:
            errs.append(f'invalid/duplicate node id: {nid!r}')
        else:
            node_ids.add(nid)
        sc = n.get('scores', n)
        for k in score_fields:
            if k in sc:
                v = sc[k]
                if not isinstance(v, (int,float)) or not 0 <= v <= 100:
                    errs.append(f'{nid}.{k} must be 0..100')
        for sid in n.get('sourceIds', n.get('sources', [])) or []:
            if isinstance(sid, str) and sid not in source_ids:
                errs.append(f'{nid} references unknown source {sid}')
    return errs
