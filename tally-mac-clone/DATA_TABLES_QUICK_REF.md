# Data Tables Quick Reference

## Files Created

```
/src/tally_mac_clone/static/components/
├── data-table.html                  # Generic reusable component
├── ledger-table.html                # Ledger masters table
├── voucher-list-table.html          # Vouchers list table  
├── stock-items-table.html           # Stock/inventory table
├── outstanding-bills-table.html     # Receivables/payables table
└── integration-example.html         # Integration guide
```

## Quick Features Matrix

| Feature                | Ledgers | Vouchers | Stock | Bills |
|------------------------|---------|----------|-------|-------|
| Search                 | ✓       | ✓        | ✓     | ✓     |
| Sort all columns       | ✓       | ✓        | ✓     | ✓     |
| Filter dropdowns       | 2       | 3        | 2     | 3     |
| Date range filter      | -       | ✓        | -     | -     |
| Batch delete           | -       | ✓        | -     | -     |
| Keyboard nav (↑↓⏎)     | ✓       | ✓        | ✓     | ✓     |
| Click to edit          | ✓       | ✓        | ✓     | ✓     |
| Export Excel/CSV       | ✓       | ✓        | ✓     | ✓     |
| Colored badges         | ✓       | ✓        | ✓     | ✓     |
| Pagination             | ✓       | ✓        | ✓     | ✓     |
| Summary cards          | -       | -        | -     | ✓     |
| Alert banners          | -       | -        | ✓     | -     |

## Component Sizes (Sample Data)

- **Ledger Table:** 8 accounts
- **Voucher List:** 8 vouchers
- **Stock Items:** 8 items
- **Outstanding Bills:** 8 bills

## Key Filters

### Ledgers
- Group: Sundry Debtors, Bank Accounts, Cash, Sales, Purchase, Expenses
- Type: Asset, Liability, Revenue, Expense

### Vouchers
- Type: Payment, Receipt, Journal, Contra, Sales, Purchase, Credit Note, Debit Note
- Party: All unique parties
- Date Range: From/To dates

### Stock Items
- Group: Raw Materials, Finished Goods, WIP, Consumables, Trading Goods
- Unit: Nos, Kgs, Ltrs, Mtr, Box
- Stock Status: All / Low Stock only

### Outstanding Bills
- Type: Receivable, Payable
- Aging: Current (0-30), 30-60, 60-90, 90+, Overdue
- Party: All unique parties

## Integration Steps

1. **Add workspace tabs** to index.html tab bar
2. **Copy component HTML** into workspace content divs
3. **Replace sample data** with API calls
4. **Add modal forms** for create/edit
5. **Test** each table

## Color Coding

### Ledger Table
- **Green badge:** Asset
- **Red badge:** Liability  
- **Blue badge:** Revenue
- **Yellow badge:** Expense
- **Green amount:** Positive balance
- **Red amount:** Negative balance

### Voucher List
- **Red badge:** Payment
- **Green badge:** Receipt
- **Purple badge:** Journal
- **Blue badge:** Contra
- **Emerald badge:** Sales
- **Orange badge:** Purchase
- **Pink badge:** Credit Note
- **Yellow badge:** Debit Note

### Stock Items
- **Green badge:** In Stock (qty > min)
- **Yellow badge + row:** Low Stock (qty ≤ min)
- **Red badge:** Out of Stock (qty = 0)

### Outstanding Bills
- **Green badge:** Receivable
- **Red badge:** Payable
- **Yellow badge:** Overdue ≤30 days
- **Orange badge:** Overdue 31-60 days
- **Red badge:** Overdue 60+ days
- **Red row:** Any overdue bill

## API Endpoints Required

```
GET    /api/ledgers              # List ledgers
GET    /api/ledgers/:id          # Get ledger
POST   /api/ledgers              # Create ledger
PUT    /api/ledgers/:id          # Update ledger
DELETE /api/ledgers/:id          # Delete ledger

GET    /api/vouchers             # List vouchers
GET    /api/vouchers/:id         # Get voucher
POST   /api/vouchers             # Create voucher
PUT    /api/vouchers/:id         # Update voucher
DELETE /api/vouchers             # Batch delete (array of IDs)

GET    /api/stock-items          # List stock items
GET    /api/stock-items/:id      # Get item
POST   /api/stock-items          # Create item
PUT    /api/stock-items/:id      # Update item

GET    /api/bills/outstanding    # List outstanding bills
GET    /api/bills/:id            # Get bill
POST   /api/bills/:id/allocate   # Allocate payment
```

## Sample API Call

```javascript
// In component's init() method
async init() {
  const response = await fetch('/api/ledgers');
  this.ledgers = await response.json();
}

// Handle create
async createLedger() {
  const response = await fetch('/api/ledgers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  });
  if (response.ok) await this.init();
}
```

## Keyboard Shortcuts

All tables:
- **↑** Navigate up
- **↓** Navigate down
- **Enter** Open selected row
- **Tab** Move between filters
- **Esc** Close modals (when added)

## Browser Console Testing

```javascript
// Test filter
Alpine.store('ledgerTable').activeFilters.group = 'Bank Accounts';
Alpine.store('ledgerTable').applyFilters();

// Test sort
Alpine.store('ledgerTable').sortBy('current_balance');

// Test search
Alpine.store('ledgerTable').searchQuery = 'cash';
```

## Performance Tips

- Client-side filtering good for <10,000 rows
- For larger datasets, use server-side pagination
- Debounce search input (add 300ms delay)
- Virtual scrolling for very large tables

## Customization

Change primary color from blue:
```html
<!-- Replace all instances of: -->
bg-blue-600  → bg-purple-600
text-blue-700 → text-purple-700
ring-blue-500 → ring-purple-500
```

Change page size:
```javascript
pageSize: 10  // Change to 25, 50, 100, etc.
```

Add new column:
```javascript
columns: [
  // ...existing
  {
    key: 'new_field',
    label: 'New Field',
    align: 'right',
    format: (val) => `₹${val}`
  }
]
```
