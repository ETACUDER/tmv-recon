# Column Normalization Rules - Quick Reference

## AGODA Column Mappings

### Invoice Number Variants
```python
'INVOICE NO.'   → 'invoice_no'
'INVOICE  NO.'  → 'invoice_no'  # Double space variant
'INVOCIE NO.'   → 'invoice_no'  # Typo variant
'INVOCIE NO'    → 'invoice_no'  # Missing period
```

### Invoice Amount Variants
```python
'INVOICE AMT'    → 'invoice_amount'
'INVOICE AMT.'   → 'invoice_amount'
'INVOCIE AMT'    → 'invoice_amount'  # Typo
'INVOCIE AMT.'   → 'invoice_amount'
'invoice amt.'   → 'invoice_amount'  # Lowercase
```

### Commission + GST Variants
```python
'COMM + GST'  → 'commission_gst'
'COMM+GST'    → 'commission_gst'  # No spaces
'COMM +GST'   → 'commission_gst'  # Left space only
'COMM+ GST'   → 'commission_gst'  # Right space only
'comm + gst'  → 'commission_gst'  # Lowercase
```

### Site Amount Variants
```python
'AGODA SITE'   → 'agoda_site_amount'
'AGODAT SITE'  → 'agoda_site_amount'  # Typo
'site amt'     → 'agoda_site_amount'
```

### Standard Fields
```python
'Booking ID'         → 'booking_id'
'Reference number'   → 'reference_number'
'Guest name'         → 'guest_name'
'Booking paid by'    → 'booking_paid_by'
'From Agoda'         → 'payment_from_agoda'
'Check-in date'      → 'checkin_date'
'Check-out date'     → 'checkout_date'
'Transaction type'   → 'transaction_type'
'Property ID'        → 'property_id'
'Currency'           → 'currency'
'To property'        → 'to_property'
'Payout method'      → 'payout_method'
```

### Credit Note Variants
```python
'CREDIT NOTE'  → 'credit_note'
'credit note'  → 'credit_note'
'AMEND'        → 'credit_note'
'amend amt'    → 'credit_note'
```

## BANK Column Mappings

**Note:** Bank statements have NO standard headers. Headers appear at row ~21.

### Standard Bank Columns (Row 21)
```python
'Value Date'              → 'transaction_date'
'Description'             → 'description'
'Chq No/REF No/UTR No'    → 'utr_no'
'Debit Amount'            → 'debit_amount'
'Credit Amount'           → 'credit_amount'
'Balance'                 → 'balance'
```

### Metadata Fields (Rows 0-20)
```python
Row 6:  'Account Number : 7223534417'     → metadata['account_number']
Row 14: 'Statement Date :Fri Aug 08...'   → metadata['statement_date']
Row 15: 'Cleared Balance :894825.55'      → metadata['cleared_balance']
Row 19: 'Statement of Account from...'    → metadata['date_range']
```

## UPI Column Mappings

### Date Column Variants
```python
'Transaction_Date'  → 'transaction_date'  # Preferred
'Updated_Date'      → 'transaction_date'  # Variant in 1 file
```

### Standard UPI Columns
```python
'Amount'           → 'amount'
'Commission'       → 'commission'
'GST'              → 'gst'
'Settled_Amount'   → 'settled_amount'
'UTR_No.'          → 'utr_no'
'Settled_Date'     → 'settled_date'
'Payment_Mode'     → 'payment_mode'
'Issuing_Bank'     → 'issuing_bank'  # Only in 1 variant
```

## INVOICE Column Mappings

### Core Transaction Fields
```python
'Transaction Type'  → 'transaction_type'
'Reservation #'     → 'reservation_id'
'Invoice #'         → 'invoice_no'
'Invoice date'      → 'invoice_date'
'Transaction Date'  → 'transaction_date'
'Arrival'           → 'arrival_date'
'Folio #'           → 'folio_no'
```

### Guest/Booking Fields
```python
'Guest Name'        → 'guest_name'
'Bill To Name'      → 'bill_to_name'
'Company Name'      → 'company_name'
'Nationality'       → 'nationality'
'Business Source'   → 'business_source'
```

### Amount Fields
```python
'Net Amount'                              → 'net_amount'
'Taxable Amount'                          → 'taxable_amount'
'Gross Amount'                            → 'gross_amount'
'Settlement Amount'                       → 'settlement_amount'
'Discount Amount'                         → 'discount_amount'
'Tax Amount'                              → 'tax_amount_cgst'
'Tax Amount.1'                            → 'tax_amount_sgst'
'Actual Rate(Configured Rate)'            → 'configured_rate'
'Adjustment(Room Charge/Extra Charges)'   → 'adjustment_amount'
```

## Data Cleaning Rules

### Guest Name Normalization
```python
def normalize_guest_name(name: str) -> str:
    """
    Normalize guest names for fuzzy matching.
    
    Examples:
        "Mr.Nikhil Jat"      → "NIKHIL JAT"
        "Mrs. Priya Sharma"  → "PRIYA SHARMA"
        "indrajeet tiwari"   → "INDRAJEET TIWARI"
    """
    return (
        name
        .upper()
        .replace(r'^(MR\.|MRS\.|MS\.|DR\.|PROF\.)\s*', '', regex=True)
        .strip()
    )
```

### Date Normalization
```python
def normalize_date(date_str: str, source: str) -> datetime:
    """
    Parse dates from different sources.
    
    AGODA:   "7/3/2025 12:00:00 AM"     → 2025-07-03
    BANK:    "01/07/2025"                → 2025-07-01
    UPI:     "'2025-07-01 08:48:19'"    → 2025-07-01
    INVOICE: "2025-03-27"                → 2025-03-27
    """
    if source == 'agoda':
        return pd.to_datetime(date_str, format='%m/%d/%Y %I:%M:%S %p')
    elif source == 'bank':
        return pd.to_datetime(date_str, format='%d/%m/%Y')
    elif source == 'upi':
        return pd.to_datetime(date_str.strip("'"), format='%Y-%m-%d %H:%M:%S')
    else:  # invoice
        return pd.to_datetime(date_str)
```

### Amount Normalization
```python
def normalize_amount(amount_str: str) -> float:
    """
    Clean and parse amounts.
    
    Examples:
        "11687.12"      → 11687.12
        "35,997.98"     → 35997.98
        "470414.15CR"   → 470414.15
        " 1,234.56 "    → 1234.56
    """
    return (
        str(amount_str)
        .replace('CR', '')
        .replace('DR', '')
        .replace(',', '')
        .strip()
    )
    return float(cleaned)
```

### UTR Normalization
```python
def normalize_utr(utr_str: str) -> str:
    """
    Clean UTR references for matching.
    
    Examples:
        "'YESAP51833296492'"            → "YESAP51833296492"
        " YESBN12025070105404991 "      → "YESBN12025070105404991"
        "HDFCN52025070227523293"        → "HDFCN52025070227523293"
    """
    return str(utr_str).strip("' ").upper()
```

## Validation Rules

### Required Fields by Source

**AGODA**
```python
REQUIRED_FIELDS = [
    'booking_id',
    'guest_name',
    'payment_from_agoda',
    'checkin_date',
    'checkout_date'
]
```

**BANK**
```python
REQUIRED_FIELDS = [
    'transaction_date',
    'description',
    'utr_no',
    'credit_amount' OR 'debit_amount'  # At least one
]
```

**UPI**
```python
REQUIRED_FIELDS = [
    'transaction_date',
    'amount',
    'settled_amount',
    'utr_no'  # May be null for unsettled
]
```

**INVOICE**
```python
REQUIRED_FIELDS = [
    'reservation_id',
    'guest_name',
    'arrival_date',
    'transaction_date',
    'gross_amount'
]
```

### Data Type Validation

```python
FIELD_TYPES = {
    # Dates
    'transaction_date': datetime,
    'invoice_date': datetime,
    'checkin_date': datetime,
    
    # Amounts
    'amount': float,
    'invoice_amount': float,
    'credit_amount': float,
    
    # IDs (stored as strings to preserve leading zeros)
    'booking_id': str,
    'invoice_no': str,
    'reservation_id': str,
    'utr_no': str,
    
    # Text
    'guest_name': str,
    'description': str,
}
```

### Range Validation

```python
VALIDATION_RULES = {
    'amount': {'min': 0, 'max': 1_000_000},
    'commission': {'min': 0, 'max': 10_000},
    'gst': {'min': 0, 'max': 2_000},
    'transaction_date': {
        'min': datetime(2025, 1, 1),
        'max': datetime(2026, 12, 31)
    },
}
```

## Common Issues & Fixes

### Issue 1: Quoted Strings in UPI Files
**Problem:** `'2025-07-01 08:48:19'` instead of `2025-07-01 08:48:19`
**Fix:** `.str.strip("'")`

### Issue 2: Balance CR/DR Suffix
**Problem:** `470414.15CR` cannot be parsed as float
**Fix:** `.str.replace('CR', '').str.replace('DR', '')`

### Issue 3: Invoice Number Spelling
**Problem:** `INVOICE NO.` vs `INVOCIE NO.` not matched
**Fix:** Use normalization dict with all variants

### Issue 4: Guest Name Case/Titles
**Problem:** `Mr.Nikhil Jat` vs `NIKHIL JAT` not matched
**Fix:** Uppercase + regex remove title prefixes

### Issue 5: Bank Header Row Variable
**Problem:** Header at row 21 in some files, row 22 in others
**Fix:** Search for "Value Date" in first 30 rows

### Issue 6: UPI UTR Duplicates
**Problem:** 93% duplicate UTRs due to batch settlements
**Fix:** `GROUP BY utr_no, SUM(settled_amount)` before joining

### Issue 7: Null Invoice Numbers
**Problem:** 39% of invoices have null Invoice #
**Fix:** Use composite key: `(reservation_id, guest_name, arrival_date)`

### Issue 8: Date Format Ambiguity
**Problem:** `01/07/2025` - is it Jan 7 or July 1?
**Fix:** Bank uses DD/MM/YYYY, AGODA uses M/D/YYYY - parse separately

## Testing Checklist

- [ ] Parse all 17 AGODA variants successfully
- [ ] Extract bank metadata from all 4 bank variants
- [ ] Handle quoted strings in UPI files
- [ ] Normalize all guest names identically
- [ ] Parse all 4 date formats correctly
- [ ] Handle null invoice numbers gracefully
- [ ] Aggregate UPI by UTR before joining
- [ ] Match amounts within ±1% tolerance
- [ ] Extract UTR from bank descriptions
- [ ] Handle balance CR/DR suffixes
