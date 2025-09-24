import json
import re
from dataclasses import dataclass
from typing import Iterable, List, Pattern


DEFAULT_SENSITIVE_PATTERNS = [
    r"\bAuthorization\b[:\-\s]*.*",
    r"\bAuth\b[:\-\s]*.*",
    r"\bBearer\b\s+[A-Za-z0-9\-\._~\+\/=]+",
    r"\bX\-API\-Key\b[:\-\s]*.*",
    r"\bAPI\s*Key\b[:\-\s]*.*",
    r"\bHost\b[:\-\s]*.*",
    r"\bCookie\b[:\-\s]*.*",
    r"\bSet\-Cookie\b[:\-\s]*.*",
    r"\bX\-Auth\-Token\b[:\-\s]*.*",
]


@dataclass
class PatternSet:
    patterns: List[Pattern]

    @classmethod
    def from_strings(cls, pats: Iterable[str]):
        return cls(patterns=[re.compile(p, flags=re.IGNORECASE) for p in pats])

    @classmethod
    def default(cls):
        return cls.from_strings(DEFAULT_SENSITIVE_PATTERNS)

    @classmethod
    def from_file(cls, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            pats = data.get('patterns', [])
        else:
            pats = data
        return cls.from_strings(pats)

    @classmethod
    def from_headers(cls, headers: Iterable[str], include_defaults: bool = False):
        pats: List[str] = []
        for h in headers:
            h = h.strip()
            if not h:
                continue
            # Escape header for regex and match the full line after header
            esc = re.escape(h)
            pats.append(rf"\b{esc}\b[:\-\s]*.*")
            # Special-case common sensitive variants
            if h.lower() in {"authorization", "auth"}:
                pats.append(r"\bBearer\b\s+[A-Za-z0-9\-\._~\+\/=]+")
        if include_defaults:
            pats.extend(DEFAULT_SENSITIVE_PATTERNS)
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for p in pats:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return cls.from_strings(deduped)

    @classmethod
    def from_headers_file(cls, path: str, include_defaults: bool = False):
        # Accept JSON array or simple newline-separated text
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
            # Try JSON first
            try:
                obj = json.loads(data)
                if isinstance(obj, dict):
                    headers = obj.get('headers', [])
                else:
                    headers = obj
                if not isinstance(headers, list):
                    headers = []
            except Exception:
                # Fallback: newline-separated
                headers = [line.strip() for line in data.splitlines() if line.strip()]
        except FileNotFoundError:
            headers = []
        return cls.from_headers(headers, include_defaults=include_defaults)

    def find_matches(self, text: str):
        matches = []
        for p in self.patterns:
            for m in p.finditer(text):
                matches.append((p, m.span()))
        return matches
