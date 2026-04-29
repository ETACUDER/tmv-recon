"""Gemini client. PDF inline (<18MB) or Files API (large)."""
from __future__ import annotations
from pathlib import Path
from google import genai
from google.genai import types as gtypes

from tmv_recon.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FLASH

_client = genai.Client(api_key=GEMINI_API_KEY)


def _model(model: str | None, flash: bool) -> str:
    return model or (GEMINI_FLASH if flash else GEMINI_MODEL)


def text(prompt: str, *, model: str | None = None, flash: bool = False) -> str:
    r = _client.models.generate_content(model=_model(model, flash), contents=prompt)
    return r.text or ""


def pdf(pdf_path: str | Path, prompt: str, *, model: str | None = None, flash: bool = False) -> str:
    p = Path(pdf_path)
    data = p.read_bytes()
    m = _model(model, flash)
    if len(data) < 18 * 1024 * 1024:
        part = gtypes.Part.from_bytes(data=data, mime_type="application/pdf")
        r = _client.models.generate_content(model=m, contents=[part, prompt])
    else:
        f = _client.files.upload(file=str(p), config={"mime_type": "application/pdf"})
        r = _client.models.generate_content(model=m, contents=[f, prompt])
    return r.text or ""
