"""Generate sample bank.xlsx and journal.xlsx into data/input/ for manual testing."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "input"
OUT.mkdir(parents=True, exist_ok=True)

bank = pd.DataFrame([
    {"Date": "2026-04-02", "Ref No": "TXN001", "Description": "Office rent April",
     "UTR": "UTR-A1", "Withdrawal": 12000.00, "Deposit": None, "Counterparty": "Office Rent"},
    {"Date": "2026-04-05", "Ref No": "TXN002", "Description": "Sale to Acme",
     "UTR": "UTR-A2", "Withdrawal": None, "Deposit": "₹54,500.00", "Counterparty": "Acme Pvt Ltd"},
    {"Date": "05-04-2026", "Ref No": "TXN003", "Description": "Bank charges",
     "UTR": "", "Withdrawal": "(250.00)", "Deposit": None, "Counterparty": "Bank Charges"},
])
bank.to_excel(OUT / "bank.xlsx", index=False, engine="openpyxl")

journal = pd.DataFrame([
    {"Voucher No": "J1", "Date": "2026-04-30", "Ledger": "Salaries",
     "Amount": 50000.00, "DrCr": "Dr", "Narration": "April salary", "Reference": "PAY-04"},
    {"Voucher No": "J1", "Date": "2026-04-30", "Ledger": "HDFC Bank",
     "Amount": 50000.00, "DrCr": "Cr", "Narration": "April salary", "Reference": "PAY-04"},
    {"Voucher No": "J2", "Date": "2026-04-30", "Ledger": "Rent",
     "Amount": 10000.00, "DrCr": "Dr", "Narration": "Rent + GST", "Reference": "RENT-04"},
    {"Voucher No": "J2", "Date": "2026-04-30", "Ledger": "Input CGST",
     "Amount": 900.00,   "DrCr": "Dr", "Narration": "Rent + GST", "Reference": "RENT-04"},
    {"Voucher No": "J2", "Date": "2026-04-30", "Ledger": "HDFC Bank",
     "Amount": 10900.00, "DrCr": "Cr", "Narration": "Rent + GST", "Reference": "RENT-04"},
])
journal.to_excel(OUT / "journal.xlsx", index=False, engine="openpyxl")

print(f"wrote {OUT}/bank.xlsx and {OUT}/journal.xlsx")
