"""EZee Transaction Detail Report column names referenced across the pipeline.

If the EZee export schema changes, edit these constants once.
"""
from __future__ import annotations

# ----- Identity / dates -----
INVOICE_NO = "Invoice #"
INVOICE_DATE = "Invoice date"
TRANSACTION_DATE = "Transaction Date"
ARRIVAL = "Arrival"
DEPARTURE = "Dept."
GUEST_NAME = "Guest Name"
ROOM_TYPE = "Room Type"
TRAVEL_AGENT = "Travel Agent"
BUSINESS_SOURCE = "Business Source"
TRANSACTION_TYPE = "Transaction Type"
TRANSACTION = "Transaction"

# ----- Money columns -----
NET_AMOUNT = "Net Amount"
TAX_AMOUNT_CGST = "Tax Amount"
TAX_AMOUNT_SGST = "Tax Amount.1"
GROSS_AMOUNT = "Gross Amount"
DISCOUNT_AMOUNT = "Discount Amount"
ADJUSTMENT = "Adjustment(Room Charge/Extra Charges)"
SETTLEMENT_AMOUNT = "Settlement Amount"
SETTLEMENT_MODE = "Settlement/Particular"
REFERENCE_NO = "Reference #"
