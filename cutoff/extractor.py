"""Turn changelog text into structured migration rules.

Backends: Claude (default) or the fine-tuned model served locally (CUTOFF_EXTRACTOR=local, later).
Every rule must carry a quote that appears verbatim in the source text, or it is dropped.
"""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor

import anthropic

from . import config

KINDS = ["renamed", "removed", "signature_changed", "behavior_changed", "moved", "default_changed", "dependency_dropped"]
NULLABLE = {"anyOf": [{"type": "string"}, {"type": "null"}]}
RULE_SCHEMA = {
    "type": "object",
    "properties": {"rules": {"type": "array", "items": {
        "type": "object",
        "properties": {"kind": {"type": "string", "enum": KINDS}, "symbol": {"type": "string"},
                       "replacement": NULLABLE, "before": NULLABLE, "after": NULLABLE,
                       "note": {"type": "string"}, "source_quote": {"type": "string"}},
        "required": ["kind", "symbol", "replacement", "before", "after", "note", "source_quote"],
        "additionalProperties": False}}},
    "required": ["rules"], "additionalProperties": False,
}

# Identical to the instruction the fine-tuned model was trained on (scripts/build_dataset.py).
TASK = """Extract migration rules from a library changelog excerpt.

A migration rule is a change that can break code which uses the library: something renamed, removed, moved,
given a new signature, a changed default, changed behavior that callers rely on, or a dropped Python/dependency
version. Ignore new features, bug fixes, performance work, docs and internal changes, unless they remove or
replace something callers use.

For each rule return:
- kind: one of renamed | removed | signature_changed | behavior_changed | moved | default_changed | dependency_dropped
- symbol: the affected public name (e.g. "pkg.module.func", "Class.method", "--cli-flag", "Python 3.9")
- replacement: what to use instead, or null if there is none
- before / after: a minimal code example of the old and new usage, or null when the excerpt gives too little to write one
- note: one sentence on what changed and how it breaks callers
- source_quote: a short span copied EXACTLY, character for character, from the excerpt that supports the rule

Only use information in the excerpt. Do not invent symbols or versions. If nothing in the excerpt can break
callers, return {"rules": []}.
Answer with JSON only: {"rules": [...]}"""

# Extra guidance for the Claude backend only; the fine-tuned model was trained on TASK alone.
QUOTE_HINT = """

Make each source_quote the whole sentence or bullet that states the change (usually 8 to 40 words), so that a
reviewer reading only the quote can see what changed. Never quote a bare symbol name."""

BREAKING = re.compile(r"breaking|deprecat|removed|remove |renamed|rename |no longer|replaced|expired|"
                      r"migration|incompatible|api change|instead", re.I)
CHUNK = 3500
MAX_CHUNKS = 12
KEYWORD_CHUNKS = 10


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def chunk(text: str) -> list[str]:
    parts, chunks, cur = re.split(r"\n(?=#{1,4} )", text), [], ""
    for part in parts:
        for line in ([part] if len(part) <= CHUNK else part.split("\n")):
            if len(cur) + len(line) > CHUNK and cur:
                chunks.append(cur)
                cur = ""
            cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks


def pick_chunks(text: str, keywords: list[str]) -> list[str]:
    """Rank chunks: ones naming a keyword first, then ones that talk about breaking changes."""
    kws = [k.lower() for k in keywords if k]
    scored = []
    for i, c in enumerate(chunk(text)):
        low = c.lower()
        score = 10 * sum(k in low for k in kws) + len(BREAKING.findall(c))
        if score:
            scored.append((score, i, c))
    scored.sort(key=lambda t: (-t[0], t[1]))
    named = [t for t in scored if t[0] >= 10]  # chunks that mention a keyword
    if named:  # verification asks about specific symbols: read only the sections that name them
        return [c for _, _, c in named[:KEYWORD_CHUNKS]]
    return [c for _, _, c in scored[:MAX_CHUNKS]]


class Extractor:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.cost = 0.0
        self.name = f"claude:{config.EXTRACTOR_MODEL}"

    def _one(self, package: str, upgrade: str, excerpt: str) -> list[dict]:
        msg = self.client.messages.create(
            model=config.EXTRACTOR_MODEL, max_tokens=6000, system=TASK + QUOTE_HINT,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": RULE_SCHEMA}},
            messages=[{"role": "user", "content":
                       f"Package: {package}\nUpgrade: {upgrade}\n\nChangelog excerpt:\n{excerpt}"}],
        )
        self.cost += config.cost(config.EXTRACTOR_MODEL, msg.usage)
        if msg.stop_reason != "end_turn":
            return []
        try:
            rules = json.loads(next(b.text for b in msg.content if b.type == "text"))["rules"]
        except (StopIteration, json.JSONDecodeError, KeyError):
            return []
        ex = norm(excerpt)
        return [r for r in rules if len(norm(r["source_quote"]).split()) >= 4 and norm(r["source_quote"]) in ex]

    def extract(self, text: str, package: str, upgrade: str, source_url: str, keywords: list[str]) -> list[dict]:
        chunks = pick_chunks(text, keywords)
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda c: self._one(package, upgrade, c), chunks))
        out, seen = [], set()
        for rules in results:
            for r in rules:
                key = (r["kind"], r["symbol"])
                if key in seen:
                    continue
                seen.add(key)
                rid = "R-" + hashlib.sha1(f"{package}|{source_url}|{r['symbol']}|{r['kind']}".encode()).hexdigest()[:8]
                out.append({"rule_id": rid, "package": package, "from_version": upgrade.split(" -> ")[0],
                            "to_version": upgrade.split(" -> ")[-1], **r, "source_url": source_url,
                            "extractor": self.name})
        return out
