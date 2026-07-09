"""Manual-review detection for hotel payment settlements — the ONE place this lives.

An invoice needs manual review when its settlements contain a reversal/refund
(e.g. an amount collected via one mode and partly refunded via another). Auto-booking
a refund voucher is error-prone, so the pipeline EXCLUDES such invoices from the
generated import XML and flags them with a plain-English treatment for the accountant
to enter in Tally.

Convention: payment 'Settlement Amount' is SIGNED — positive = collection (money in),
negative = refund/reversal (money out).
"""
from __future__ import annotations

from .primitives import ffloat


def invoice_review(invoice_no: str, rows: list[dict], billed: float) -> dict | None:
    """Return a review record if this invoice needs manual entry, else None.

    `rows` = the payment canonical CSV rows for this invoice.
    """
    legs = [((r.get("Settlement/Particular") or "").strip(), ffloat(r.get("Settlement Amount")))
            for r in rows]
    if not any(a < 0 for _, a in legs):
        return None  # all collections — safe to auto-book

    collected = round(sum(a for _, a in legs if a > 0), 2)
    refunded = round(-sum(a for _, a in legs if a < 0), 2)
    net = round(collected - refunded, 2)
    coll = ", ".join(f"{m} ₹{a:,.2f}" for m, a in legs if a > 0) or "—"
    refs = ", ".join(f"{m} ₹{-a:,.2f}" for m, a in legs if a < 0) or "—"
    treatment = (
        f"Collected {coll}; refunded {refs}. Net ₹{net:,.2f} settles the bill of ₹{billed:,.2f}. "
        f"In Tally: book the receipt(s) as usual, then the refund as a separate voucher "
        f"(Dr Sundry Debtors / Cr the refund mode) against this invoice."
    )
    return {
        "invoice": invoice_no,
        "billed": round(billed, 2),
        "collected": collected,
        "refunded": refunded,
        "net": net,
        "reason": "reversal / refund",
        "treatment": treatment,
        "legs": [{"mode": m, "amount": a} for m, a in legs],
    }


def find_manual_review(payment_rows: list[dict], total_payable_by_inv: dict[str, float]) -> list[dict]:
    """Group payment rows by invoice and return the review records that need manual entry."""
    by_inv: dict[str, list[dict]] = {}
    for r in payment_rows:
        by_inv.setdefault((r.get("Invoice #") or "").strip(), []).append(r)
    out = []
    for inv, rows in by_inv.items():
        rec = invoice_review(inv, rows, total_payable_by_inv.get(inv, 0.0))
        if rec:
            out.append(rec)
    out.sort(key=lambda x: -abs(x["refunded"]))
    return out
