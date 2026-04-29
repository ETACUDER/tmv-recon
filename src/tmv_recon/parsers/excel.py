"""Excel readers. .xlsx via openpyxl, .xls via xlrd."""
from __future__ import annotations
from pathlib import Path
import pandas as pd


def _engine(p: Path) -> str | None:
    s = p.suffix.lower()
    if s == ".xlsx":
        return "openpyxl"
    if s == ".xls":
        return "xlrd"
    return None


def sheets(path: str | Path) -> dict[str, pd.DataFrame]:
    p = Path(path)
    return pd.read_excel(p, sheet_name=None, engine=_engine(p))


def sheet(path: str | Path, name: str | int = 0) -> pd.DataFrame:
    p = Path(path)
    return pd.read_excel(p, sheet_name=name, engine=_engine(p))
