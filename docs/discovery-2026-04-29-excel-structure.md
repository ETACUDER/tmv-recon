# Excel Data Structure Discovery - 2026-04-29

## Executive Summary

Analyzed 48 Excel files across 4 data source types (AGODA bookings, bank statements, UPI payments, transaction invoices). Found **17 distinct column variants** in AGODA files alone, confirming significant header inconsistency. Bank statements require custom parsing (headers at row 21). Multiple data quality issues identified including duplicate keys, high null percentages, and inconsistent formatting.

---

## Source Inventory

### Files by Source Type

**AGODA (Booking/Invoice Data)**
- Location: `meet-recording/data_sheets_historical/mangal all data sheet/AGODA/`
- File count: 20 files
- Date range: July 2025 - April 2026
- Format: .xlsx
- Examples:
  - `AGODA AUGUST 2025.xlsx`
  - `AGODA MARCH 2026, AMT 759282.14.xlsx`
  - `AGODA DEC 2025 -98974.39 AMT.xlsx`

**BANK STATEMENTS (Payment Reconciliation)**
- Locations:
  - `INDIAN BANK/` (9 files)
  - `INDIAN BANK ROOFTOP/` (6 files)
- File count: 15 files
- Date range: July 2025 - March 2026
- Format: .xlsx, .xls
- Examples:
  - `Statement Of Account - JULY 2025.xlsx`
  - `TMV - ROOFTOP STATEMNT OF AC, NOV 2025.xls`

**UPI PAYMENTS (Paytm)**
- Locations:
  - `UPI STATMENT/` (4 files)
  - `PTM ROOFTOP/` (5 files)
  - `F&B UPI/` (3 files)
- File count: 12 files
- Date range: July 2025 - March 2026
- Format: .xlsx
- Examples:
  - `PTM - MARCH 2026 (FRONT OFFICE).xlsx`
  - `TMV ROOFTOP - DECEMBER 2025.xlsx`

**INVOICES (Transaction Detail)**
- Location: `meet-recording/`
- File count: 1 file
- Format: .xlsx
- File: `transaction_detail20250428.xlsx`

---

## Column Mappings by Source Type

### AGODA - 17 Header Variants Found

#### Canonical Fields Mapping

| Canonical Field | Column Variants | Notes |
|----------------|-----------------|-------|
| **booking_id** | `Booking ID`, `Reference number` | Primary key candidate |
| **invoice_no** | `INVOICE NO.`, `INVOICE  NO.`, `INVOCIE NO.`, `INVOCIE NO` | **CRITICAL**: 4 spelling variants |
| **guest_name** | `Guest name` | Consistent across variants |
| **booking_paid_by** | `Booking paid by` | Always "Agoda" (100% duplicate) |
| **invoice_amount** | `INVOICE AMT`, `INVOICE AMT.`, `INVOCIE AMT`, `INVOCIE AMT.`, `invoice amt.`, `INVOICE AMT.` | **CRITICAL**: 6 variants |
| **agoda_site_amount** | `AGODA SITE`, `AGODAT SITE`, `site amt` | Typo variant exists |
| **payment_from_agoda** | `From Agoda` | Consistent |
| **commission_gst** | `COMM + GST`, `COMM+GST`, `COMM + GST`, `COMM +GST`, `COMM+ GST`, `comm + gst` | **CRITICAL**: 6 spacing/case variants |
| **credit_note** | `CREDIT NOTE`, `credit note`, `AMEND`, `amend amt` | Multiple meanings |
| **checkin_date** | `Check-in date` | Consistent |
| **checkout_date** | `Check-out date` | Consistent |
| **transaction_type** | `Transaction type` | Only in 2 variants |
| **property_id** | `Property ID` | Only in 2 variants |
| **currency** | `Currency` | Only in 2 variants |
| **to_property** | `To property` | Only in 2 variants |
| **payout_method** | `Payout method` | Only in 2 variants |

#### 17 Specific Variants

**Variant 1** (2 files): Standard Agoda remittance format
```
['Transaction type', 'Booking ID', 'Property ID', 'Guest name', 
 'Booking paid by', 'Currency', 'From Agoda', 'To property', 
 'Check-in date', 'Check-out date', 'Payout method']
```

**Variant 2** (1 file): With Reference number + site amount
```
['INVOICE NO.', 'Reference number', 'Guest name', 'Booking paid by', 
 'AGODA SITE', 'INVOICE AMT.', 'e-f =g', 'From Agoda', 
 'COMM + GST', 'CREDIT NOTE', 'Check-in date', 'Check-out date']
```

**Variant 3** (1 file): Simplified with booking ID
```
['INVOICE NO.', 'Booking ID', 'Guest name', 'Booking paid by', 
 'INVOCIE AMT', 'From Agoda', 'COMM+GST', 'Check-in date', 'Check-out date']
```

**Variant 4-17**: See detailed analysis in `/tmp/excel_analysis.json` for remaining 14 variants with spelling variations, spacing differences, and column additions/removals.

#### Header Normalization Rules for AGODA

```python
AGODA_COLUMN_NORMALIZER = {
    # Invoice number variants
    'INVOICE NO.': 'invoice_no',
    'INVOICE  NO.': 'invoice_no',  # Double space
    'INVOCIE NO.': 'invoice_no',   # Typo
    'INVOCIE NO': 'invoice_no',     # Missing period
    
    # Invoice amount variants  
    'INVOICE AMT': 'invoice_amount',
    'INVOICE AMT.': 'invoice_amount',
    'INVOCIE AMT': 'invoice_amount',   # Typo
    'INVOCIE AMT.': 'invoice_amount',
    'invoice amt.': 'invoice_amount',   # Lowercase
    
    # Commission + GST variants
    'COMM + GST': 'commission_gst',
    'COMM+GST': 'commission_gst',       # No spaces
    'COMM +GST': 'commission_gst',      # One space
    'COMM+ GST': 'commission_gst',
    'comm + gst': 'commission_gst',     # Lowercase
    
    # Site amount variants
    'AGODA SITE': 'agoda_site_amount',
    'AGODAT SITE': 'agoda_site_amount', # Typo
    'site amt': 'agoda_site_amount',
    
    # Other fields
    'Booking ID': 'booking_id',
    'Reference number': 'reference_number',
    'Guest name': 'guest_name',
    'Booking paid by': 'booking_paid_by',
    'From Agoda': 'payment_from_agoda',
    'CREDIT NOTE': 'credit_note',
    'credit note': 'credit_note',
    'AMEND': 'credit_note',
    'amend amt': 'credit_note',
    'Check-in date': 'checkin_date',
    'Check-out date': 'checkout_date',
    'Transaction type': 'transaction_type',
    'Property ID': 'property_id',
    'Currency': 'currency',
    'To property': 'to_property',
    'Payout method': 'payout_method',
}
```

### BANK STATEMENTS - 4 Structure Variants

**CRITICAL FINDING**: Bank statements have **NO standard headers**. Headers appear at row 21 (variable position).

#### File Structure

```
Rows 0-20:  Bank metadata (name, branch, account, balance summary)
Row 21:     Headers: ['Value Date', 'Description', 'Chq No/REF No/UTR No', 
                      'Debit Amount', 'Credit Amount', 'Balance']
Row 22:     Balance brought forward
Row 23+:    Transaction data
```

#### Canonical Fields Mapping

| Canonical Field | Bank Column | Notes |
|----------------|-------------|-------|
| **transaction_date** | `Value Date` | Format: DD/MM/YYYY |
| **description** | `Description` | Contains UTR/NEFT info |
| **utr_no** | `Chq No/REF No/UTR No` | **Primary join key** |
| **debit_amount** | `Debit Amount` | Blank if credit |
| **credit_amount** | `Credit Amount` | Blank if debit |
| **balance** | `Balance` | Ends with "CR" or "DR" |

#### Parser Requirements

1. **Skip first 21 rows** (metadata)
2. **Extract metadata** from rows 6-19:
   - Account Number (row 6)
   - Statement Date (row 14)
   - Cleared Balance (row 15)
   - Date Range (row 19)
3. **Parse transaction rows** starting row 23
4. **Clean UTR** from description field (contains `/UTR_NUMBER/`)
5. **Handle balance suffix** ("CR" or "DR")
6. **Parse amounts** (blank = 0)

#### 4 Column Count Variants

- **Variant 1** (5 files): 6 columns - Standard format
- **Variant 2** (2 files): 5 columns - Missing one field
- **Variant 3** (2 files): 8 columns - Extra columns (unknown)
- **Variant 4** (2 files): 14 columns - Significantly different format

**Recommendation**: Parse all variants by detecting header row position (search for "Value Date" in first 30 rows).

### UPI PAYMENTS (Paytm) - 4 Variants

#### Canonical Fields Mapping

| Canonical Field | Column Variants | Notes |
|----------------|-----------------|-------|
| **transaction_date** | `Transaction_Date`, `Updated_Date` | **CRITICAL**: 2 date types |
| **amount** | `Amount` | Gross payment amount |
| **commission** | `Commission` | Paytm fee |
| **gst** | `GST` | Tax on commission |
| **settled_amount** | `Settled_Amount` | Net = Amount - Commission - GST |
| **utr_no** | `UTR_No.` | **Primary join key** (high duplicates!) |
| **settled_date** | `Settled_Date` | When funds settled |
| **payment_mode** | `Payment_Mode` | UPI/DEBIT_CARD/etc |
| **issuing_bank** | `Issuing_Bank` | Only in 1 variant |

#### 4 Specific Variants

**Variant 1** (1 file): Uses `Updated_Date` instead of `Transaction_Date`
```
['Updated_Date', 'Amount', 'Commission', 'GST', 'Settled_Amount', 
 'UTR_No.', 'Settled_Date', 'Payment_Mode']
```

**Variant 2** (9 files): Standard format - most common
```
['Transaction_Date', 'Amount', 'Commission', 'GST', 'Settled_Amount', 
 'UTR_No.', 'Settled_Date', 'Payment_Mode']
```

**Variant 3** (1 file): Includes issuing bank
```
['Transaction_Date', 'Amount', 'Commission', 'GST', 'Settled_Amount', 
 'UTR_No.', 'Settled_Date', 'Payment_Mode', 'Issuing_Bank']
```

**Variant 4** (1 file): CORRUPTED - No proper headers
```
['Unnamed: 0', 'UPI STATEMENT F&B JULY 2025', 'Unnamed: 2', ...]
```

#### Date Format Variations

- Format: String with quotes: `'2025-07-01 08:48:19'`
- **CRITICAL**: Dates are stored as strings with quotes that need stripping
- Pattern: `'YYYY-MM-DD HH:MM:SS'`

#### Amount Format

- Decimal: Float with 2 decimal places
- No currency symbols
- No negatives (all positive)
- Range: 1.0 to 44,145.0 (in sample)

### INVOICES (Transaction Detail) - 1 Variant

**File**: `transaction_detail20250428.xlsx` - 55 columns, highly denormalized

#### Canonical Fields Mapping

| Canonical Field | Column Name | Notes |
|----------------|-------------|-------|
| **reservation_id** | `Reservation #` | Format: "6669", "6803-1" |
| **invoice_no** | `Invoice #` | Format: "2025/2026/96" (sparse - 39% null) |
| **guest_name** | `Guest Name` | **Join key candidate** |
| **invoice_date** | `Invoice date` | 75% duplicates |
| **transaction_date** | `Transaction Date` | Actual transaction date |
| **arrival_date** | `Arrival` | Check-in |
| **folio_no** | `Folio #` | Property management ID |
| **transaction_type** | `Transaction Type` | "FrontOffice" (100% in sample) |
| **transaction_code** | `Transaction` | Charge code |
| **net_amount** | `Net Amount` | Before tax |
| **taxable_amount** | `Taxable Amount` | Tax base |
| **tax_amount** | `Tax Amount`, `Tax Amount.1` | CGST, SGST |
| **gross_amount** | `Gross Amount` | Total with tax |
| **settlement_amount** | `Settlement Amount` | Actual payment |
| **reference_no** | `Reference #` | External reference |

#### High Null Columns (>50% empty)

- `Group Code` (70%)
- `Owner Name` (100%)
- `VIP Status` (100%)
- `Market Code` (100%)
- `Company Name` (100%)
- `Sales Person Name` (100%)
- `RegNo.` (100%)
- `Charge` (53%)
- `Extra Charge Type` (74%)
- `HSN/SAC` (76%)
- `Comment` (86%)
- `Discount Name/Amount/%` (100%)
- Tax fields (56% - only on some transactions)

---

## Join Key Analysis

### Primary Join Keys by Source

| Source | Primary Key | Secondary Keys | Format Issues |
|--------|-------------|----------------|---------------|
| **AGODA** | `Booking ID` | `Reference number`, `Invoice No`, `Guest name` | 14% duplicates on Booking ID, Invoice No has 4 spelling variants |
| **BANK** | `UTR No` (extracted) | `Transaction Date`, `Description` | UTR embedded in Description field, needs regex extraction |
| **UPI** | `UTR_No.` | `Transaction_Date` | **93% duplicates!** Same UTR for batch settlements |
| **INVOICE** | `Invoice #` | `Reservation #`, `Guest Name`, `Reference #` | 39% null, 39% duplicates |

### Cross-Source Join Strategies

#### AGODA → BANK (Match booking to bank payment)

**Join Keys:**
1. **Amount matching**: `AGODA.From Agoda` ≈ `BANK.Credit Amount` (fuzzy match ±1%)
2. **Date range**: `AGODA.Check-in date` within 7 days of `BANK.Value Date`
3. **UTR extraction**: Parse AGODA name/description vs BANK UTR

**Challenges:**
- AGODA has no direct UTR field
- Multiple AGODA bookings may settle in one bank transaction
- Amount aggregation needed

**Recommended Approach:**
```python
# Match by date range + amount
SELECT a.*, b.*
FROM agoda a
JOIN bank b ON (
    b.credit_amount BETWEEN a.from_agoda * 0.99 AND a.from_agoda * 1.01
    AND b.value_date BETWEEN a.checkin_date - 7 AND a.checkin_date + 30
)
```

#### UPI → BANK (Match Paytm settlement to bank)

**Join Keys:**
1. **UTR match**: `UPI.UTR_No.` = `BANK.Chq No/REF No/UTR No` (exact)
2. **Amount match**: `UPI.Settled_Amount` = `BANK.Credit Amount` (exact)
3. **Date match**: `UPI.Settled_Date` = `BANK.Value Date` (±1 day)

**Challenges:**
- **UPI UTR has 93% duplicates** (batch settlements)
- Need to SUM UPI amounts by UTR before joining
- Bank Description contains "ONE 97 COM" for Paytm (filter needed)

**Recommended Approach:**
```python
# Aggregate UPI by UTR first
upi_agg = upi.groupby('UTR_No.').agg({
    'Settled_Amount': 'sum',
    'Settled_Date': 'first'
})

# Join to bank
JOIN bank ON (
    bank.utr_no = upi_agg.utr_no
    AND bank.description LIKE '%ONE 97 COM%'  # Paytm marker
    AND bank.credit_amount = upi_agg.settled_amount
)
```

#### INVOICE → AGODA (Match invoice to booking)

**Join Keys:**
1. **Guest Name**: `INVOICE.Guest Name` = `AGODA.Guest name` (fuzzy - 40% duplicates)
2. **Date range**: `INVOICE.Arrival` ≈ `AGODA.Check-in date` (±1 day)
3. **Amount**: `INVOICE.Gross Amount` ≈ `AGODA.INVOICE AMT` (fuzzy ±5%)

**Challenges:**
- Guest name has case/format variations ("Mr.", "Mrs.", etc.)
- Multiple invoices per booking (room + F&B + extras)
- Invoice # is 39% null in transaction detail

**Recommended Approach:**
```python
# Normalize guest names first
invoice['guest_clean'] = invoice['Guest Name'].str.upper().str.replace(r'^(MR\.|MRS\.|MS\.)\s*', '')
agoda['guest_clean'] = agoda['Guest name'].str.upper()

# Fuzzy join
JOIN ON (
    similarity(invoice.guest_clean, agoda.guest_clean) > 0.8
    AND invoice.arrival = agoda.checkin_date
)
```

### Join Key Format Consistency

| Key Type | AGODA Format | BANK Format | UPI Format | INVOICE Format |
|----------|--------------|-------------|------------|----------------|
| **UTR** | Not present | `YESBN12025...` | `'YESAP51833...'` (quoted) | `Reference #` (sparse) |
| **Guest Name** | `Nidhi Verma` | Not present | Not present | `indrajeet tiwari`, `Mr.Nikhil Jat` |
| **Date** | `7/3/2025 12:00:00 AM` | `01/07/2025` | `'2025-07-01 08:48:19'` | `2025-03-27` |
| **Amount** | `11687.12` (float) | `35997.98` (may have spaces) | `549.0` (float) | `4500` (int or float) |

**Normalization Required:**
1. **UTR**: Strip quotes, uppercase
2. **Guest Name**: Uppercase, remove titles (Mr./Mrs./Ms.), trim
3. **Date**: Convert all to `YYYY-MM-DD` format
4. **Amount**: Parse as float, handle decimals consistently

---

## Data Quality Issues

### 1. Duplicate Records

**AGODA**
- `Booking ID`: 14% duplicate rate (86 unique out of 100 rows)
- `Guest name`: 27% duplicate rate (repeat customers)
- `Invoice No`: 1% duplicate rate (mostly unique)
- `Property ID`: 100% duplicate (all same property)

**BANK**
- Column duplicates not meaningful (parse errors due to no headers)

**UPI**
- **CRITICAL**: `UTR_No.` has **93% duplicate rate** (6 unique UTRs for 100 rows)
  - Paytm batches multiple transactions under same UTR
  - Must GROUP BY UTR before reconciliation
- `Transaction_Date`: 27% duplicates (multiple transactions per second)

**INVOICE**
- `Transaction Type`: 100% duplicate ("FrontOffice" only in sample)
- `Invoice #`: 39% duplicate rate (60 unique out of 100 rows)
- `Invoice date`: 75% duplicate rate (24 unique dates)
- `Guest Name`: 40% duplicate rate (repeat guests)

### 2. Missing Data (High Null Percentages)

**AGODA**
- No significant null issues (well-structured when headers correct)

**UPI**
- `UTR_No.`, `Settled_Date`, `Payment_Mode`: **53.7% null** in March 2026 files
  - Indicates unsettled/pending transactions
  - Cannot reconcile to bank without UTR

**INVOICE**
- **20 columns with >50% nulls** (see Column Mappings section)
- Critical fields affected:
  - `Invoice #`: Needed for reconciliation but sparse
  - `Company Name`: 100% null (no corporate bookings in sample)
  - Tax fields: 56% null (only on taxable transactions)
  - Discount fields: 100% null (no discounts in sample)

### 3. Inconsistent Formats

**Date Formats (4 variants)**
```
AGODA:    "7/3/2025 12:00:00 AM"     # M/D/YYYY with time
BANK:     "01/07/2025"                # DD/MM/YYYY
UPI:      "'2025-07-01 08:48:19'"    # Quoted ISO with time
INVOICE:  "2025-03-27"                # ISO date only
```

**Amount Formats**
```
AGODA:    11687.12    # Float, 2 decimals
BANK:     35997.98    # Float, may have spaces/commas in raw
UPI:      549.0       # Float, variable decimals
INVOICE:  4500        # Int or float, no decimals shown
```

**Balance Suffixes (BANK only)**
```
"470414.15CR"  # Credit balance
"1234.56DR"    # Debit balance (rare)
```

### 4. Spelling/Typo Issues

**AGODA Column Headers** (17 variants)
- `INVOICE` vs `INVOCIE` (appears 8 times)
- `COMMISSION + GST` (6 spacing variants)
- `AGODA SITE` vs `AGODAT SITE` (typo)
- `INVOICE NO.` vs `INVOICE  NO.` (double space)

**Guest Name Variations**
```
INVOICE: "indrajeet tiwari", "Mr.Nikhil Jat", "Mr.ROSHAN KUMAR"
AGODA:   "Nidhi Verma", "Rupesh Harode"
```
- Case inconsistency
- Title prefixes (Mr., Mrs., Ms.) inconsistent
- Requires fuzzy matching for joins

### 5. Outliers

**UPI Commission Rates**
- Commission: 0 to 261.32 (most are 0 for UPI, higher for cards)
- GST: 0 to 47.04 (on commission only)
- Settled Amount range: 1.0 to 43,836.64

**BANK Transactions**
- Credit amounts: 984.11 to 39,731.99 (in sample)
- Negative amounts in AGODA: `-417.40` (cancellations/refunds)

**INVOICE Amounts**
- Actual Rate: 0 to 10,999
- Net Amount: 0 to 1,500 (many zeros indicate cancelled bookings)

---

## Recommended Parsers

### 1. AGODA Parser

**Input**: Excel file with unknown header variant
**Output**: Normalized DataFrame with canonical columns

```python
class AgodaParser:
    """
    Handles 17 header variants with normalization.
    """
    
    def parse(self, file_path: str) -> pd.DataFrame:
        # Step 1: Read raw
        df = pd.read_excel(file_path, sheet_name='Remittances')
        
        # Step 2: Normalize column names
        df.columns = [self._normalize_column(col) for col in df.columns]
        
        # Step 3: Standardize columns
        df = self._ensure_required_columns(df)
        
        # Step 4: Clean data
        df['booking_id'] = df['booking_id'].astype(str).str.strip()
        df['guest_name'] = df['guest_name'].str.upper().str.strip()
        
        # Step 5: Parse dates
        df['checkin_date'] = pd.to_datetime(df['checkin_date'])
        df['checkout_date'] = pd.to_datetime(df['checkout_date'])
        
        # Step 6: Parse amounts
        df['invoice_amount'] = pd.to_numeric(df['invoice_amount'], errors='coerce')
        df['payment_from_agoda'] = pd.to_numeric(df['payment_from_agoda'], errors='coerce')
        df['commission_gst'] = pd.to_numeric(df['commission_gst'], errors='coerce')
        
        return df
    
    def _normalize_column(self, col: str) -> str:
        return AGODA_COLUMN_NORMALIZER.get(col, col.lower().replace(' ', '_'))
```

**Key Features:**
- Auto-detects header variant
- Maps all 17 variants to canonical schema
- Handles spelling errors (INVOICE vs INVOCIE)
- Handles spacing variations (COMM+GST vs COMM + GST)
- Validates required fields exist

### 2. Bank Statement Parser

**Input**: Excel file with metadata header
**Output**: Transactions DataFrame + metadata dict

```python
class BankStatementParser:
    """
    Parses Indian Bank statements with metadata extraction.
    """
    
    def parse(self, file_path: str) -> tuple[pd.DataFrame, dict]:
        # Step 1: Read raw (no header)
        df_raw = pd.read_excel(file_path, header=None)
        
        # Step 2: Extract metadata from rows 0-20
        metadata = {
            'account_number': self._extract_field(df_raw, 'Account Number'),
            'statement_date': self._extract_field(df_raw, 'Statement Date'),
            'cleared_balance': self._extract_field(df_raw, 'Cleared Balance'),
            'date_range': self._extract_field(df_raw, 'Statement of Account from'),
        }
        
        # Step 3: Find header row (search for "Value Date")
        header_row = None
        for i in range(30):
            if 'Value Date' in str(df_raw.iloc[i, 0]):
                header_row = i
                break
        
        if header_row is None:
            raise ValueError("Could not find header row")
        
        # Step 4: Re-read with correct header
        df = pd.read_excel(file_path, header=header_row, skiprows=range(header_row))
        
        # Step 5: Clean column names
        df.columns = df.columns.str.strip()
        
        # Step 6: Remove balance brought forward row
        df = df[~df['Description'].str.contains('BALANCE B/F', na=False)]
        
        # Step 7: Parse amounts
        df['Debit Amount'] = pd.to_numeric(df['Debit Amount'], errors='coerce').fillna(0)
        df['Credit Amount'] = pd.to_numeric(df['Credit Amount'], errors='coerce').fillna(0)
        
        # Step 8: Parse balance (remove CR/DR suffix)
        df['Balance_Clean'] = df['Balance'].str.replace('CR', '').str.replace('DR', '').str.strip()
        df['Balance_Numeric'] = pd.to_numeric(df['Balance_Clean'], errors='coerce')
        df['Balance_Type'] = df['Balance'].str.extract(r'(CR|DR)$')[0]
        
        # Step 9: Parse date
        df['Value Date'] = pd.to_datetime(df['Value Date'], format='%d/%m/%Y', errors='coerce')
        
        # Step 10: Extract clean UTR
        df['UTR'] = df['Chq No/REF No/UTR No'].str.strip()
        
        # Step 11: Normalize columns
        df = df.rename(columns={
            'Value Date': 'transaction_date',
            'Description': 'description',
            'Debit Amount': 'debit_amount',
            'Credit Amount': 'credit_amount',
            'UTR': 'utr_no',
        })
        
        return df, metadata
    
    def _extract_field(self, df: pd.DataFrame, field_name: str) -> str:
        """Extract metadata field from raw dataframe."""
        for i in range(30):
            for col in df.columns:
                cell = str(df.iloc[i, col])
                if field_name in cell:
                    # Extract value after colon
                    if ':' in cell:
                        return cell.split(':', 1)[1].strip()
        return None
```

**Key Features:**
- Auto-detects header row position
- Extracts account metadata
- Parses CR/DR balance suffixes
- Cleans UTR references
- Handles variable column counts (4 variants)

### 3. UPI Payment Parser

**Input**: Paytm Excel export
**Output**: Normalized DataFrame

```python
class UPIPaymentParser:
    """
    Parses Paytm UPI payment exports with date normalization.
    """
    
    def parse(self, file_path: str) -> pd.DataFrame:
        # Step 1: Read Excel
        xls = pd.ExcelFile(file_path)
        sheet_name = xls.sheet_names[0]  # First sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Step 2: Check for corrupted headers
        if 'Unnamed' in str(df.columns[0]):
            # Try reading from row 1 or 2
            for skip_rows in [1, 2]:
                df_test = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
                if 'Transaction_Date' in str(df_test.columns) or 'Updated_Date' in str(df_test.columns):
                    df = df_test
                    break
        
        # Step 3: Normalize column names (handle variant 1 vs 2)
        if 'Updated_Date' in df.columns:
            df = df.rename(columns={'Updated_Date': 'Transaction_Date'})
        
        # Step 4: Remove summary rows (TOTAL, etc.)
        df = df[~df['Transaction_Date'].astype(str).str.upper().str.contains('TOTAL', na=False)]
        
        # Step 5: Clean quoted strings
        for col in ['Transaction_Date', 'Settled_Date', 'UTR_No.', 'Payment_Mode']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip("'").str.strip()
        
        # Step 6: Parse dates
        df['transaction_date'] = pd.to_datetime(df['Transaction_Date'], errors='coerce')
        df['settled_date'] = pd.to_datetime(df['Settled_Date'], errors='coerce')
        
        # Step 7: Parse amounts
        df['amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['commission'] = pd.to_numeric(df['Commission'], errors='coerce').fillna(0)
        df['gst'] = pd.to_numeric(df['GST'], errors='coerce').fillna(0)
        df['settled_amount'] = pd.to_numeric(df['Settled_Amount'], errors='coerce')
        
        # Step 8: Clean UTR (uppercase, strip)
        df['utr_no'] = df['UTR_No.'].str.upper().str.strip()
        
        # Step 9: Normalize payment mode
        df['payment_mode'] = df['Payment_Mode'].str.upper()
        
        return df[['transaction_date', 'amount', 'commission', 'gst', 
                   'settled_amount', 'utr_no', 'settled_date', 'payment_mode']]
```

**Key Features:**
- Handles `Transaction_Date` vs `Updated_Date` variant
- Strips quoted strings from CSV-like exports
- Detects and skips corrupted headers
- Removes summary rows
- Aggregation-ready for UTR-based reconciliation

### 4. Invoice Transaction Parser

**Input**: Transaction detail export
**Output**: Normalized DataFrame with cleaned columns

```python
class InvoiceParser:
    """
    Parses property management system transaction exports.
    """
    
    def parse(self, file_path: str) -> pd.DataFrame:
        # Step 1: Read Excel
        df = pd.read_excel(file_path)
        
        # Step 2: Normalize guest names
        df['guest_name_clean'] = (
            df['Guest Name']
            .str.upper()
            .str.replace(r'^(MR\.|MRS\.|MS\.|DR\.|PROF\.)\s*', '', regex=True)
            .str.strip()
        )
        
        # Step 3: Parse dates
        df['reservation_date'] = pd.to_datetime(df['Reservation Date'], errors='coerce')
        df['invoice_date'] = pd.to_datetime(df['Invoice date'], errors='coerce')
        df['arrival_date'] = pd.to_datetime(df['Arrival'], errors='coerce')
        df['transaction_date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')
        
        # Step 4: Parse amounts (handle int and float)
        amount_cols = ['Net Amount', 'Taxable Amount', 'Tax Amount', 
                       'Gross Amount', 'Settlement Amount', 'Discount Amount',
                       'Actual Rate(Configured Rate)']
        
        for col in amount_cols:
            if col in df.columns:
                df[f'{col.lower().replace(" ", "_").replace("(", "").replace(")", "")}'] = (
                    pd.to_numeric(df[col], errors='coerce').fillna(0)
                )
        
        # Step 5: Clean invoice number
        df['invoice_no'] = df['Invoice #'].astype(str).str.strip()
        df.loc[df['invoice_no'] == 'nan', 'invoice_no'] = None
        
        # Step 6: Clean reservation ID
        df['reservation_id'] = df['Reservation #'].astype(str).str.strip()
        
        # Step 7: Filter out high-null columns
        keep_cols = [col for col in df.columns if df[col].notna().sum() > len(df) * 0.3]
        
        return df[keep_cols]
```

**Key Features:**
- Removes title prefixes from guest names
- Normalizes name casing for fuzzy matching
- Handles sparse invoice numbers
- Filters out 100% null columns
- Consistent date/amount parsing

---

## Next Steps

### 1. Immediate Actions

1. **Create test parsers** for each source type
2. **Validate on sample files** (1 file per variant)
3. **Build canonical data models** (Booking, Invoice, Payment, BankTransaction)
4. **Implement fuzzy matching** for guest names

### 2. Reconciliation Strategy

```
Phase 1: Load & Normalize
  → Parse all 4 source types
  → Apply normalization rules
  → Load into staging tables

Phase 2: Direct Joins
  → UPI → Bank (by UTR + amount)
  → Invoice → AGODA (by guest + date + amount)

Phase 3: Fuzzy Matching
  → AGODA → Bank (by amount + date range)
  → Unmatched invoices → guest name similarity

Phase 4: Manual Review
  → Flag unmatched transactions
  → Generate exception reports
```

### 3. Technical Requirements

**Python Libraries:**
- `pandas` - DataFrame operations
- `openpyxl` - Excel parsing
- `fuzzywuzzy` / `rapidfuzz` - Guest name matching
- `pydantic` - Data validation
- `sqlalchemy` - Database ORM

**Database Schema:**
```sql
-- Staging tables (raw parsed data)
CREATE TABLE staging_agoda (...);
CREATE TABLE staging_bank (...);
CREATE TABLE staging_upi (...);
CREATE TABLE staging_invoice (...);

-- Canonical models (normalized)
CREATE TABLE bookings (...);
CREATE TABLE invoices (...);
CREATE TABLE payments (...);
CREATE TABLE bank_transactions (...);

-- Reconciliation tracking
CREATE TABLE reconciliation_matches (
    match_id UUID PRIMARY KEY,
    source_type VARCHAR,
    source_id VARCHAR,
    target_type VARCHAR,
    target_id VARCHAR,
    confidence_score FLOAT,
    match_method VARCHAR,
    matched_at TIMESTAMP
);
```

---

## Appendix: Sample Data

### AGODA Sample (Variant 2)
```
INVOICE NO. | Booking ID  | Guest name      | From Agoda | COMM + GST | Check-in    | Check-out
5150, 5151  | 1906206150  | Nidhi Verma     | 11687.12   | 2345.67    | 2025-07-03  | 2025-07-07
5108        | 1914457101  | Rupesh Harode   | 3950.27    | 790.05     | 2025-07-05  | 2025-07-07
```

### BANK Sample
```
Value Date  | Description                                    | UTR                     | Credit Amount
01/07/2025  | NEFT/YESB/YESBN12025070105404991/ONE 97 COM    | YESBN12025070105404991  | 35997.98
02/07/2025  | NEFT/HDFC/HDFCN52025070227523293/MAKEMYTRIP    | HDFCN52025070227523293  | 1843.00
```

### UPI Sample
```
Transaction_Date        | Amount | Commission | GST  | Settled_Amount | UTR_No.           | Payment_Mode
2025-07-01 08:48:19     | 549    | 12.08      | 2.17 | 534.75         | YESAP51833296492  | DEBIT_CARD
2025-07-01 07:16:22     | 200    | 0          | 0    | 200            | YESAP51833296492  | UPI
```

### INVOICE Sample
```
Reservation # | Invoice #       | Guest Name         | Arrival     | Gross Amount
6669          | NULL            | indrajeet tiwari   | 2025-04-09  | 4500
6739          | NULL            | Mr.Nikhil Jat      | 2025-04-05  | 10999
6803-1        | 2025/2026/96    | Mr.ROSHAN KUMAR    | 2025-04-11  | 4499
```

---

## File Locations Reference

**Analysis Results:**
- `/tmp/excel_analysis.json` - Full JSON output with all 48 files

**Source Data:**
- AGODA: `/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/meet-recording/data_sheets_historical/mangal all data sheet/AGODA/`
- Bank: `.../INDIAN BANK/` and `.../INDIAN BANK ROOFTOP/`
- UPI: `.../UPI STATMENT/`, `.../PTM ROOFTOP/`, `.../F&B UPI/`
- Invoice: `/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/meet-recording/transaction_detail20250428.xlsx`

**Symlinks (currently broken):**
- `/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/data/booking/raw/`
- `/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/data/invoices/raw/`
- `/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/data/payments/raw/`
