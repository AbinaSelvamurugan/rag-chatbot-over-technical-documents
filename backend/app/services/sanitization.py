"""Defense-in-depth removal of obvious role spoofing in untrusted document excerpts.

This is not a proof against all injection. Original indexed evidence is preserved.
"""
import re

SUSPECT_LINES = re.compile(
    r'(?:ignore\s+(?:all\s+)?(?:previous|prior|system|developer)\s+instructions|'
    r'(?:system|developer)\s+(?:prompt|message)\s*:|'
    r'\[/?(?:system|developer|assistant)\]|'
    r'<\/?(?:system|developer|assistant)>|'
    r'(?:reveal|print|send|exfiltrate)\s+(?:the\s+)?(?:api\s+key|secret|credential|password)|'
    r'you\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|system|developer)\b)',
    flags=re.I,
)


def sanitize_excerpt(text: str) -> str:
    return '\n'.join('[Untrusted instruction-like line withheld]' if SUSPECT_LINES.search(line) else line
                     for line in text.split('\n'))
