"""Company-level constants + tolerances.

Change these once; both Sales and Journal emitters pick them up.
"""
from __future__ import annotations

import uuid

# ----- Company identity (used in voucher headers and GUID seeds) -----
COMPANY = "THE MANGAL VIEW RESIDENCY"
CMP_GSTIN = "08AABCJ1528Q1Z8"
CMP_STATE = "Rajasthan"

# Seed namespace for deterministic uuid5() generation of <GUID>.
# Tied to The Mangal View Residency's real Tally GUID prefix so re-imports
# overwrite existing vouchers cleanly.
GUID_NAMESPACE = uuid.UUID("029dfefd-5996-4e71-8914-ec5a8528c655")

# ----- Tolerances -----
# Below this absolute rupee amount we skip emitting a ROUND OFF entry
# (treat as exactly balanced).
ROUND_OFF_TOLERANCE = 0.005
