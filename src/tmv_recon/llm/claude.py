"""Claude (Sonnet 4.6) client. PDF as base64 document block."""
from __future__ import annotations
import base64
from pathlib import Path
import anthropic

from tmv_recon.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def text(prompt: str, *, model: str | None = None, max_tokens: int = 4096) -> str:
    r = _client.messages.create(
        model=model or CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in r.content if b.type == "text")


def pdf(pdf_path: str | Path, prompt: str, *, model: str | None = None, max_tokens: int = 4096) -> str:
    data = base64.standard_b64encode(Path(pdf_path).read_bytes()).decode()
    r = _client.messages.create(
        model=model or CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return "".join(b.text for b in r.content if b.type == "text")
