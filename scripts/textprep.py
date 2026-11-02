"""Text preparation shared by the dispatcher and the engine runners (stdlib only).

clean(): turns markdown / terminal output into speakable prose.
chunk(): splits long text into sentence-aligned pieces an engine can take in one call.
"""
import re

_CODE_FENCE = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL = re.compile(r"https?://\S+")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.M)
_EMPH = re.compile(r"(\*\*|__|\*|_|~~)(?=\S)(.+?)(?<=\S)\1")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}.*$", re.M)
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def clean(text: str) -> str:
    t = _ANSI.sub("", text)
    t = _CODE_FENCE.sub(" (code block omitted) ", t)
    t = _INLINE_CODE.sub(r"\1", t)
    t = _LINK.sub(r"\1", t)
    t = _URL.sub("link", t)
    t = _TABLE_RULE.sub("", t)
    t = t.replace("|", ", ")
    t = _HEADING.sub("", t)
    t = _BULLET.sub("", t)
    t = _EMPH.sub(r"\2", t)
    # A line without terminal punctuation is a heading or list item: end it so the
    # engine pauses instead of running it into the next line.
    lines = []
    for line in t.splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if s[-1] not in ".!?:;,":
            s += "."
        lines.append(s)
    t = "\n".join(lines)
    t = re.sub(r"\n{2,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


_SENT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def chunk(text: str, max_chars: int = 300) -> list[str]:
    """Sentence-aligned chunks no longer than max_chars (a single overlong
    sentence is split at commas, then hard-wrapped)."""
    out, cur = [], ""
    for sent in (s.strip() for s in _SENT.split(text)):
        if not sent:
            continue
        pieces = [sent]
        if len(sent) > max_chars:
            pieces = re.split(r"(?<=[,;:])\s+", sent)
        for p in pieces:
            while len(p) > max_chars:
                cut = p.rfind(" ", 0, max_chars)
                cut = cut if cut > 0 else max_chars
                if cur:
                    out.append(cur)
                    cur = ""
                out.append(p[:cut].strip())
                p = p[cut:].strip()
            if cur and len(cur) + 1 + len(p) > max_chars:
                out.append(cur)
                cur = p
            else:
                cur = f"{cur} {p}".strip()
    if cur:
        out.append(cur)
    return out
