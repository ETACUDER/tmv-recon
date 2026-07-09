"""TMV Rooftop Restaurant pipeline (GST Composition dealer).

Source: Paytm gateway settlement report + Indian Bank statement (monthly xlsx).
Output: Tally Receipt + Payment vouchers (UTF-16 LE+BOM), import into the
"TMV Rooftop Restaurant" company. No output GST, no bill-wise allocation.
"""
from .pipeline import (  # noqa: F401
    generate, parse_sales_detail, parse_settlement_daily, parse_bank_statement,
)
