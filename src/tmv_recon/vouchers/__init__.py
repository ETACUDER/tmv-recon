"""Verbose Tally voucher generation package.

Single source of truth for:
  * config.py        — company, GSTIN, GUID seed, tolerances
  * ledgers.py       — all string ledger names + mode/rate mappings
  * ezee_columns.py  — EZee Transaction Detail Report column names
  * flags.py         — voucher/ledger flag sets + empty container lists
  * primitives.py    — XML rendering primitives (no business logic)
  * sales.py         — render_sales_voucher(record) -> str
  * journal.py       — render_journal_voucher(...) -> str

Scripts in `scripts/` orchestrate I/O and call into this package.
"""

from . import config, ledgers, ezee_columns, flags, primitives, sales, journal

__all__ = ["config", "ledgers", "ezee_columns", "flags", "primitives", "sales", "journal"]
