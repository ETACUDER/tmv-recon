"""Test Journal voucher generation."""
from datetime import date
from tmv_recon.tally.voucher_generators import generate_journal_voucher


def test_journal_voucher_basic():
    """Test basic Journal voucher structure."""
    xml = generate_journal_voucher(
        payment_amount=1000.0,
        invoice_no="25-26/6473",
        payment_mode="UPI",
        guest_name="Rohan Sharma",
        voucher_date=date(2026, 3, 31)
    )

    # Check structure
    assert 'VCHTYPE="Journal"' in xml
    assert 'ALLLEDGERENTRIES.LIST' in xml
    assert 'CARD / UPI / PAYTM / G PAY' in xml
    assert 'Sundry Debtors' in xml

    # Check amounts (payment ledger credited, debtors debited)
    assert '<AMOUNT>-1000.00</AMOUNT>' in xml
    assert '<AMOUNT>1000.00</AMOUNT>' in xml

    # Check narration
    assert 'BEING PAID THROUGH UPI AGAINST INVOICE NO:25-26/6473 ROHAN SHARMA' in xml

    # Check sign convention (appears in both entries)
    assert 'ISDEEMEDPOSITIVE' in xml
    assert xml.count('<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>') == 1
    assert xml.count('<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>') == 1


def test_journal_voucher_payment_modes():
    """Test different payment modes."""
    for mode in ['UPI', 'CARD', 'CASH', 'TPP']:
        xml = generate_journal_voucher(
            payment_amount=500.0,
            invoice_no="25-26/1234",
            payment_mode=mode,
            guest_name="Test Guest"
        )
        assert f'BEING PAID THROUGH {mode}' in xml


def test_journal_voucher_amounts():
    """Test amount formatting."""
    xml = generate_journal_voucher(
        payment_amount=1234.56,
        invoice_no="25-26/5000",
        payment_mode="UPI",
        guest_name="Test"
    )
    assert '<AMOUNT>-1234.56</AMOUNT>' in xml
    assert '<AMOUNT>1234.56</AMOUNT>' in xml


if __name__ == '__main__':
    test_journal_voucher_basic()
    test_journal_voucher_payment_modes()
    test_journal_voucher_amounts()
    print("All tests passed!")
