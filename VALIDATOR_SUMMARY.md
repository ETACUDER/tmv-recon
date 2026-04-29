# Tally Voucher Validation Layer

## Implementation Summary

Built minimal validation layer with 3 core validators:

### Files Created

1. **`src/tmv_recon/etl/validator.py`** (98 lines)
   - `validate_xml_wellformed()` - Parse XML with ElementTree
   - `validate_amount_balance()` - Sum AMOUNT fields, check = 0
   - `validate_ledger_exists()` - Lookup ledger in catalog

2. **`tests/test_validator.py`** (100 lines)
   - 3 test functions covering all validators
   - Uses temp files for isolation
   - All tests pass

3. **`scripts/generate_validation_report.py`** (148 lines)
   - Generates validation summary report
   - Tests production + sample data
   - Documents findings

4. **Sample Data** (for testing)
   - `data/tally/raw_xml/samples/sample_voucher.xml`
   - `data/tally/raw_xml/samples/sample_ledgers.xml`

### Report Generated

`data/recon/reports/validation_summary.txt` with findings:

- Production XML files have invalid characters (line 209, 2628)
- Validators work correctly on clean XML
- Sample voucher balance validation: PASSED
- Sample ledger lookup: PASSED

### Test Results

```
tests/test_validator.py::test_validate_xml_wellformed PASSED
tests/test_validator.py::test_validate_amount_balance PASSED
tests/test_validator.py::test_validate_ledger_exists PASSED
```

### Line Count

- Core validator: 98 lines
- Tests: 100 lines
- **Total core implementation: 198 lines**

### Notes

- SQLite deduplication skipped per requirements
- Production XML needs character sanitization before validation
- Validators are functional and tested on clean data
