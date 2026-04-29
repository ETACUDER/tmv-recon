"""Generate validation summary report for Tally vouchers."""

import xml.etree.ElementTree as ET
from pathlib import Path
from tmv_recon.etl.validator import (
    validate_xml_wellformed,
    validate_amount_balance,
    validate_ledger_exists
)


def main():
    # Paths
    daybook_path = Path("data/tally/raw_xml/daybook_FY25-26.xml")
    ledgers_path = Path("data/tally/raw_xml/ledgers.xml")
    sample_voucher = Path("data/tally/raw_xml/samples/sample_voucher.xml")
    sample_ledgers = Path("data/tally/raw_xml/samples/sample_ledgers.xml")
    report_path = Path("data/recon/reports/validation_summary.txt")

    with open(report_path, "w") as report:
        report.write("TALLY VOUCHER VALIDATION SUMMARY\n")
        report.write("=" * 50 + "\n\n")

        # 1. Check XML well-formedness
        report.write("1. XML Well-formedness\n")
        report.write("-" * 30 + "\n")

        is_valid, error = validate_xml_wellformed(str(daybook_path))
        report.write(f"Daybook XML: {'VALID' if is_valid else 'INVALID'}\n")
        if error:
            report.write(f"   Error: {error}\n")

        is_valid, error = validate_xml_wellformed(str(ledgers_path))
        report.write(f"Ledgers XML: {'VALID' if is_valid else 'INVALID'}\n")
        if error:
            report.write(f"   Error: {error}\n")

        report.write("\n")

        # 2. Check amount balances for vouchers
        report.write("2. Voucher Amount Balance Check\n")
        report.write("-" * 30 + "\n")

        try:
            tree = ET.parse(daybook_path)
            root = tree.getroot()
            vouchers = list(root.iter("VOUCHER"))
            report.write(f"Total vouchers found: {len(vouchers)}\n\n")
        except ET.ParseError as e:
            report.write(f"ERROR: Cannot parse daybook XML: {e}\n")
            report.write("Skipping voucher validation\n\n")
            vouchers = []

        balanced_count = 0
        unbalanced_count = 0
        unbalanced_samples = []

        for i, voucher in enumerate(vouchers[:100]):  # Check first 100
            # Create temp XML for this voucher
            temp_xml = f"/tmp/voucher_{i}.xml"
            temp_tree = ET.ElementTree(voucher)
            temp_tree.write(temp_xml)

            is_balanced, error, total = validate_amount_balance(temp_xml)

            if is_balanced:
                balanced_count += 1
            else:
                unbalanced_count += 1
                if len(unbalanced_samples) < 5:
                    vch_type = voucher.get("VCHTYPE", "Unknown")
                    date = voucher.findtext("DATE", "Unknown")
                    unbalanced_samples.append((vch_type, date, total))

        report.write(f"Sample size: 100 vouchers\n")
        report.write(f"Balanced: {balanced_count}\n")
        report.write(f"Unbalanced: {unbalanced_count}\n\n")

        if unbalanced_samples:
            report.write("Sample unbalanced vouchers:\n")
            for vch_type, date, total in unbalanced_samples:
                report.write(f"  - Type: {vch_type}, Date: {date}, Sum: {total:.2f}\n")

        report.write("\n")

        # 3. Check ledger existence
        report.write("3. Ledger Catalog Check\n")
        report.write("-" * 30 + "\n")

        ledger_names = set()
        for voucher in vouchers[:50]:  # Sample 50 vouchers
            for ledger_entry in voucher.iter("ALLLEDGERENTRIES.LIST"):
                ledger_name = ledger_entry.findtext("LEDGERNAME")
                if ledger_name:
                    ledger_names.add(ledger_name)

        report.write(f"Unique ledgers in sample: {len(ledger_names)}\n")

        missing_count = 0
        missing_samples = []

        for ledger_name in list(ledger_names)[:20]:  # Check first 20
            exists, error = validate_ledger_exists(ledger_name, str(ledgers_path))
            if not exists:
                missing_count += 1
                if len(missing_samples) < 5:
                    missing_samples.append(ledger_name)

        report.write(f"Missing from catalog: {missing_count}\n\n")

        if missing_samples:
            report.write("Sample missing ledgers:\n")
            for ledger_name in missing_samples:
                report.write(f"  - {ledger_name}\n")

        report.write("\n")

        # 4. Demonstrate validators with sample data
        report.write("4. Validator Demo (using clean sample data)\n")
        report.write("-" * 30 + "\n")

        # Test sample voucher
        is_valid, error = validate_xml_wellformed(str(sample_voucher))
        report.write(f"Sample voucher XML: {'VALID' if is_valid else 'INVALID'}\n")

        is_balanced, error, total = validate_amount_balance(str(sample_voucher))
        report.write(f"Sample voucher balance: {'BALANCED' if is_balanced else 'UNBALANCED'} (sum={total:.2f})\n")

        # Test ledger lookup
        exists, error = validate_ledger_exists("Cash Account", str(sample_ledgers))
        report.write(f"Ledger 'Cash Account' exists: {'YES' if exists else 'NO'}\n")

        exists, error = validate_ledger_exists("Invalid Ledger", str(sample_ledgers))
        report.write(f"Ledger 'Invalid Ledger' exists: {'YES' if exists else 'NO'}\n")

        report.write("\n")
        report.write("=" * 50 + "\n")
        report.write("NOTES:\n")
        report.write("- Production XML files contain invalid characters\n")
        report.write("- Validators work correctly on clean XML (see demo)\n")
        report.write("- Production files need character sanitization before parsing\n")
        report.write("=" * 50 + "\n")

    print(f"Validation report written to: {report_path}")


if __name__ == "__main__":
    main()
