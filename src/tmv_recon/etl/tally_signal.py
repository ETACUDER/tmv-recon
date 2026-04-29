"""Cross-match canonical recon results against `data/tally/raw/`.

The tally bucket holds files Urvashi has handed off to her accountant for
posting into Tally. Discovery confirmed it has no actual journal-voucher
export — just the same data files re-bundled. So the **signal** here is
*presence/absence*: a canonical row whose source file has a byte-identical
peer in `data/tally/raw/` is already booked; otherwise it's pending.

Outputs:
  data/recon/reports/tally_signal.csv      one row per canonical file with status
  data/recon/reports/pending_tally.csv     rows from canonical that still need entry
  data/recon/reports/tally_status.txt      human-readable summary
"""
from __future__ import annotations
import hashlib
import re
import sys
from pathlib import Path
import pandas as pd

from tmv_recon.config import ROOT

CANON_DIR  = ROOT / "data" / "recon" / "canonical"
REPORT_DIR = ROOT / "data" / "recon" / "reports"
TALLY_DIR  = ROOT / "data" / "tally" / "raw"

MONTH_RE = re.compile(
    r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEPT?|OCT|NOV|DEC)[\s\-,]+(20\d{2})",
    re.I,
)


def _md5(p: Path) -> str:
    return hashlib.md5(p.resolve().read_bytes()).hexdigest()


def _peer_index() -> dict[str, Path]:
    """Map file content hash → tally peer path. Followed symlinks."""
    out = {}
    for p in TALLY_DIR.iterdir():
        if not p.is_file():
            continue
        try:
            out[_md5(p)] = p
        except OSError:
            continue
    return out


def _month_key(name: str) -> str:
    m = MONTH_RE.search(name)
    if not m: return ""
    mon = m.group(1).upper()
    if mon == "SEPT": mon = "SEP"
    return f"{mon} {m.group(2)}"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if not TALLY_DIR.exists():
        print(f"no tally bucket at {TALLY_DIR}")
        return 1

    # 1. Build hash → tally peer index
    tally_hashes = _peer_index()
    print(f"tally/raw: {len(tally_hashes)} files indexed by hash")

    # 2. For each file referenced by a canonical CSV, mark in_tally / pending
    rows: list[dict] = []
    for canon_name in ("invoice", "booking", "payment", "bank"):
        p = CANON_DIR / f"{canon_name}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if "raw_path" not in df.columns:
            continue
        for src_rel, n in df["raw_path"].value_counts().items():
            src = ROOT / src_rel
            if not src.exists():
                continue
            try: h = _md5(src)
            except OSError: continue
            in_tally = h in tally_hashes
            rows.append({
                "stream": canon_name,
                "source_file": Path(src_rel).name,
                "source_path": src_rel,
                "month": _month_key(Path(src_rel).name),
                "row_count": int(n),
                "in_tally": in_tally,
                "tally_peer": tally_hashes[h].name if in_tally else "",
            })

    sig = pd.DataFrame(rows)
    sig_csv = REPORT_DIR / "tally_signal.csv"
    sig.to_csv(sig_csv, index=False)

    # 3. Per-stream + per-month rollup
    print(f"\n{'stream':<12} {'in_tally_rows':>14}  {'pending_rows':>14}  files (in/total)")
    print("─" * 70)
    for stream, g in sig.groupby("stream"):
        in_n = g.loc[g["in_tally"], "row_count"].sum()
        pend = g.loc[~g["in_tally"], "row_count"].sum()
        files_in = g["in_tally"].sum()
        print(f"{stream:<12} {in_n:>14,}  {pend:>14,}  {files_in}/{len(g)}")

    # 4. Pending-by-month detail
    print(f"\n{'stream':<12} {'month':<12} {'pending_rows':>14}")
    print("─" * 50)
    pend_by_month = (
        sig[~sig["in_tally"]]
        .groupby(["stream", "month"])["row_count"]
        .sum()
        .reset_index()
        .sort_values(["stream", "month"])
    )
    for _, r in pend_by_month.iterrows():
        if r["row_count"]:
            print(f"{r['stream']:<12} {(r['month'] or '(no-month-in-name)'):<12} {r['row_count']:>14,}")

    # 5. Build a per-row pending CSV by joining canonical with the file-level signal
    pending_files = set(sig.loc[~sig["in_tally"], "source_path"])
    pending_rows: list[pd.DataFrame] = []
    for canon_name in ("invoice", "booking", "payment", "bank"):
        p = CANON_DIR / f"{canon_name}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if "raw_path" not in df.columns:
            continue
        sub = df[df["raw_path"].isin(pending_files)].copy()
        sub.insert(0, "stream", canon_name)
        pending_rows.append(sub)
    pending_df = pd.concat(pending_rows, ignore_index=True) if pending_rows else pd.DataFrame()
    pending_csv = REPORT_DIR / "pending_tally.csv"
    pending_df.to_csv(pending_csv, index=False)

    # 6. Status summary
    total_rows = sig["row_count"].sum()
    in_rows = sig.loc[sig["in_tally"], "row_count"].sum()
    pct = 100 * in_rows / max(1, total_rows)

    summary = (
        f"# Tally entry status\n\n"
        f"  files in tally bucket:     {len(tally_hashes)}\n"
        f"  canonical files booked:    {sig['in_tally'].sum()} of {len(sig)}\n"
        f"  canonical rows booked:     {in_rows:,} of {total_rows:,} ({pct:.1f}%)\n"
        f"  rows pending Tally entry:  {total_rows - in_rows:,}\n\n"
        f"Per-stream:\n"
    )
    for stream, g in sig.groupby("stream"):
        in_n = g.loc[g["in_tally"], "row_count"].sum()
        pend = g.loc[~g["in_tally"], "row_count"].sum()
        summary += f"  {stream:<10} booked {in_n:>6,}  pending {pend:>6,}\n"

    pend_str = "\nPending months (rows still to enter into Tally):\n"
    for _, r in pend_by_month.iterrows():
        if r["row_count"]:
            pend_str += f"  {r['stream']:<10} {(r['month'] or '(unknown)'):<12} {r['row_count']:>6,}\n"
    summary += pend_str

    summary += (
        f"\nOutputs:\n"
        f"  {sig_csv.relative_to(ROOT)}      file-level booked/pending status\n"
        f"  {pending_csv.relative_to(ROOT)}   row-level pending entries\n"
    )
    (REPORT_DIR / "tally_status.txt").write_text(summary)
    print("\n" + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
