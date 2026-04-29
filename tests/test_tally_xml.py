"""Tally XML builder tests. No live Tally needed."""
from datetime import date
from xml.etree import ElementTree as ET

from tmv_recon.tally import Voucher, LedgerEntry, Ledger
from tmv_recon.tally.xml import vouchers_envelope, masters_envelope


def test_payment_voucher_balanced():
    v = Voucher(
        date=date(2026, 4, 28), voucher_type="Payment", voucher_number="1",
        narration="Office rent",
        entries=[
            LedgerEntry(ledger="Office Rent", amount=-12000.00, is_deemed_positive=True),
            LedgerEntry(ledger="HDFC Bank",   amount=12000.00, is_deemed_positive=False),
        ],
    )
    xml = vouchers_envelope([v], company="ACME PVT LTD")
    root = ET.fromstring(xml)
    assert root.tag == "ENVELOPE"
    assert root.findtext("HEADER/TALLYREQUEST") == "Import"
    assert root.findtext("HEADER/ID") == "Vouchers"
    voucher = root.find(".//VOUCHER")
    assert voucher.get("VCHTYPE") == "Payment"
    assert voucher.findtext("DATE") == "20260428"
    entries = voucher.findall("ALLLEDGERENTRIES.LIST")
    assert len(entries) == 2
    total = sum(float(e.findtext("AMOUNT")) for e in entries)
    assert abs(total) < 0.01, "Dr/Cr must balance"


def test_master_envelope():
    l = Ledger(name="HDFC Bank", parent="Bank Accounts", opening_balance=-12500)
    xml = masters_envelope([l], dup="@@DUPCOMBINE")
    root = ET.fromstring(xml)
    assert root.findtext("HEADER/ID") == "All Masters"
    assert root.find(".//IMPORTDUPS").text == "@@DUPCOMBINE"
    led = root.find(".//LEDGER")
    assert led.get("NAME") == "HDFC Bank"
    assert led.findtext("PARENT") == "Bank Accounts"
