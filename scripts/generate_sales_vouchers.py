#!/usr/bin/env python3
"""Generate Sales vouchers from canonical invoices.csv.

Reads invoice data, generates Tally Sales vouchers, saves to XML file.
"""
import sys
import csv
from pathlib import Path
from datetime import datetime, date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.tally.voucher_generators import (
    Invoice,
    generate_sales_voucher,
    vouchers_envelope,
    calculate_gst_split,
)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    if not date_str or date_str == 'nan':
        return date.today()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        # Try other formats
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return date.today()


def parse_float(value: str) -> float:
    """Parse float, handling empty/nan values."""
    if not value or value.lower() == 'nan':
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def main():
    """Generate Sales vouchers from invoices.csv."""
    base_dir = Path(__file__).parent.parent
    invoices_path = base_dir / "data" / "recon" / "canonical" / "invoice.csv"
    output_dir = base_dir / "data" / "recon" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"sales_vouchers_{today}.xml"

    print(f"Reading invoices from: {invoices_path}")

    if not invoices_path.exists():
        print(f"ERROR: Invoice file not found: {invoices_path}")
        sys.exit(1)

    invoices = []
    skipped = []
    errors = []

    with open(invoices_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            try:
                invoice_no = row.get("invoice_no", "").strip()
                if not invoice_no or invoice_no == "nan":
                    skipped.append(f"Row {i}: Missing invoice_no")
                    continue

                # Parse amounts
                net_amount = parse_float(row.get("net_amount", "0"))
                cgst = parse_float(row.get("cgst", "0"))
                sgst = parse_float(row.get("sgst", "0"))
                gross_amount = parse_float(row.get("gross_amount", "0"))
                gst_rate = parse_float(row.get("gst_rate", "0"))

                # If GST components missing, calculate them
                if cgst == 0.0 and sgst == 0.0 and gross_amount > 0:
                    rate = gst_rate if gst_rate > 0 else 5.0
                    net_amount, cgst, sgst = calculate_gst_split(gross_amount, rate)

                # Validate minimum data
                if gross_amount <= 0:
                    skipped.append(f"Row {i} ({invoice_no}): Zero/negative gross_amount")
                    continue

                invoice = Invoice(
                    invoice_no=invoice_no,
                    invoice_date=parse_date(row.get("invoice_date", "")),
                    guest_name=row.get("guest_name", "").strip() or "Unknown Guest",
                    net_amount=net_amount,
                    cgst=cgst,
                    sgst=sgst,
                    gross_amount=gross_amount,
                    gst_rate=gst_rate,
                )

                invoices.append(invoice)

            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

    print(f"Loaded {len(invoices)} invoices")
    print(f"Skipped {len(skipped)} invoices")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"  - {err}")

    if not invoices:
        print("No valid invoices to process")
        sys.exit(1)

    # Limit to first 10 for sample
    sample_invoices = invoices[:10]
    print(f"\nGenerating vouchers for {len(sample_invoices)} invoices (sample)...")

    voucher_xmls = []
    generation_errors = []

    for invoice in sample_invoices:
        try:
            voucher_xml = generate_sales_voucher(invoice)
            voucher_xmls.append(voucher_xml)
        except Exception as e:
            generation_errors.append(f"{invoice.invoice_no}: {str(e)}")

    print(f"Generated {len(voucher_xmls)} vouchers")
    if generation_errors:
        print(f"Generation errors: {len(generation_errors)}")
        for err in generation_errors:
            print(f"  - {err}")

    if not voucher_xmls:
        print("No vouchers generated")
        sys.exit(1)

    # Generate envelope
    print("\nGenerating XML envelope...")
    envelope = vouchers_envelope(voucher_xmls)

    # Save to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(envelope)

    print(f"\n✓ Saved to: {output_path}")
    print(f"  Size: {len(envelope):,} bytes")
    print(f"  Vouchers: {len(voucher_xmls)}")

    # Print sample voucher details
    print("\nSample vouchers:")
    for inv in sample_invoices[:3]:
        print(f"  - {inv.invoice_no}: {inv.guest_name} (₹{inv.gross_amount:.2f})")

    if skipped:
        print(f"\nSkipped invoices ({len(skipped)}):")
        for skip in skipped[:5]:
            print(f"  - {skip}")
        if len(skipped) > 5:
            print(f"  ... and {len(skipped) - 5} more")


if __name__ == "__main__":
    main()
