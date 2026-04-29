from xml.etree import ElementTree as ET
from tmv_recon.parsers import excel as xls
from tmv_recon.integration import load_preset, build, validate, has_errors
from tmv_recon.tally.xml import vouchers_envelope


def test_bank_statement_preset(bank_xlsx):
    df = xls.sheet(bank_xlsx)
    cmap = load_preset("bank_statement")
    vs = build(df, cmap)
    assert len(vs) == 3

    types = [v.voucher_type for v in vs]
    assert types == ["Payment", "Receipt", "Payment"]

    assert vs[0].entries[0].ledger == "Office Rent"   # Dr side
    assert vs[0].entries[1].ledger == "HDFC Bank"     # Cr side
    assert vs[1].entries[0].ledger == "HDFC Bank"     # Receipt: bank Dr
    assert vs[1].entries[1].ledger == "Acme Pvt Ltd"

    # Magnitudes preserved through messy formatting
    assert abs(vs[1].entries[0].amount) == 54500.0
    assert abs(vs[2].entries[0].amount) == 250.0

    # Each voucher must balance
    for v in vs:
        assert abs(sum(e.amount for e in v.entries)) < 0.01

    # Validation clean
    assert not has_errors(validate(vs))


def test_journal_preset_compound(journal_xlsx):
    df = xls.sheet(journal_xlsx)
    cmap = load_preset("journal")
    vs = build(df, cmap)
    assert len(vs) == 2
    assert [v.voucher_number for v in vs] == ["J1", "J2"]
    assert len(vs[0].entries) == 2
    assert len(vs[1].entries) == 3

    # Sign convention check: Dr=negative, Cr=positive
    j2 = vs[1]
    drs = [e for e in j2.entries if e.is_deemed_positive]
    crs = [e for e in j2.entries if not e.is_deemed_positive]
    assert all(e.amount < 0 for e in drs)
    assert all(e.amount > 0 for e in crs)
    assert abs(sum(e.amount for e in j2.entries)) < 0.01

    # Validation clean
    assert not has_errors(validate(vs))


def test_full_pipeline_to_xml(journal_xlsx):
    df = xls.sheet(journal_xlsx)
    cmap = load_preset("journal")
    vs = build(df, cmap)
    xml = vouchers_envelope(vs, company="TEST CO")
    root = ET.fromstring(xml)
    assert root.findtext("HEADER/ID") == "Vouchers"
    vouchers = root.findall(".//VOUCHER")
    assert len(vouchers) == 2
    assert root.findtext(".//SVCURRENTCOMPANY") == "TEST CO"


def test_validator_catches_unbalanced(bank_xlsx):
    df = xls.sheet(bank_xlsx)
    cmap = load_preset("bank_statement")
    vs = build(df, cmap)
    # Manually break one to confirm detection
    vs[0].entries[1].amount += 100
    issues = validate(vs)
    assert has_errors(issues)
    assert any("unbalanced" in i.message for i in issues)
