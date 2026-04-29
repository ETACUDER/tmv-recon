"""Comprehensive tests for 3-stage matcher.

Tests exact matches, fuzzy matches, manual queue, edge cases.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal

from tmv_recon.etl.recon import (
    normalize_name,
    score_match,
    exact_match_invoice_booking,
    exact_match_payment_bank,
    fuzzy_match_invoice_booking,
    fuzzy_match_payment_invoice,
    classify_unmatched,
)


class TestNameNormalization:
    """Test name normalization per requirements §3.2."""

    def test_remove_titles(self):
        assert normalize_name("Mr. John Doe") == "John Doe"
        assert normalize_name("Mrs. Jane Smith") == "Jane Smith"
        assert normalize_name("Ms. Alice") == "Alice"
        assert normalize_name("Dr. Bob") == "Bob"

    def test_title_case(self):
        assert normalize_name("JOHN DOE") == "John Doe"
        assert normalize_name("jane smith") == "Jane Smith"

    def test_extra_whitespace(self):
        assert normalize_name("John  Doe") == "John Doe"
        assert normalize_name("  John Doe  ") == "John Doe"

    def test_edge_cases(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""
        assert normalize_name("   ") == ""


class TestConfidenceScoring:
    """Test confidence scoring function."""

    def test_perfect_match(self):
        row_a = pd.Series({
            'guest_name': 'John Doe',
            'date': datetime(2025, 1, 15),
            'amount': 5000.0
        })
        row_b = pd.Series({
            'guest_name': 'John Doe',
            'date': datetime(2025, 1, 15),
            'amount': 5000.0
        })
        score = score_match(row_a, row_b,
                            name_a='guest_name', name_b='guest_name',
                            date_a='date', date_b='date',
                            amount_a='amount', amount_b='amount')
        assert score == 0.9  # Per §3.2: name>0.8 + date + amount → 0.9

    def test_high_confidence_match(self):
        row_a = pd.Series({
            'guest_name': 'John Doe',
            'date': datetime(2025, 1, 15),
            'amount': 5000.0
        })
        row_b = pd.Series({
            'guest_name': 'John P. Doe',  # Slight variation
            'date': datetime(2025, 1, 16),  # 1 day apart
            'amount': 5050.0  # Within 1%
        })
        score = score_match(row_a, row_b,
                            name_a='guest_name', name_b='guest_name',
                            date_a='date', date_b='date',
                            amount_a='amount', amount_b='amount')
        assert score >= 0.7  # Should be high confidence

    def test_low_confidence_match(self):
        row_a = pd.Series({
            'guest_name': 'John Doe',
            'date': datetime(2025, 1, 15),
            'amount': 5000.0
        })
        row_b = pd.Series({
            'guest_name': 'Jane Smith',  # Different name
            'date': datetime(2025, 2, 15),  # 31 days apart
            'amount': 6000.0  # 20% different
        })
        score = score_match(row_a, row_b,
                            name_a='guest_name', name_b='guest_name',
                            date_a='date', date_b='date',
                            amount_a='amount', amount_b='amount')
        assert score < 0.6  # Should be below threshold


class TestStage1ExactMatches:
    """Test Stage 1: Exact matching."""

    def test_exact_invoice_booking_match(self):
        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'guest_name': 'John Doe',
                'gross_amount': 5000.0,
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            },
            {
                'invoice_no': '25-26/1235',
                'invoice_date': '2025-04-16',
                'guest_name': 'Jane Smith',
                'gross_amount': 3000.0,
                'arrival': '2025-04-15',
                'departure': '2025-04-17'
            }
        ])

        bookings = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'guest_name': 'John Doe',
                'checkin': '2025-04-14',
                'checkout': '2025-04-16',
                'settlement_amount': 5000.0
            }
        ])

        matches = exact_match_invoice_booking(invoices, bookings)

        assert len(matches) == 1
        assert matches.iloc[0]['invoice_no'] == '25-26/1234'
        assert matches.iloc[0]['confidence'] == 1.0
        assert matches.iloc[0]['match_stage'] == 'exact'

    def test_exact_payment_bank_match(self):
        payments = pd.DataFrame([
            {
                'txn_id': 'TXN001',
                'txn_dt': '2025-04-15 10:30:00',
                'amount_gross': 5000.0,
                'settled_amount': 4900.0,
                'utr': 'UTR123456789',
                'payment_mode': 'UPI'
            }
        ])

        bank = pd.DataFrame([
            {
                'utr_extracted': 'UTR123456789',
                'value_date': '2025-04-15',
                'credit': 4900.0,
                'description': 'PAYTM PAYMENT'
            }
        ])

        matches = exact_match_payment_bank(payments, bank)

        assert len(matches) == 1
        assert matches.iloc[0]['utr'] == 'UTR123456789'
        assert matches.iloc[0]['confidence'] == 1.0
        assert matches.iloc[0]['match_stage'] == 'exact'

    def test_no_match_when_key_missing(self):
        invoices = pd.DataFrame([
            {
                'invoice_no': None,
                'invoice_date': '2025-04-15',
                'guest_name': 'John Doe',
                'gross_amount': 5000.0,
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            }
        ])
        bookings = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'guest_name': 'John Doe',
                'checkin': '2025-04-14',
                'checkout': '2025-04-16',
                'settlement_amount': 5000.0
            }
        ])

        matches = exact_match_invoice_booking(invoices, bookings)
        assert len(matches) == 0


class TestStage2FuzzyMatches:
    """Test Stage 2: Fuzzy matching with Levenshtein."""

    def test_fuzzy_invoice_booking_name_match(self):
        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'guest_name': 'Mr. JOHN DOE',
                'gross_amount': 5000.0,
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            }
        ])

        bookings = pd.DataFrame([
            {
                'agoda_booking_id': 'AGODA123',
                'invoice_no': None,  # No invoice_no for exact match
                'guest_name': 'John P Doe',  # Slight variation
                'checkin': '2025-04-14',  # Same date
                'checkout': '2025-04-16',
                'settlement_amount': 5000.0  # Same amount
            }
        ])

        matches = fuzzy_match_invoice_booking(invoices, bookings, already_matched=set())

        assert len(matches) == 1
        assert matches.iloc[0]['invoice_no'] == '25-26/1234'
        assert matches.iloc[0]['match_stage'] == 'fuzzy'
        assert matches.iloc[0]['confidence'] >= 0.6

    def test_fuzzy_payment_invoice_date_window(self):
        payments = pd.DataFrame([
            {
                'txn_id': 'TXN001',
                'txn_dt': '2025-04-17',  # 2 days after invoice
                'amount_gross': 5000.0,
                'settled_amount': 4900.0,
                'payment_mode': 'UPI',
                'pos_guest_name': 'JOHN DOE'
            }
        ])

        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'guest_name': 'Mr. John Doe',
                'gross_amount': 5000.0
            }
        ])

        matches = fuzzy_match_payment_invoice(payments, invoices, already_matched=set())

        assert len(matches) == 1
        assert matches.iloc[0]['txn_id'] == 'TXN001'
        assert matches.iloc[0]['invoice_no'] == '25-26/1234'
        assert matches.iloc[0]['confidence'] >= 0.6

    def test_fuzzy_rejects_poor_match(self):
        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'guest_name': 'John Doe',
                'gross_amount': 5000.0,
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            }
        ])

        bookings = pd.DataFrame([
            {
                'agoda_booking_id': 'AGODA123',
                'invoice_no': None,
                'guest_name': 'Completely Different Name',
                'checkin': '2025-05-01',  # Too far apart (17 days)
                'checkout': '2025-05-03',
                'settlement_amount': 10000.0  # 100% difference
            }
        ])

        matches = fuzzy_match_invoice_booking(invoices, bookings, already_matched=set())
        assert len(matches) == 0  # Should not match

    def test_fuzzy_keeps_best_match_only(self):
        """When multiple candidates match, keep only the best one."""
        payments = pd.DataFrame([
            {
                'txn_id': 'TXN001',
                'txn_dt': '2025-04-15',
                'amount_gross': 5000.0,
                'pos_guest_name': 'John Doe'
            }
        ])

        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'guest_name': 'John Doe',
                'gross_amount': 5000.0
            },
            {
                'invoice_no': '25-26/1235',
                'invoice_date': '2025-04-14',
                'guest_name': 'John P. Doe',
                'gross_amount': 5050.0
            }
        ])

        matches = fuzzy_match_payment_invoice(payments, invoices, already_matched=set())

        assert len(matches) == 1  # Only best match
        assert matches.iloc[0]['confidence'] >= 0.6


class TestStage3ManualQueue:
    """Test Stage 3: Manual review queue with reason codes."""

    def test_classify_missing_join_key(self):
        df = pd.DataFrame([
            {'invoice_no': None, 'gross_amount': 5000.0, 'invoice_date': '2025-04-15'},
            {'invoice_no': '', 'gross_amount': 3000.0, 'invoice_date': '2025-04-16'},
        ])

        result = classify_unmatched(df, 'invoice',
                                     key_col='invoice_no',
                                     amount_col='gross_amount',
                                     date_col='invoice_date')

        assert len(result) == 2
        assert 'NO_JOIN_KEY' in result.iloc[0]['unmatched_reason']
        assert 'NO_JOIN_KEY' in result.iloc[1]['unmatched_reason']

    def test_classify_amount_missing(self):
        df = pd.DataFrame([
            {'invoice_no': '25-26/1234', 'gross_amount': 0, 'invoice_date': '2025-04-15'},
            {'invoice_no': '25-26/1235', 'gross_amount': None, 'invoice_date': '2025-04-16'},
        ])

        result = classify_unmatched(df, 'invoice',
                                     key_col='invoice_no',
                                     amount_col='gross_amount',
                                     date_col='invoice_date')

        assert 'AMOUNT_MISSING' in result.iloc[0]['unmatched_reason']
        assert 'AMOUNT_MISSING' in result.iloc[1]['unmatched_reason']

    def test_classify_date_out_range(self):
        old_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
        df = pd.DataFrame([
            {'invoice_no': '25-26/1234', 'gross_amount': 5000.0, 'invoice_date': old_date},
        ])

        result = classify_unmatched(df, 'invoice',
                                     key_col='invoice_no',
                                     amount_col='gross_amount',
                                     date_col='invoice_date')

        assert 'DATE_OUT_RANGE' in result.iloc[0]['unmatched_reason']

    def test_classify_no_match_found(self):
        recent_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        df = pd.DataFrame([
            {'invoice_no': '25-26/1234', 'gross_amount': 5000.0, 'invoice_date': recent_date},
        ])

        result = classify_unmatched(df, 'invoice',
                                     key_col='invoice_no',
                                     amount_col='gross_amount',
                                     date_col='invoice_date')

        assert result.iloc[0]['unmatched_reason'] == 'NO_MATCH_FOUND'


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_dataframes(self):
        empty = pd.DataFrame()
        assert len(exact_match_invoice_booking(empty, empty)) == 0
        assert len(exact_match_payment_bank(empty, empty)) == 0
        assert len(fuzzy_match_invoice_booking(empty, empty, set())) == 0
        assert len(fuzzy_match_payment_invoice(empty, empty, set())) == 0

    def test_amount_tolerance_boundary(self):
        """Test ±1% tolerance boundary."""
        # Exactly at 1% boundary (should match)
        score_within = score_match(
            pd.Series({'guest_name': 'John Doe', 'date': datetime(2025, 1, 1), 'amount': 10000.0}),
            pd.Series({'guest_name': 'John Doe', 'date': datetime(2025, 1, 1), 'amount': 10100.0}),
            name_a='guest_name', name_b='guest_name',
            date_a='date', date_b='date',
            amount_a='amount', amount_b='amount'
        )
        # With perfect name, perfect date, and amount within tolerance, should be 0.9
        assert score_within == 0.9

        # Outside 5% tolerance (should score lower)
        score_outside = score_match(
            pd.Series({'guest_name': 'John Doe', 'date': datetime(2025, 1, 1), 'amount': 10000.0}),
            pd.Series({'guest_name': 'John Doe', 'date': datetime(2025, 1, 1), 'amount': 11000.0}),
            name_a='guest_name', name_b='guest_name',
            date_a='date', date_b='date',
            amount_a='amount', amount_b='amount'
        )
        # Amount is 10% off, amount_match = False, name+date match → 0.7
        assert score_outside == 0.7

    def test_date_window_boundaries(self):
        """Test ±3 day invoice window, ±7 day payment window."""
        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'guest_name': 'John Doe',
                'gross_amount': 5000.0,
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            }
        ])

        # Within 3 days
        bookings_within = pd.DataFrame([
            {
                'agoda_booking_id': 'AGODA123',
                'invoice_no': None,
                'guest_name': 'John Doe',
                'checkin': '2025-04-17',  # 3 days after arrival
                'checkout': '2025-04-18',
                'settlement_amount': 5000.0
            }
        ])

        matches_within = fuzzy_match_invoice_booking(invoices, bookings_within, set())
        assert len(matches_within) == 1

        # Outside 3 days
        bookings_outside = pd.DataFrame([
            {
                'agoda_booking_id': 'AGODA124',
                'invoice_no': None,
                'guest_name': 'John Doe',
                'checkin': '2025-04-20',  # 6 days after arrival
                'checkout': '2025-04-21',
                'settlement_amount': 5000.0
            }
        ])

        matches_outside = fuzzy_match_invoice_booking(invoices, bookings_outside, set())
        assert len(matches_outside) == 0

    def test_duplicate_keys_handled(self):
        """Test handling of duplicate invoice_no."""
        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'gross_amount': 5000.0,
                'guest_name': 'John',
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            },
            {
                'invoice_no': '25-26/1234',
                'invoice_date': '2025-04-15',
                'gross_amount': 5000.0,
                'guest_name': 'John',
                'arrival': '2025-04-14',
                'departure': '2025-04-16'
            },
        ])

        bookings = pd.DataFrame([
            {
                'invoice_no': '25-26/1234',
                'guest_name': 'John',
                'checkin': '2025-04-14',
                'checkout': '2025-04-16',
                'settlement_amount': 5000.0
            }
        ])

        matches = exact_match_invoice_booking(invoices, bookings)
        assert len(matches) == 2  # Both invoices match

    def test_special_characters_in_names(self):
        """Test names with special characters."""
        assert normalize_name("O'Brien") == "O'Brien"
        assert normalize_name("Jean-Paul") == "Jean-Paul"
        assert normalize_name("Müller") == "Müller"


class TestKnownMatches:
    """Test with known good matches from actual data."""

    def test_alamelu_senthilkumar_match(self):
        """Real example from bookings.csv."""
        invoices = pd.DataFrame([
            {
                'invoice_no': '25-26/2370',
                'invoice_date': '2025-09-01',
                'guest_name': 'ALAMELU SENTHILKUMAR',
                'gross_amount': 11760.0,
                'arrival': '2025-09-01',
                'departure': '2025-09-06'
            }
        ])

        bookings = pd.DataFrame([
            {
                'agoda_booking_id': '1637618404',
                'invoice_no': '25-26/2370',
                'guest_name': 'ALAMELU SENTHILKUMAR',
                'checkin': '2025-09-01',
                'checkout': '2025-09-06',
                'settlement_amount': 80280.25
            }
        ])

        matches = exact_match_invoice_booking(invoices, bookings)
        assert len(matches) == 1
        assert matches.iloc[0]['confidence'] == 1.0

    def test_payment_bank_utr_match(self):
        """Real UPI payment match."""
        payments = pd.DataFrame([
            {
                'txn_id': '20251201010840000202321030660583916',
                'txn_dt': '2025-12-01 18:34:31',
                'amount_gross': 7500.0,
                'settled_amount': 7500.0,
                'utr': 'YESAP53365113871',
                'payment_mode': 'UPI'
            }
        ])

        bank = pd.DataFrame([
            {
                'utr_extracted': 'YESAP53365113871',
                'value_date': '2025-12-02',
                'credit': 7500.0,
                'description': 'UPI PAYTM'
            }
        ])

        matches = exact_match_payment_bank(payments, bank)
        assert len(matches) == 1
        assert matches.iloc[0]['utr'] == 'YESAP53365113871'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
