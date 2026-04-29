"""Canonical fact-table schemas. All amounts in INR.
Refine field set as discovery agents report — see _discovery_*.md.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Booking:
    """One row per OTA reservation (fct_booking)."""
    booking_id: str
    source: str                          # "agoda" | "gomt" | "walkin"
    guest_name: str = ""
    booking_date: date | None = None
    arrival_date: date | None = None
    departure_date: date | None = None
    nights: int = 0
    rate_per_night: Decimal | None = None
    gross_amount: Decimal | None = None
    commission: Decimal | None = None
    commission_gst: Decimal | None = None
    tcs: Decimal | None = None
    tds: Decimal | None = None
    net_settled: Decimal | None = None
    settlement_date: date | None = None
    settlement_utr: str = ""
    invoice_no: str = ""                 # linked EZ invoice if known
    credit_note_for: str = ""            # booking_id of original (rate-change CN)
    raw_path: str = ""                   # source file for traceback


@dataclass
class Invoice:
    """One row per invoice (fct_invoice). Folio detail in line_items."""
    invoice_no: str                      # normalized 25-26/####
    invoice_date: date | None = None
    folio_nos: list[str] = field(default_factory=list)
    reservation_no: str = ""
    guest_name: str = ""
    travel_agent: str = ""               # "Booking.com" | "Agoda" | "Walk-in"
    arrival_date: date | None = None
    departure_date: date | None = None
    nights: int = 0
    room_type: str = ""
    rate_type: str = ""
    room_no: str = ""
    net_amount: Decimal | None = None
    cgst: Decimal | None = None
    sgst: Decimal | None = None
    gst_rate: Decimal | None = None      # e.g. 5.0
    gross_amount: Decimal | None = None
    settlement_amount: Decimal | None = None
    settlement_mode: str = ""            # "Cash" | "Card" | "Credit" | "OTA"
    raw_path: str = ""


@dataclass
class Payment:
    """One row per settlement leg (fct_payment)."""
    payment_id: str
    source: str                          # "ptm" | "bank" | "receipt_pdf"
    unit: str = ""                       # "front_office" | "rooftop" | "f&b"
    txn_date: date | None = None
    settled_date: date | None = None
    gross_amount: Decimal | None = None
    commission: Decimal | None = None
    commission_gst: Decimal | None = None
    settled_amount: Decimal | None = None
    utr: str = ""
    payment_mode: str = ""               # CREDIT_CARD | UPI | CASH | TPP
    issuing_bank: str = ""
    customer_vpa: str = ""
    invoice_no: str = ""                 # if derivable from raw row
    matched_invoice_no: str = ""         # filled by matcher
    raw_path: str = ""


@dataclass
class Match:
    """A matcher decision linking a payment to an invoice (or marking unmatched)."""
    payment_id: str
    invoice_no: str | None
    confidence: float                    # 0.0 - 1.0
    rule: str                            # which rule fired (utr_exact, amount_date_window, etc.)
    residual: Decimal = Decimal(0)       # diff between payment net and invoice gross
    notes: str = ""
