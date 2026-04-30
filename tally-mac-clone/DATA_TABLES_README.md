# RecordX.Finance Data Tables

## Overview

Searchable, sortable data tables built with Alpine.js for RecordX.Finance accounting system.

## Components Created

All components are located in `/src/tally_mac_clone/static/components/`

### 1. Generic Data Table (`data-table.html`)
Reusable Alpine.js component for building custom tables.

**Features:**
- Search across all columns
- Multi-column sorting
- Custom filters (dropdown)
- Row selection with batch operations
- Pagination (configurable page size)
- Keyboard navigation (arrow keys, Enter)
- Export to Excel/CSV
- Responsive design

**Usage:**
```html
<div x-data="dataTable(config)">
  <!-- Table renders automatically -->
</div>
```

**Config Options:**
```javascript
{
  data: [],                    // Array of row objects
  columns: [],                 // Column definitions
  rowKey: 'id',               // Unique identifier
  searchable: true,           // Enable search
  sortable: true,             // Enable sorting
  selectable: false,          // Enable row selection
  clickable: true,            // Rows are clickable
  batchDelete: false,         // Enable batch delete
  actions: false,             // Show edit/delete buttons
  pagination: true,           // Enable pagination
  pageSize: 10,              // Rows per page
  filters: [],               // Filter dropdowns
  onRowClick: fn,            // Row click handler
  onEdit: fn,                // Edit handler
  onDelete: fn,              // Delete handler
  onBatchDelete: fn          // Batch delete handler
}
```

### 2. Ledger Table (`ledger-table.html`)
Master ledger accounts table.

**Features:**
- Search by ledger name
- Filter by group (Sundry Debtors, Bank Accounts, etc.)
- Filter by type (Asset, Liability, Revenue, Expense)
- Sort by name, group, type, opening balance, current balance
- Click row to edit ledger
- Keyboard navigation (↑↓ arrows, Enter)
- Color-coded balances (green=positive, red=negative)
- Export to Excel

**Columns:**
- Name
- Group
- Type (with colored badges)
- Opening Balance
- Current Balance

**Sample Data Included:** 8 ledger accounts

### 3. Voucher List Table (`voucher-list-table.html`)
Transaction voucher management.

**Features:**
- Search by voucher number, party, or narration
- Date range filter (from/to)
- Filter by voucher type (Payment, Receipt, Journal, etc.)
- Filter by party
- Sort by date, type, amount
- Batch delete with selection
- Click row to view/edit voucher
- Keyboard navigation
- Color-coded voucher types
- Export to Excel

**Columns:**
- Date
- Type (with colored badges)
- Number
- Party
- Amount
- Narration (truncated)

**Voucher Types Supported:**
- Payment, Receipt, Journal, Contra
- Sales, Purchase
- Credit Note, Debit Note

**Sample Data Included:** 8 vouchers

### 4. Stock Items Table (`stock-items-table.html`)
Inventory management with low stock alerts.

**Features:**
- Low stock alert banner (shows count)
- Toggle to show only low stock items
- Search by item name
- Filter by group (Raw Materials, Finished Goods, etc.)
- Filter by unit (Nos, Kgs, Ltrs, Mtr, Box)
- Sort by name, group, rate, stock qty, value
- Click row to edit stock item
- Keyboard navigation
- Visual indicators:
  - Green: In Stock
  - Yellow: Low Stock (highlighted row)
  - Red: Out of Stock
- Export to Excel

**Columns:**
- Name
- Group
- Unit
- Rate
- Stock Qty (with unit)
- Value (calculated)
- Status (badge)

**Stock Status Logic:**
- In Stock: qty > min_qty
- Low Stock: qty ≤ min_qty and qty > 0
- Out of Stock: qty = 0

**Sample Data Included:** 8 stock items

### 5. Outstanding Bills Table (`outstanding-bills-table.html`)
Receivables and payables tracking with aging analysis.

**Features:**
- Summary cards:
  - Total Outstanding
  - Total Receivables (green)
  - Total Payables (red)
  - Total Overdue (orange)
- Search by party or bill number
- Filter by type (Receivable/Payable)
- Filter by aging buckets:
  - Current (0-30 days)
  - 30-60 days
  - 60-90 days
  - 90+ days
  - Overdue only
- Filter by party
- Sort by party, bill date, due date, amount, pending, overdue days
- Click row to allocate payment
- Keyboard navigation
- Overdue bills highlighted in red
- Color-coded overdue badges:
  - Yellow: ≤30 days
  - Orange: 31-60 days
  - Red: 60+ days
- Export to Excel

**Columns:**
- Party
- Bill Number
- Bill Date
- Due Date
- Amount
- Pending
- Overdue Days (with colored badge)
- Type (Receivable/Payable badge)

**Sample Data Included:** 8 bills with calculated overdue days

## Integration

### Add to index.html

Add new workspace tabs (after line 199):
```html
<button @click="workspaceMode = 'ledgers'" ...>Ledgers</button>
<button @click="workspaceMode = 'vouchers'" ...>Vouchers</button>
<button @click="workspaceMode = 'stock'" ...>Stock Items</button>
<button @click="workspaceMode = 'bills'" ...>Outstanding Bills</button>
```

Add new workspace views (in the workspace content section):
```html
<!-- LEDGERS TABLE -->
<div x-show="workspaceMode === 'ledgers'" x-html="$fetchComponent('/static/components/ledger-table.html')"></div>

<!-- VOUCHERS TABLE -->
<div x-show="workspaceMode === 'vouchers'" x-html="$fetchComponent('/static/components/voucher-list-table.html')"></div>

<!-- STOCK ITEMS TABLE -->
<div x-show="workspaceMode === 'stock'" x-html="$fetchComponent('/static/components/stock-items-table.html')"></div>

<!-- OUTSTANDING BILLS TABLE -->
<div x-show="workspaceMode === 'bills'" x-html="$fetchComponent('/static/components/outstanding-bills-table.html')"></div>
```

Or simpler approach - include components directly:
```html
<div x-show="workspaceMode === 'ledgers'">
  <!-- Copy/paste ledger-table.html content here -->
</div>
```

## API Integration

Replace sample data with real API calls. Example for Ledger Table:

```javascript
async init() {
  const response = await fetch('/api/ledgers');
  this.ledgers = await response.json();
}
```

### API Endpoints Needed

1. **Ledgers:**
   - GET `/api/ledgers` - List all ledgers
   - GET `/api/ledgers/:id` - Get ledger details
   - POST `/api/ledgers` - Create ledger
   - PUT `/api/ledgers/:id` - Update ledger
   - DELETE `/api/ledgers/:id` - Delete ledger

2. **Vouchers:**
   - GET `/api/vouchers` - List all vouchers
   - GET `/api/vouchers/:id` - Get voucher details
   - POST `/api/vouchers` - Create voucher
   - PUT `/api/vouchers/:id` - Update voucher
   - DELETE `/api/vouchers` - Batch delete (accepts array of IDs)

3. **Stock Items:**
   - GET `/api/stock-items` - List all stock items
   - GET `/api/stock-items/:id` - Get item details
   - POST `/api/stock-items` - Create item
   - PUT `/api/stock-items/:id` - Update item

4. **Bills:**
   - GET `/api/bills/outstanding` - List outstanding bills
   - GET `/api/bills/:id` - Get bill details
   - POST `/api/bills/:id/allocate` - Allocate payment to bill

## Keyboard Shortcuts

All tables support:
- **↑/↓ Arrow Keys:** Navigate between rows
- **Enter:** Open selected row for editing/viewing
- **Tab:** Navigate between filters
- **Ctrl+F / Cmd+F:** Focus search box (can be added)

## Customization

### Styling

All components use Tailwind CSS classes. Modify colors by changing:
- Blue (primary): `bg-blue-600`, `text-blue-700`, etc.
- Table headers: `bg-gray-50`
- Hover states: `hover:bg-blue-50`

### Adding Custom Columns

In each component's config, add to columns array:
```javascript
columns: [
  // existing columns...
  {
    key: 'custom_field',
    label: 'Custom',
    align: 'right', // left, center, right
    className: 'text-purple-600',
    format: (value, row) => {
      return `Custom: ${value}`;
    }
  }
]
```

### Adding Custom Filters

```javascript
filters: [
  {
    key: 'status',
    label: 'Status',
    options: [
      { value: 'active', label: 'Active' },
      { value: 'inactive', label: 'Inactive' }
    ]
  }
]
```

## Performance

- Tables use virtual pagination (only render visible rows)
- Filtering and sorting are client-side (fast for <10,000 rows)
- For larger datasets, implement server-side pagination:
  - Modify `filteredData` to call API with params
  - Add `@change` handlers to update from server

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires Alpine.js 3.x and Tailwind CSS.

## Future Enhancements

1. **Advanced filtering:** Range sliders, multi-select
2. **Column visibility toggle:** Show/hide columns
3. **Saved views:** Store filter preferences
4. **Inline editing:** Edit cells without modal
5. **Drag & drop:** Reorder rows
6. **Print view:** Printer-friendly layout
7. **PDF export:** Using jsPDF library
8. **Real-time updates:** WebSocket integration
9. **Column resizing:** Drag to resize columns
10. **Grouping:** Group rows by column value

## License

MIT - RecordX.Finance
