"""Ground truth validation - compare generated vouchers against actual Tally data.

Parses Tally daybook XML and generated XML to validate:
- Voucher type match (exact)
- Ledger names (exact string match)
- Amounts (within ₹1 tolerance)
- Narration patterns (regex match)

Target: 95%+ structural similarity.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re
import csv


@dataclass
class LedgerEntry:
    """Single ledger entry in a voucher."""
    ledger_name: str
    amount: Decimal
    is_deemed_positive: str  # "Yes" | "No"
    is_party_ledger: bool = False


@dataclass
class TallyVoucher:
    """Parsed Tally voucher from daybook XML."""
    guid: str
    voucher_type: str  # Sales, Journal, Purchase, Receipt, Credit Note
    voucher_number: str
    date: date
    narration: str
    party_ledger_name: str
    reference: str
    ledger_entries: List[LedgerEntry] = field(default_factory=list)

    # For matching
    gross_amount: Optional[Decimal] = None
    invoice_no_pattern: Optional[str] = None  # extracted from narration/reference

    @property
    def total_debit(self) -> Decimal:
        """Sum of all debit entries."""
        total = Decimal(0)
        for entry in self.ledger_entries:
            # Positive amount means debit
            if entry.amount > 0:
                total += entry.amount
        return total

    @property
    def total_credit(self) -> Decimal:
        """Sum of all credit entries."""
        total = Decimal(0)
        for entry in self.ledger_entries:
            # Negative amount means credit
            if entry.amount < 0:
                total += abs(entry.amount)
        return total

    @property
    def ledger_names_sorted(self) -> List[str]:
        """Sorted list of ledger names for comparison."""
        return sorted([e.ledger_name for e in self.ledger_entries])


@dataclass
class ComparisonResult:
    """Result of comparing actual vs generated voucher."""
    actual_voucher_no: str
    generated_voucher_no: str
    actual_date: date
    generated_date: date
    match_score: float  # 0.0 - 1.0
    voucher_type_match: bool
    ledger_names_match: bool
    amount_match: bool
    narration_pattern_match: bool
    differences: List[str] = field(default_factory=list)

    @property
    def is_acceptable(self) -> bool:
        """Check if match meets acceptance criteria."""
        return self.match_score >= 0.95


def parse_tally_date(date_str: str) -> date:
    """Parse Tally date format YYYYMMDD."""
    if not date_str or len(date_str) != 8:
        return date(1900, 1, 1)
    return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))


def parse_amount(amount_str: str) -> Decimal:
    """Parse amount string to Decimal."""
    if not amount_str:
        return Decimal(0)
    # Remove any non-numeric except decimal point and minus
    cleaned = re.sub(r'[^\d.-]', '', amount_str)
    return Decimal(cleaned) if cleaned else Decimal(0)


def extract_invoice_no(text: str) -> Optional[str]:
    """Extract invoice number from narration/reference."""
    if not text:
        return None

    # Pattern: 25-26/#### or INVOICE NO:-25-26/####
    patterns = [
        r'(\d{2}-\d{2}/\d{4,5})',  # Direct invoice number
        r'INVOICE NO[:\.\-\s]*(\d{2}-\d{2}/\d{4,5})',  # With prefix
        r'INV(?:OICE)?[:\.\-\s]*(\d{2}-\d{2}/\d{4,5})',  # INV prefix
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def clean_tally_xml(content: str) -> str:
    """Clean Tally XML from invalid characters and entities.

    Tally exports sometimes contain:
    - Invalid character references like &#4;
    - Control characters (\\x00-\\x1F except \\t, \\n, \\r)
    """
    # Remove control characters except tab, newline, carriage return
    cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', content)

    # Remove invalid character entity references (&#0; to &#31; except &#9;, &#10;, &#13;)
    cleaned = re.sub(r'&#([0-8]|1[1-2]|1[4-9]|2[0-9]|3[0-1]);', '', cleaned)

    return cleaned


def parse_tally_vouchers(xml_path: str) -> List[TallyVoucher]:
    """Parse Tally daybook XML export.

    Handles both LEDGERENTRIES.LIST (Sales, Purchase, Credit Note)
    and ALLLEDGERENTRIES.LIST (Journal, Receipt).
    """
    # Read and clean XML (Tally exports often have control characters)
    with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
        xml_content = f.read()

    xml_content = clean_tally_xml(xml_content)

    # Parse cleaned XML
    root = ET.fromstring(xml_content)

    vouchers = []

    # Find all VOUCHER elements
    for voucher_elem in root.findall('.//VOUCHER'):
        try:
            # Basic voucher info
            guid = voucher_elem.find('GUID')
            guid = guid.text if guid is not None else ""

            vch_type = voucher_elem.get('VCHTYPE', '')

            date_elem = voucher_elem.find('DATE')
            vch_date = parse_tally_date(date_elem.text if date_elem is not None else '')

            vch_number_elem = voucher_elem.find('VOUCHERNUMBER')
            vch_number = vch_number_elem.text if vch_number_elem is not None else ""

            narration_elem = voucher_elem.find('NARRATION')
            narration = narration_elem.text if narration_elem is not None else ""

            party_ledger_elem = voucher_elem.find('PARTYLEDGERNAME')
            party_ledger = party_ledger_elem.text if party_ledger_elem is not None else ""

            reference_elem = voucher_elem.find('REFERENCE')
            reference = reference_elem.text if reference_elem is not None else ""

            # Parse ledger entries (try both types)
            ledger_entries = []

            # Try LEDGERENTRIES.LIST first (Sales, Purchase, Credit Note)
            for entry_elem in voucher_elem.findall('.//LEDGERENTRIES.LIST'):
                ledger_name_elem = entry_elem.find('LEDGERNAME')
                if ledger_name_elem is None:
                    continue

                ledger_name = ledger_name_elem.text

                amount_elem = entry_elem.find('AMOUNT')
                amount = parse_amount(amount_elem.text if amount_elem is not None else '0')

                is_deemed_pos_elem = entry_elem.find('ISDEEMEDPOSITIVE')
                is_deemed_positive = is_deemed_pos_elem.text if is_deemed_pos_elem is not None else "No"

                is_party_elem = entry_elem.find('ISPARTYLEDGER')
                is_party = (is_party_elem.text if is_party_elem is not None else "No") == "Yes"

                ledger_entries.append(LedgerEntry(
                    ledger_name=ledger_name,
                    amount=amount,
                    is_deemed_positive=is_deemed_positive,
                    is_party_ledger=is_party
                ))

            # Try ALLLEDGERENTRIES.LIST (Journal, Receipt)
            if not ledger_entries:
                for entry_elem in voucher_elem.findall('.//ALLLEDGERENTRIES.LIST'):
                    ledger_name_elem = entry_elem.find('LEDGERNAME')
                    if ledger_name_elem is None:
                        continue

                    ledger_name = ledger_name_elem.text

                    amount_elem = entry_elem.find('AMOUNT')
                    amount = parse_amount(amount_elem.text if amount_elem is not None else '0')

                    is_deemed_pos_elem = entry_elem.find('ISDEEMEDPOSITIVE')
                    is_deemed_positive = is_deemed_pos_elem.text if is_deemed_pos_elem is not None else "No"

                    is_party_elem = entry_elem.find('ISPARTYLEDGER')
                    is_party = (is_party_elem.text if is_party_elem is not None else "No") == "Yes"

                    ledger_entries.append(LedgerEntry(
                        ledger_name=ledger_name,
                        amount=amount,
                        is_deemed_positive=is_deemed_positive,
                        is_party_ledger=is_party
                    ))

            # Calculate gross amount (total debit or highest amount)
            gross_amount = None
            if ledger_entries:
                amounts = [abs(e.amount) for e in ledger_entries]
                gross_amount = max(amounts)

            # Extract invoice number from narration or reference
            invoice_no = extract_invoice_no(narration) or extract_invoice_no(reference) or extract_invoice_no(vch_number)

            voucher = TallyVoucher(
                guid=guid,
                voucher_type=vch_type,
                voucher_number=vch_number,
                date=vch_date,
                narration=narration,
                party_ledger_name=party_ledger,
                reference=reference,
                ledger_entries=ledger_entries,
                gross_amount=gross_amount,
                invoice_no_pattern=invoice_no
            )

            vouchers.append(voucher)

        except Exception as e:
            # Skip malformed vouchers
            continue

    return vouchers


def parse_generated_vouchers(xml_path: str) -> List[TallyVoucher]:
    """Parse generated voucher XML (same structure as Tally export).

    Uses same parser as parse_tally_vouchers since structure is identical.
    """
    return parse_tally_vouchers(xml_path)


def compare_narrations(actual: str, generated: str) -> bool:
    """Compare narration using pattern matching.

    Allows for minor variations in formatting, whitespace, and case.
    """
    if not actual and not generated:
        return True
    if not actual or not generated:
        return False

    # Normalize both
    def normalize(text: str) -> str:
        text = text.upper()
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    actual_norm = normalize(actual)
    generated_norm = normalize(generated)

    # Exact match after normalization
    if actual_norm == generated_norm:
        return True

    # Check if key patterns match (invoice number, amounts)
    actual_invoice = extract_invoice_no(actual)
    generated_invoice = extract_invoice_no(generated)

    if actual_invoice and generated_invoice:
        return actual_invoice == generated_invoice

    # Fuzzy similarity check (at least 80% of words match)
    actual_words = set(actual_norm.split())
    generated_words = set(generated_norm.split())

    if actual_words and generated_words:
        intersection = actual_words & generated_words
        union = actual_words | generated_words
        similarity = len(intersection) / len(union)
        return similarity >= 0.8

    return False


def compare_vouchers(actual: TallyVoucher, generated: TallyVoucher) -> ComparisonResult:
    """Compare actual vs generated voucher and calculate similarity score.

    Scoring:
    - Voucher type match: 25%
    - Ledger names match: 35%
    - Amount match: 30%
    - Narration pattern: 10%
    """
    differences = []
    score_components = []

    # 1. Voucher type (25%)
    voucher_type_match = actual.voucher_type == generated.voucher_type
    if voucher_type_match:
        score_components.append(0.25)
    else:
        differences.append(f"Voucher type: {actual.voucher_type} != {generated.voucher_type}")

    # 2. Ledger names (35%)
    actual_ledgers = actual.ledger_names_sorted
    generated_ledgers = generated.ledger_names_sorted

    ledger_names_match = actual_ledgers == generated_ledgers
    if ledger_names_match:
        score_components.append(0.35)
    else:
        # Partial credit for partial match
        matching_ledgers = set(actual_ledgers) & set(generated_ledgers)
        all_ledgers = set(actual_ledgers) | set(generated_ledgers)
        if all_ledgers:
            partial_score = 0.35 * (len(matching_ledgers) / len(all_ledgers))
            score_components.append(partial_score)

        missing = set(actual_ledgers) - set(generated_ledgers)
        extra = set(generated_ledgers) - set(actual_ledgers)
        if missing:
            differences.append(f"Missing ledgers: {', '.join(missing)}")
        if extra:
            differences.append(f"Extra ledgers: {', '.join(extra)}")

    # 3. Amount match (30%)
    amount_match = False
    actual_total = actual.total_debit
    generated_total = generated.total_debit

    amount_diff = abs(actual_total - generated_total)
    if amount_diff <= Decimal('1.0'):  # Within ₹1 tolerance
        amount_match = True
        score_components.append(0.30)
    else:
        # Partial credit based on percentage difference
        if actual_total > 0:
            pct_diff = float(amount_diff / actual_total)
            if pct_diff <= 0.05:  # Within 5%
                score_components.append(0.30 * (1 - pct_diff / 0.05))
        differences.append(f"Amount: {actual_total} != {generated_total} (diff: ₹{amount_diff})")

    # 4. Narration pattern (10%)
    narration_match = compare_narrations(actual.narration, generated.narration)
    if narration_match:
        score_components.append(0.10)
    else:
        differences.append(f"Narration: '{actual.narration}' != '{generated.narration}'")

    total_score = sum(score_components)

    return ComparisonResult(
        actual_voucher_no=actual.voucher_number,
        generated_voucher_no=generated.voucher_number,
        actual_date=actual.date,
        generated_date=generated.date,
        match_score=total_score,
        voucher_type_match=voucher_type_match,
        ledger_names_match=ledger_names_match,
        amount_match=amount_match,
        narration_pattern_match=narration_match,
        differences=differences
    )


def find_best_match(
    actual_voucher: TallyVoucher,
    generated_vouchers: List[TallyVoucher],
    used_indices: set
) -> Tuple[Optional[TallyVoucher], float, int]:
    """Find best matching generated voucher for actual voucher.

    Matching strategy:
    1. Invoice number exact match (if available)
    2. Amount + date within window
    3. Highest similarity score

    Returns: (best_match, score, index) or (None, 0.0, -1)
    """
    if not generated_vouchers:
        return None, 0.0, -1

    best_match = None
    best_score = 0.0
    best_index = -1

    # Try invoice number match first
    if actual_voucher.invoice_no_pattern:
        for i, gen_voucher in enumerate(generated_vouchers):
            if i in used_indices:
                continue
            if gen_voucher.invoice_no_pattern == actual_voucher.invoice_no_pattern:
                comparison = compare_vouchers(actual_voucher, gen_voucher)
                if comparison.match_score > best_score:
                    best_match = gen_voucher
                    best_score = comparison.match_score
                    best_index = i

    # If no good invoice match, try amount + date
    if best_score < 0.8 and actual_voucher.gross_amount:
        for i, gen_voucher in enumerate(generated_vouchers):
            if i in used_indices:
                continue

            # Amount within ₹1
            if gen_voucher.gross_amount:
                amount_diff = abs(actual_voucher.gross_amount - gen_voucher.gross_amount)
                if amount_diff <= Decimal('1.0'):
                    # Date within ±3 days
                    date_diff = abs((actual_voucher.date - gen_voucher.date).days)
                    if date_diff <= 3:
                        comparison = compare_vouchers(actual_voucher, gen_voucher)
                        if comparison.match_score > best_score:
                            best_match = gen_voucher
                            best_score = comparison.match_score
                            best_index = i

    # Fallback: highest score regardless
    if best_score < 0.5:
        for i, gen_voucher in enumerate(generated_vouchers):
            if i in used_indices:
                continue
            comparison = compare_vouchers(actual_voucher, gen_voucher)
            if comparison.match_score > best_score:
                best_match = gen_voucher
                best_score = comparison.match_score
                best_index = i

    return best_match, best_score, best_index


def generate_diff_report(
    comparisons: List[ComparisonResult],
    actual_vouchers: List[TallyVoucher],
    generated_vouchers: List[TallyVoucher],
    output_path: str
):
    """Generate CSV report with comparison results."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'Actual Voucher No',
            'Generated Voucher No',
            'Actual Date',
            'Generated Date',
            'Match Score',
            'Voucher Type Match',
            'Ledger Names Match',
            'Amount Match',
            'Narration Match',
            'Differences'
        ])

        # Data rows
        for comp in comparisons:
            writer.writerow([
                comp.actual_voucher_no,
                comp.generated_voucher_no,
                comp.actual_date.strftime('%Y-%m-%d'),
                comp.generated_date.strftime('%Y-%m-%d'),
                f"{comp.match_score:.2%}",
                'Yes' if comp.voucher_type_match else 'No',
                'Yes' if comp.ledger_names_match else 'No',
                'Yes' if comp.amount_match else 'No',
                'Yes' if comp.narration_pattern_match else 'No',
                ' | '.join(comp.differences)
            ])


def generate_summary_report(
    comparisons: List[ComparisonResult],
    actual_vouchers: List[TallyVoucher],
    generated_vouchers: List[TallyVoucher],
    output_path: str
):
    """Generate text summary of comparison results."""
    total_actual = len(actual_vouchers)
    total_generated = len(generated_vouchers)
    total_matched = len(comparisons)

    # Calculate match rates
    voucher_type_matches = sum(1 for c in comparisons if c.voucher_type_match)
    ledger_name_matches = sum(1 for c in comparisons if c.ledger_names_match)
    amount_matches = sum(1 for c in comparisons if c.amount_match)
    narration_matches = sum(1 for c in comparisons if c.narration_pattern_match)
    acceptable_matches = sum(1 for c in comparisons if c.is_acceptable)

    avg_score = sum(c.match_score for c in comparisons) / total_matched if total_matched > 0 else 0

    # Voucher type distribution
    actual_type_dist = {}
    for v in actual_vouchers:
        actual_type_dist[v.voucher_type] = actual_type_dist.get(v.voucher_type, 0) + 1

    generated_type_dist = {}
    for v in generated_vouchers:
        generated_type_dist[v.voucher_type] = generated_type_dist.get(v.voucher_type, 0) + 1

    # Generate report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GROUND TRUTH VALIDATION REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("OVERVIEW\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total actual vouchers:     {total_actual}\n")
        f.write(f"Total generated vouchers:  {total_generated}\n")
        f.write(f"Matched vouchers:          {total_matched}\n")
        f.write(f"Unmatched actual:          {total_actual - total_matched}\n")
        f.write(f"Unmatched generated:       {total_generated - total_matched}\n")
        f.write(f"\n")

        f.write("MATCH QUALITY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Average match score:       {avg_score:.2%}\n")
        f.write(f"Acceptable matches (≥95%): {acceptable_matches} ({acceptable_matches/total_matched*100:.1f}%)\n")
        f.write(f"\n")

        f.write("COMPONENT MATCH RATES\n")
        f.write("-" * 80 + "\n")
        if total_matched > 0:
            f.write(f"Voucher type:    {voucher_type_matches}/{total_matched} ({voucher_type_matches/total_matched*100:.1f}%) [Target: 95%]\n")
            f.write(f"Ledger names:    {ledger_name_matches}/{total_matched} ({ledger_name_matches/total_matched*100:.1f}%) [Target: 100%]\n")
            f.write(f"Amounts (±₹1):   {amount_matches}/{total_matched} ({amount_matches/total_matched*100:.1f}%) [Target: 98%]\n")
            f.write(f"Narration:       {narration_matches}/{total_matched} ({narration_matches/total_matched*100:.1f}%) [Target: 95%]\n")
        f.write(f"\n")

        f.write("VOUCHER TYPE DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Type':<20} {'Actual':>10} {'Generated':>10} {'Match':>10}\n")
        f.write("-" * 80 + "\n")

        all_types = set(actual_type_dist.keys()) | set(generated_type_dist.keys())
        for vtype in sorted(all_types):
            actual_count = actual_type_dist.get(vtype, 0)
            gen_count = generated_type_dist.get(vtype, 0)
            match_status = "✓" if actual_count == gen_count else "✗"
            f.write(f"{vtype:<20} {actual_count:>10} {gen_count:>10} {match_status:>10}\n")

        f.write(f"\n")
        f.write("ACCEPTANCE CRITERIA\n")
        f.write("-" * 80 + "\n")

        # Check acceptance criteria
        criteria_met = []
        if total_matched > 0:
            vtype_rate = voucher_type_matches / total_matched
            ledger_rate = ledger_name_matches / total_matched
            amount_rate = amount_matches / total_matched
            narration_rate = narration_matches / total_matched

            criteria_met.append(("Voucher type match ≥95%", vtype_rate >= 0.95, f"{vtype_rate:.1%}"))
            criteria_met.append(("Ledger name match 100%", ledger_rate >= 1.0, f"{ledger_rate:.1%}"))
            criteria_met.append(("Amount match ≥98%", amount_rate >= 0.98, f"{amount_rate:.1%}"))
            criteria_met.append(("Narration match ≥95%", narration_rate >= 0.95, f"{narration_rate:.1%}"))

        for criterion, met, actual in criteria_met:
            status = "✓ PASS" if met else "✗ FAIL"
            f.write(f"{status:8} {criterion:30} (Actual: {actual})\n")

        f.write(f"\n")
        f.write("=" * 80 + "\n")


def filter_vouchers_by_date(
    vouchers: List[TallyVoucher],
    start_date: date,
    end_date: date
) -> List[TallyVoucher]:
    """Filter vouchers by date range."""
    return [v for v in vouchers if start_date <= v.date <= end_date]
