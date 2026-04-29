# Sales Voucher Generator - Quick Start

**5-minute setup guide**

---

## Generate Vouchers (Single Command)

```bash
cd /Volumes/CRESCENT/dev/project-sonnet/tmv-recon
python3 scripts/generate_sales_vouchers.py
```

**Output:** `data/recon/output/sales_vouchers_2026-04-29.xml`

---

## Validate Output

```bash
python3 scripts/validate_against_ground_truth.py
```

**Expected:** `SUCCESS RATE: 100.0%`

---

## Run Tests

```bash
python3 tests/test_integration_sales.py
```

**Expected:** `✓✓✓ ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY ✓✓✓`

---

## Programmatic Usage

```python
import sys
sys.path.insert(0, 'src')

from datetime import date
from tmv_recon.tally.voucher_generators import (
    Invoice,
    generate_sales_voucher,
    vouchers_envelope,
)

# Create invoice
invoice = Invoice(
    invoice_no="25-26/6453",
    invoice_date=date(2026, 3, 31),
    guest_name="MRS. MADHUR PIPARSANIA",
    net_amount=2984.19,
    cgst=74.60,
    sgst=74.60,
    gross_amount=3133.39,
    gst_rate=5.0,
)

# Generate voucher
voucher = generate_sales_voucher(invoice)

# Create envelope
xml = vouchers_envelope([voucher])

# Save
with open("output.xml", "w") as f:
    f.write(xml)
```

---

## Calculate GST from Gross Amount

```python
from tmv_recon.tally.voucher_generators import calculate_gst_split

# 5% GST
net, cgst, sgst = calculate_gst_split(5250.00, gst_rate=5.0)
# Returns: (5000.00, 125.00, 125.00)

# 18% GST
net, cgst, sgst = calculate_gst_split(59000.00, gst_rate=18.0)
# Returns: (50000.00, 4500.00, 4500.00)
```

---

## Key Files

**Input:**
- `data/recon/canonical/invoice.csv` (Invoice data)

**Output:**
- `data/recon/output/sales_vouchers_YYYY-MM-DD.xml` (Generated vouchers)

**Code:**
- `src/tmv_recon/tally/voucher_generators.py` (Main implementation)

**Tests:**
- `tests/test_sales_voucher.py` (Unit tests)
- `tests/test_integration_sales.py` (Integration tests)

**Scripts:**
- `scripts/generate_sales_vouchers.py` (CSV → XML generator)
- `scripts/validate_against_ground_truth.py` (Validator)

**Docs:**
- `docs/sales_voucher_generator.md` (Full documentation)
- `DELIVERY_SUMMARY.md` (Delivery summary)
- `QUICKSTART.md` (This file)

---

## Validation Checklist

- [x] Uses LEDGERENTRIES.LIST (not ALLLEDGERENTRIES.LIST)
- [x] Sign convention: ISDEEMEDPOSITIVE=No/Yes + amount sign
- [x] Narration: INVOICE NO:-{{invoice_no}} {{GUEST_NAME}}
- [x] GST validation: net + cgst + sgst = gross (±₹1)
- [x] Ledgers: Sundry Debtors, Income, CGST, SGST
- [x] XML escaping for special characters
- [x] Party ledger configuration
- [x] 100% pass rate against ground truth

---

## Troubleshooting

**Issue:** `No module named tmv_recon`  
**Fix:** Ensure `sys.path.insert(0, 'src')` before imports

**Issue:** `File not found: invoice.csv`  
**Fix:** Check path: `data/recon/canonical/invoice.csv`

**Issue:** `GST validation failed`  
**Fix:** Verify net + cgst + sgst = gross (within ₹1)

**Issue:** `Missing invoice_no`  
**Fix:** Invoice will be skipped, check CSV data quality

---

## Support

**Documentation:** `docs/sales_voucher_generator.md`  
**Requirements:** `docs/discovery-2026-04-29-requirements.md` §1.1  
**Ground Truth:** `data/tally/raw_xml/daybook_FY25-26.xml`

---

**Status:** ✓ Production Ready  
**Validation:** 100% pass rate  
**Last Updated:** 2026-04-29
