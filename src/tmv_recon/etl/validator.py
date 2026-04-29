"""Minimal validation layer for Tally vouchers."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple


def validate_xml_wellformed(xml_path: str) -> Tuple[bool, str]:
    """
    Check if XML is well-formed by attempting to parse.

    Args:
        xml_path: Path to XML file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ET.parse(xml_path)
        return True, ""
    except ET.ParseError as e:
        return False, f"XML parse error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def validate_amount_balance(voucher_xml_path: str) -> Tuple[bool, str, float]:
    """
    Parse voucher XML and verify all AMOUNT fields sum to zero.

    Args:
        voucher_xml_path: Path to voucher XML file

    Returns:
        Tuple of (is_balanced, error_message, sum_total)
    """
    try:
        tree = ET.parse(voucher_xml_path)
        root = tree.getroot()

        amounts = []
        for amount_elem in root.iter("AMOUNT"):
            if amount_elem.text:
                try:
                    amounts.append(float(amount_elem.text))
                except ValueError:
                    pass

        if not amounts:
            return False, "No AMOUNT fields found", 0.0

        total = sum(amounts)

        # Use small epsilon for float comparison
        if abs(total) < 0.01:
            return True, "", total
        else:
            return False, f"Amounts do not balance: sum = {total:.2f}", total

    except ET.ParseError as e:
        return False, f"XML parse error: {e}", 0.0
    except Exception as e:
        return False, f"Error: {e}", 0.0


def validate_ledger_exists(
    ledger_name: str,
    catalog_path: str = "data/tally/raw_xml/ledgers.xml"
) -> Tuple[bool, str]:
    """
    Check if ledger exists in catalog.

    Args:
        ledger_name: Name of ledger to validate
        catalog_path: Path to ledgers XML catalog

    Returns:
        Tuple of (exists, error_message)
    """
    try:
        tree = ET.parse(catalog_path)
        root = tree.getroot()

        ledger_names = []
        for ledger in root.iter("LEDGER"):
            name = ledger.get("NAME")
            if name:
                ledger_names.append(name)

        if ledger_name in ledger_names:
            return True, ""
        else:
            return False, f"Ledger '{ledger_name}' not found in catalog"

    except ET.ParseError as e:
        return False, f"XML parse error in catalog: {e}"
    except Exception as e:
        return False, f"Error reading catalog: {e}"
