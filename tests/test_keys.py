"""Smoke-test live LLM keys. Run: .venv/bin/python -m pytest tests/test_keys.py -s"""
from tmv_recon.llm import gemini, claude
from tmv_recon.config import GEMINI_MODEL, GEMINI_FLASH, CLAUDE_MODEL


def test_gemini_pro():
    out = gemini.text("Reply with the single word: PONG").strip()
    assert "PONG" in out.upper(), f"got {out!r}"


def test_gemini_flash():
    out = gemini.text("Reply with the single word: PONG", flash=True).strip()
    assert "PONG" in out.upper(), f"got {out!r}"


def test_claude():
    out = claude.text("Reply with the single word: PONG").strip()
    assert "PONG" in out.upper(), f"got {out!r}"


if __name__ == "__main__":
    print(f"[{GEMINI_MODEL}] {gemini.text('Reply with the single word: PONG').strip()}")
    print(f"[{GEMINI_FLASH}] {gemini.text('Reply with the single word: PONG', flash=True).strip()}")
    print(f"[{CLAUDE_MODEL}] {claude.text('Reply with the single word: PONG').strip()}")
