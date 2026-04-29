"""ETL pipeline: bucket → extract → canonical → recon → reports.

Buckets (under data/):
  booking/{raw,processed}/   OTA reservation feeds (Agoda, GoMT)
  invoices/{raw,processed}/  EZ sheet / front office sales
  payments/{raw,processed}/  PTM aggregator, bank statements, PDF receipts
  tally/                     Tally exports — used as signals, not as source
  recon/{canonical,matches,reports}/
"""
