"""Pytest fixtures: sample bank-statement and journal Excel files."""
from pathlib import Path
import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def bank_xlsx(tmp_path_factory: pytest.TempPathFactory) -> Path:
    df = pd.DataFrame([
        {"Date": "2026-04-02", "Ref No": "TXN001", "Description": "Office rent April",
         "UTR": "UTR-A1", "Withdrawal": 12000.00, "Deposit": None,
         "Counterparty": "Office Rent"},
        {"Date": "2026-04-05", "Ref No": "TXN002", "Description": "Sale to Acme",
         "UTR": "UTR-A2", "Withdrawal": None, "Deposit": "₹54,500.00",
         "Counterparty": "Acme Pvt Ltd"},
        {"Date": "05-04-2026", "Ref No": "TXN003", "Description": "Bank charges",
         "UTR": "", "Withdrawal": "(250.00)", "Deposit": None,
         "Counterparty": "Bank Charges"},
    ])
    p = tmp_path_factory.mktemp("xlsx") / "bank.xlsx"
    df.to_excel(p, index=False, engine="openpyxl")
    return p


@pytest.fixture(scope="session")
def journal_xlsx(tmp_path_factory: pytest.TempPathFactory) -> Path:
    df = pd.DataFrame([
        # Voucher J1: 2 entries (Dr Salary 50000, Cr Bank 50000)
        {"Voucher No": "J1", "Date": "2026-04-30", "Ledger": "Salaries",
         "Amount": 50000.00, "DrCr": "Dr", "Narration": "April salary", "Reference": "PAY-04"},
        {"Voucher No": "J1", "Date": "2026-04-30", "Ledger": "HDFC Bank",
         "Amount": 50000.00, "DrCr": "Cr", "Narration": "April salary", "Reference": "PAY-04"},
        # Voucher J2: 3 entries (compound)
        {"Voucher No": "J2", "Date": "2026-04-30", "Ledger": "Rent",
         "Amount": 10000.00, "DrCr": "Dr", "Narration": "Rent + GST", "Reference": "RENT-04"},
        {"Voucher No": "J2", "Date": "2026-04-30", "Ledger": "Input CGST",
         "Amount": 900.00,   "DrCr": "Dr", "Narration": "Rent + GST", "Reference": "RENT-04"},
        {"Voucher No": "J2", "Date": "2026-04-30", "Ledger": "HDFC Bank",
         "Amount": 10900.00, "DrCr": "Cr", "Narration": "Rent + GST", "Reference": "RENT-04"},
    ])
    p = tmp_path_factory.mktemp("xlsx") / "journal.xlsx"
    df.to_excel(p, index=False, engine="openpyxl")
    return p
