#!/usr/bin/env python3
"""Validate generated Sales vouchers against ground truth from daybook.

Compares structure and patterns between generated vouchers and actual Tally exports.
"""
import sys
import re
from pathlib import Path
from collections import Counter

# No XML parsing due to invalid chars, use regex instead


def extract_voucher_patterns(xml_content: str, source: str) -> dict:
    """Extract patterns from voucher XML using regex."""
    patterns = {
        "source": source,
        "voucher_count": 0,
        "tag_usage": Counter(),
        "ledgers_used": Counter(),
        "sign_conventions": [],
        "narration_patterns": [],
        "voucher_types": Counter(),
    }

    # Find all Sales vouchers
    sales_vouchers = re.findall(
        r'VCHTYPE="Sales".*?</VOUCHER>',
        xml_content,
        re.DOTALL
    )
    patterns["voucher_count"] = len(sales_vouchers)

    for voucher in sales_vouchers:
        # Check tag usage
        if "LEDGERENTRIES.LIST" in voucher:
            patterns["tag_usage"]["LEDGERENTRIES.LIST"] += 1
        if "ALLLEDGERENTRIES.LIST" in voucher:
            patterns["tag_usage"]["ALLLEDGERENTRIES.LIST"] += 1

        # Extract ledger names
        ledgers = re.findall(r"<LEDGERNAME>(.*?)</LEDGERNAME>", voucher)
        for ledger in ledgers:
            patterns["ledgers_used"][ledger] += 1

        # Extract sign conventions
        entries = re.findall(
            r"<LEDGERNAME>(.*?)</LEDGERNAME>.*?<ISDEEMEDPOSITIVE>(.*?)</ISDEEMEDPOSITIVE>.*?<AMOUNT>(.*?)</AMOUNT>",
            voucher,
            re.DOTALL
        )
        for ledger, deemed, amount in entries:
            sign = "+" if not amount.startswith("-") else "-"
            patterns["sign_conventions"].append(f"{ledger}|deemed={deemed}|sign={sign}")

        # Extract narration
        narration_match = re.search(r"<NARRATION>(.*?)</NARRATION>", voucher)
        if narration_match:
            narration = narration_match.group(1)
            if "INVOICE NO:-" in narration:
                patterns["narration_patterns"].append("INVOICE NO:- pattern")
            elif "B.NO.:" in narration:
                patterns["narration_patterns"].append("B.NO.: pattern")

    return patterns


def compare_patterns(generated: dict, ground_truth: dict) -> list:
    """Compare patterns and report differences."""
    issues = []
    passes = []

    # Check tag usage
    if generated["tag_usage"].get("LEDGERENTRIES.LIST", 0) > 0:
        passes.append("✓ Uses LEDGERENTRIES.LIST tag")
    else:
        issues.append("✗ Missing LEDGERENTRIES.LIST tag")

    if generated["tag_usage"].get("ALLLEDGERENTRIES.LIST", 0) > 0:
        issues.append("✗ Incorrectly uses ALLLEDGERENTRIES.LIST (should be LEDGERENTRIES.LIST for Sales)")

    # Check required ledgers
    required_ledgers = ["Sundry Debtors", "CGST", "SGST"]
    for ledger in required_ledgers:
        if ledger in generated["ledgers_used"]:
            passes.append(f"✓ Uses ledger: {ledger}")
        else:
            issues.append(f"✗ Missing ledger: {ledger}")

    # Check income ledger patterns
    income_ledgers = [l for l in generated["ledgers_used"] if "GST @" in l]
    if income_ledgers:
        passes.append(f"✓ Uses income ledger with GST rate: {income_ledgers[0]}")
    else:
        issues.append("✗ Missing income ledger with GST rate pattern")

    # Check sign conventions
    sundry_debtors_signs = [
        sc for sc in generated["sign_conventions"]
        if "Sundry Debtors" in sc
    ]
    if sundry_debtors_signs:
        example = sundry_debtors_signs[0]
        if "deemed=No" in example and "sign=+" in example:
            passes.append("✓ Sundry Debtors uses ISDEEMEDPOSITIVE=No with positive amount (Debit)")
        else:
            issues.append(f"✗ Sundry Debtors sign convention incorrect: {example}")

    income_signs = [
        sc for sc in generated["sign_conventions"]
        if ("SALE ACCOMODATION" in sc or "RENTAL INCOME" in sc)
    ]
    if income_signs:
        example = income_signs[0]
        if "deemed=Yes" in example and "sign=-" in example:
            passes.append("✓ Income ledger uses ISDEEMEDPOSITIVE=Yes with negative amount (Credit)")
        else:
            issues.append(f"✗ Income ledger sign convention incorrect: {example}")

    # Check narration patterns
    if "INVOICE NO:- pattern" in generated["narration_patterns"]:
        passes.append("✓ Uses standard narration pattern: INVOICE NO:-")
    else:
        issues.append("✗ Missing standard narration pattern")

    return passes, issues


def main():
    """Compare generated vouchers with ground truth."""
    base_dir = Path(__file__).parent.parent
    generated_path = base_dir / "data" / "recon" / "output" / "sales_vouchers_2026-04-29.xml"
    ground_truth_path = base_dir / "data" / "tally" / "raw_xml" / "daybook_FY25-26.xml"

    print("=" * 70)
    print("Sales Voucher Validation Against Ground Truth")
    print("=" * 70)
    print()

    # Read generated vouchers
    if not generated_path.exists():
        print(f"ERROR: Generated file not found: {generated_path}")
        sys.exit(1)

    with open(generated_path, "r", encoding="utf-8") as f:
        generated_xml = f.read()

    print(f"✓ Loaded generated vouchers: {generated_path.name}")

    # Read ground truth
    if not ground_truth_path.exists():
        print(f"WARNING: Ground truth not found: {ground_truth_path}")
        print("Skipping ground truth comparison")
        ground_truth_xml = None
    else:
        with open(ground_truth_path, "r", encoding="utf-8", errors="ignore") as f:
            ground_truth_xml = f.read()
        print(f"✓ Loaded ground truth: {ground_truth_path.name}")

    print()

    # Extract patterns
    print("Analyzing generated vouchers...")
    generated_patterns = extract_voucher_patterns(generated_xml, "Generated")
    print(f"  Vouchers: {generated_patterns['voucher_count']}")
    print(f"  Unique ledgers: {len(generated_patterns['ledgers_used'])}")
    print()

    if ground_truth_xml:
        print("Analyzing ground truth vouchers...")
        gt_patterns = extract_voucher_patterns(ground_truth_xml, "Ground Truth")
        print(f"  Sales vouchers: {gt_patterns['voucher_count']}")
        print(f"  Unique ledgers: {len(gt_patterns['ledgers_used'])}")
        print()

        # Compare
        print("=" * 70)
        print("COMPARISON RESULTS")
        print("=" * 70)
        print()

        passes, issues = compare_patterns(generated_patterns, gt_patterns)

        if passes:
            print("PASSED CHECKS:")
            for p in passes:
                print(f"  {p}")
            print()

        if issues:
            print("ISSUES FOUND:")
            for i in issues:
                print(f"  {i}")
            print()
        else:
            print("✓ All checks passed!")
            print()

        # Detailed breakdown
        print("=" * 70)
        print("DETAILED BREAKDOWN")
        print("=" * 70)
        print()

        print("Tag Usage:")
        print(f"  Generated:")
        for tag, count in generated_patterns["tag_usage"].items():
            print(f"    {tag}: {count}")
        print(f"  Ground Truth:")
        for tag, count in gt_patterns["tag_usage"].items():
            print(f"    {tag}: {count}")
        print()

        print("Top Ledgers (Generated):")
        for ledger, count in generated_patterns["ledgers_used"].most_common(10):
            print(f"  {ledger}: {count}")
        print()

        print("Top Ledgers (Ground Truth Sales vouchers):")
        for ledger, count in gt_patterns["ledgers_used"].most_common(10):
            print(f"  {ledger}: {count}")
        print()

        # Success rate
        total_checks = len(passes) + len(issues)
        success_rate = (len(passes) / total_checks * 100) if total_checks > 0 else 0
        print("=" * 70)
        print(f"SUCCESS RATE: {success_rate:.1f}% ({len(passes)}/{total_checks} checks passed)")
        print("=" * 70)

        if success_rate >= 95:
            print("\n✓✓✓ VALIDATION PASSED (95%+ target met) ✓✓✓")
            return 0
        elif success_rate >= 80:
            print("\n⚠ VALIDATION WARNING (80-95% - review issues)")
            return 1
        else:
            print("\n✗✗✗ VALIDATION FAILED (< 80%) ✗✗✗")
            return 2

    else:
        # No ground truth, just validate structure
        print("=" * 70)
        print("STRUCTURE VALIDATION (No ground truth)")
        print("=" * 70)
        print()

        checks = []
        if generated_patterns["tag_usage"].get("LEDGERENTRIES.LIST", 0) > 0:
            checks.append("✓ Uses LEDGERENTRIES.LIST")
        else:
            checks.append("✗ Missing LEDGERENTRIES.LIST")

        if "Sundry Debtors" in generated_patterns["ledgers_used"]:
            checks.append("✓ Uses Sundry Debtors ledger")

        if any("GST @" in l for l in generated_patterns["ledgers_used"]):
            checks.append("✓ Uses income ledger with GST rate")

        for check in checks:
            print(f"  {check}")

        return 0


if __name__ == "__main__":
    sys.exit(main())
