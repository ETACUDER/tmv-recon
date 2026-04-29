from datetime import date
from tmv_recon.integration.transforms import to_date, to_amount, to_str


def test_to_date_iso():
    assert to_date("2026-04-28") == date(2026, 4, 28)


def test_to_date_indian():
    assert to_date("28-04-2026") == date(2026, 4, 28)
    assert to_date("28/04/2026") == date(2026, 4, 28)


def test_to_date_yyyymmdd():
    assert to_date("20260428") == date(2026, 4, 28)


def test_to_date_excel_serial():
    import pandas as pd
    serial = (pd.Timestamp("2026-04-28") - pd.Timestamp("1899-12-30")).days
    assert to_date(serial) == date(2026, 4, 28)


def test_to_amount_clean():
    assert to_amount("₹1,23,456.78") == 123456.78
    assert to_amount("Rs. 250") == 250.0
    assert to_amount("INR 1,000") == 1000.0
    assert to_amount("(500.00)") == -500.0   # parens = negative
    assert to_amount(1234.5) == 1234.5
    assert to_amount("") is None
    assert to_amount(None) is None


def test_to_str_handles_none():
    assert to_str(None) == ""
    assert to_str("  hi ") == "hi"
