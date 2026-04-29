"""Tests for Tally voucher validation."""

import pytest
import tempfile
from pathlib import Path
from tmv_recon.etl.validator import (
    validate_xml_wellformed,
    validate_amount_balance,
    validate_ledger_exists
)


def test_validate_xml_wellformed():
    """Test XML well-formedness check."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write('<root><item>test</item></root>')
        valid_xml = f.name

    is_valid, error = validate_xml_wellformed(valid_xml)
    assert is_valid is True
    assert error == ""
    Path(valid_xml).unlink()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write('<root><item>test</root>')  # Missing closing tag
        invalid_xml = f.name

    is_valid, error = validate_xml_wellformed(invalid_xml)
    assert is_valid is False
    assert "parse error" in error.lower()
    Path(invalid_xml).unlink()


def test_validate_amount_balance():
    """Test amount balancing validation."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write('''
            <ENVELOPE>
                <VOUCHER>
                    <ALLLEDGERENTRIES.LIST>
                        <AMOUNT>100.00</AMOUNT>
                    </ALLLEDGERENTRIES.LIST>
                    <ALLLEDGERENTRIES.LIST>
                        <AMOUNT>-100.00</AMOUNT>
                    </ALLLEDGERENTRIES.LIST>
                </VOUCHER>
            </ENVELOPE>
        ''')
        balanced_xml = f.name

    is_balanced, error, total = validate_amount_balance(balanced_xml)
    assert is_balanced is True
    assert abs(total) < 0.01
    Path(balanced_xml).unlink()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write('''
            <ENVELOPE>
                <VOUCHER>
                    <ALLLEDGERENTRIES.LIST>
                        <AMOUNT>100.00</AMOUNT>
                    </ALLLEDGERENTRIES.LIST>
                    <ALLLEDGERENTRIES.LIST>
                        <AMOUNT>-50.00</AMOUNT>
                    </ALLLEDGERENTRIES.LIST>
                </VOUCHER>
            </ENVELOPE>
        ''')
        unbalanced_xml = f.name

    is_balanced, error, total = validate_amount_balance(unbalanced_xml)
    assert is_balanced is False
    assert abs(total - 50.00) < 0.01
    Path(unbalanced_xml).unlink()


def test_validate_ledger_exists():
    """Test ledger catalog lookup."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write('''
            <ENVELOPE>
                <LEDGER NAME="Cash" RESERVEDNAME="">
                    <PARENT>Current Assets</PARENT>
                </LEDGER>
                <LEDGER NAME="Sales" RESERVEDNAME="">
                    <PARENT>Sales Accounts</PARENT>
                </LEDGER>
            </ENVELOPE>
        ''')
        catalog_xml = f.name

    exists, error = validate_ledger_exists("Cash", catalog_xml)
    assert exists is True
    assert error == ""

    exists, error = validate_ledger_exists("NonExistent", catalog_xml)
    assert exists is False
    assert "not found" in error.lower()

    Path(catalog_xml).unlink()
