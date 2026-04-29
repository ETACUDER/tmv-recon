"""Generate sample Journal vouchers for payment settlements."""
from datetime import date
from tmv_recon.tally.voucher_generators import generate_journal_voucher, vouchers_envelope

# Sample payment data
payments = [
    {
        "payment_amount": 1500.0,
        "invoice_no": "25-26/6450",
        "payment_mode": "UPI",
        "guest_name": "Rajesh Kumar",
        "voucher_date": date(2026, 4, 15),
    },
    {
        "payment_amount": 2300.50,
        "invoice_no": "25-26/6451",
        "payment_mode": "CARD",
        "guest_name": "Priya Sharma",
        "voucher_date": date(2026, 4, 16),
    },
    {
        "payment_amount": 3200.0,
        "invoice_no": "25-26/6452",
        "payment_mode": "TPP",
        "guest_name": "John Doe",
        "voucher_date": date(2026, 4, 17),
    },
    {
        "payment_amount": 1850.75,
        "invoice_no": "25-26/6453",
        "payment_mode": "UPI",
        "guest_name": "Anita Desai",
        "voucher_date": date(2026, 4, 18),
    },
    {
        "payment_amount": 4500.0,
        "invoice_no": "25-26/6454",
        "payment_mode": "CASH",
        "guest_name": "Mohammed Ali",
        "voucher_date": date(2026, 4, 19),
    },
]

# Generate vouchers
tallymessages = []
for payment in payments:
    voucher = generate_journal_voucher(**payment)
    tallymessages.append(voucher)

# Wrap in envelope
xml_output = vouchers_envelope(tallymessages)

# Write to file
output_path = "data/recon/output/journal_vouchers_2026-04-29.xml"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(xml_output)

print(f"Generated {len(payments)} Journal vouchers to {output_path}")
