"""Per-month versioned-run storage for the wizard.

Layout:
  data/recon/runs/
  └── <YYYY-MM>/
      ├── latest.json                 ← {"run_id": "...", "updated_at": "..."}
      └── runs/
          └── <YYYY-MM-DD_HHMMSS>/
              ├── raw.xlsx            ← copy of uploaded source
              ├── invoice.csv         ← canonical
              ├── payment.csv         ← canonical
              ├── sales.xml.gz        ← gzipped Tally Sales XML
              ├── journal.xml.gz      ← gzipped Tally Journal XML
              ├── bundle.zip          ← all of the above for one-click download
              └── run.json            ← totals, sha256s, operator, notes, status

Every endpoint that mutates state writes through this module so history is
preserved indefinitely.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


class RunStore:
    def __init__(self, base: Path):
        self.base = base
        self.base.mkdir(parents=True, exist_ok=True)

    # ---- paths ----
    def month_dir(self, month: str) -> Path:
        return self.base / month

    def runs_dir(self, month: str) -> Path:
        return self.month_dir(month) / "runs"

    def run_dir(self, month: str, run_id: str) -> Path:
        return self.runs_dir(month) / run_id

    def latest_marker(self, month: str) -> Path:
        return self.month_dir(month) / "latest.json"

    # ---- lifecycle ----
    def new_run(self, month: str, operator: str | None = None) -> tuple[str, Path]:
        run_id = _ts()
        rd = self.run_dir(month, run_id)
        rd.mkdir(parents=True, exist_ok=True)
        meta = {
            "run_id": run_id,
            "month": month,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "operator": operator or "anonymous",
            "status": "in_progress",
            "notes": "",
            "files": {},
            "totals": {},
        }
        self.write_meta(month, run_id, meta)
        return run_id, rd

    def read_meta(self, month: str, run_id: str) -> dict[str, Any]:
        p = self.run_dir(month, run_id) / "run.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def write_meta(self, month: str, run_id: str, meta: dict[str, Any]) -> None:
        rd = self.run_dir(month, run_id)
        (rd / "run.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def update_meta(self, month: str, run_id: str, **patch: Any) -> dict[str, Any]:
        meta = self.read_meta(month, run_id)
        # shallow merge with files/totals merged at one level deep
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(meta.get(k), dict):
                meta[k].update(v)
            else:
                meta[k] = v
        meta["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.write_meta(month, run_id, meta)
        return meta

    def mark_latest(self, month: str, run_id: str) -> None:
        self.latest_marker(month).write_text(
            json.dumps(
                {"run_id": run_id, "updated_at": datetime.now().isoformat(timespec="seconds")},
                indent=2,
            ),
            encoding="utf-8",
        )

    # ---- artifact placement ----
    def stash_raw(self, month: str, run_id: str, source: Path) -> dict[str, str]:
        """Copy uploaded xlsx into run; return file metadata."""
        rd = self.run_dir(month, run_id)
        dest = rd / "raw.xlsx"
        shutil.copy2(source, dest)
        info = {
            "path": str(dest),
            "name": source.name,
            "size": dest.stat().st_size,
            "sha256": _sha256(dest),
        }
        self.update_meta(month, run_id, files={"raw": info})
        return info

    def record_csv(self, month: str, run_id: str, kind: str, csv_path: Path) -> dict[str, str]:
        """csv_path is already written into the run dir by the CLI script. Just stat + hash."""
        info = {
            "path": str(csv_path),
            "size": csv_path.stat().st_size,
            "sha256": _sha256(csv_path),
        }
        self.update_meta(month, run_id, files={kind: info})
        return info

    def compress_xml(self, month: str, run_id: str, kind: str, xml_path: Path,
                     voucher_count: int) -> dict[str, str]:
        """Gzip the XML in-place (keep both .xml and .xml.gz for now)."""
        gz = xml_path.with_suffix(xml_path.suffix + ".gz")
        with xml_path.open("rb") as src, gzip.open(gz, "wb", compresslevel=9) as out:
            shutil.copyfileobj(src, out)
        info = {
            "path": str(xml_path),
            "gz_path": str(gz),
            "size": xml_path.stat().st_size,
            "gz_size": gz.stat().st_size,
            "sha256": _sha256(xml_path),
            "voucher_count": voucher_count,
        }
        self.update_meta(month, run_id, files={kind: info})
        return info

    def bundle_zip(self, month: str, run_id: str) -> Path:
        """Build bundle.zip containing all artifacts of the run."""
        rd = self.run_dir(month, run_id)
        bz = rd / "bundle.zip"
        with zipfile.ZipFile(bz, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in sorted(rd.iterdir()):
                if p.name in {"bundle.zip"}:
                    continue
                z.write(p, arcname=p.name)
        self.update_meta(month, run_id, files={"bundle": {
            "path": str(bz),
            "size": bz.stat().st_size,
        }})
        return bz

    def finalize(self, month: str, run_id: str, totals: dict[str, Any],
                 notes: str = "", status: str = "complete") -> dict[str, Any]:
        meta = self.update_meta(month, run_id, totals=totals, notes=notes, status=status)
        self.mark_latest(month, run_id)
        # Build bundle as last step
        self.bundle_zip(month, run_id)
        return meta

    # ---- listing ----
    def list_months(self) -> list[dict[str, Any]]:
        out = []
        for md in sorted(self.base.iterdir()):
            if not md.is_dir():
                continue
            latest = self.latest_marker(md.name)
            latest_id = None
            if latest.exists():
                try:
                    latest_id = json.loads(latest.read_text())["run_id"]
                except Exception:
                    latest_id = None
            run_ids = sorted(
                (p.name for p in self.runs_dir(md.name).iterdir() if p.is_dir()),
                reverse=True,
            ) if self.runs_dir(md.name).exists() else []
            out.append({
                "month": md.name,
                "latest_run_id": latest_id,
                "run_count": len(run_ids),
                "runs": run_ids[:20],
            })
        return out

    def list_runs(self, month: str) -> list[dict[str, Any]]:
        rd = self.runs_dir(month)
        if not rd.exists():
            return []
        out = []
        latest_id = None
        if self.latest_marker(month).exists():
            try:
                latest_id = json.loads(self.latest_marker(month).read_text())["run_id"]
            except Exception:
                pass
        for d in sorted((p for p in rd.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
            meta = self.read_meta(month, d.name)
            out.append({
                "run_id": d.name,
                "is_latest": d.name == latest_id,
                **{k: meta.get(k) for k in ("status", "operator", "created_at", "updated_at", "notes", "totals")},
            })
        return out
