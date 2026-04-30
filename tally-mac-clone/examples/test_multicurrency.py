"""Test multi-currency support."""
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tally_mac_clone.database import db

def test_multicurrency():
    """Test currency and exchange rate functionality."""

    print("Testing Multi-Currency Support\n" + "="*50)

    # Create currencies
    print("\n1. Creating currencies...")
    usd = db.create_currency(
        code="USD",
        symbol="$",
        name="US Dollar",
        decimal_places=2,
        is_base=True
    )
    print(f"   Created: {usd.code} - {usd.name} ({usd.symbol})")

    eur = db.create_currency(
        code="EUR",
        symbol="€",
        name="Euro",
        decimal_places=2,
        is_base=False
    )
    print(f"   Created: {eur.code} - {eur.name} ({eur.symbol})")

    inr = db.create_currency(
        code="INR",
        symbol="₹",
        name="Indian Rupee",
        decimal_places=2,
        is_base=False
    )
    print(f"   Created: {inr.code} - {inr.name} ({inr.symbol})")

    # List currencies
    print("\n2. Listing all currencies...")
    currencies = db.list_currencies()
    for c in currencies:
        base_flag = " [BASE]" if c.is_base else ""
        print(f"   {c.code}: {c.name} ({c.symbol}){base_flag}")

    # Create exchange rates
    print("\n3. Creating exchange rates...")
    today = date(2026, 4, 30)

    eur_rate = db.create_exchange_rate(
        currency_id=eur.id,
        date=today,
        rate=0.92
    )
    print(f"   EUR rate on {today}: {eur_rate.rate} USD")

    inr_rate = db.create_exchange_rate(
        currency_id=inr.id,
        date=today,
        rate=83.50
    )
    print(f"   INR rate on {today}: {inr_rate.rate} USD")

    # Get exchange rates
    print("\n4. Retrieving exchange rates...")
    eur_retrieved = db.get_exchange_rate("EUR", today)
    print(f"   EUR rate on {today}: {eur_retrieved}")

    inr_retrieved = db.get_exchange_rate("INR", today)
    print(f"   INR rate on {today}: {inr_retrieved}")

    # Test non-existent rate
    old_date = date(2026, 1, 1)
    old_rate = db.get_exchange_rate("EUR", old_date)
    print(f"   EUR rate on {old_date}: {old_rate} (should be None)")

    # Create historical rate
    print("\n5. Creating historical rate...")
    historical = db.create_exchange_rate(
        currency_id=eur.id,
        date=date(2026, 1, 1),
        rate=0.95
    )
    print(f"   EUR rate on {historical.date}: {historical.rate}")

    # Test nearest rate lookup
    print("\n6. Testing nearest rate lookup...")
    mid_date = date(2026, 2, 15)
    mid_rate = db.get_exchange_rate("EUR", mid_date)
    print(f"   EUR rate on {mid_date}: {mid_rate} (should return 0.95 from Jan 1)")

    current_rate = db.get_exchange_rate("EUR", date(2026, 5, 1))
    print(f"   EUR rate on 2026-05-01: {current_rate} (should return 0.92 from Apr 30)")

    print("\n" + "="*50)
    print("Multi-currency support test completed successfully!")

    # Currency by code lookup
    print("\n7. Testing currency lookup...")
    usd_lookup = db.get_currency_by_code("USD")
    print(f"   Found: {usd_lookup.code} - {usd_lookup.name}")

    # Exchange rate history
    print("\n8. Exchange rate history for EUR...")
    eur_history = db.list_exchange_rates(eur.id)
    for rate in eur_history:
        print(f"   {rate.date}: {rate.rate}")

if __name__ == "__main__":
    # Initialize database
    db.create_tables()

    # Run test
    test_multicurrency()
