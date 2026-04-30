# Data Tables Visual Guide

## Component Layouts

### 1. Ledger Table

```
┌──────────────────────────────────────────────────────────────────────┐
│ Ledgers Masters                                [Create Ledger]       │
│ Manage all ledger accounts                                           │
├──────────────────────────────────────────────────────────────────────┤
│ [Search ledger by name...] [All Groups ▾] [All Types ▾] [Export]   │
├──────────────────────────────────────────────────────────────────────┤
│ Name ↑          │ Group        │ Type    │ Opening Bal │ Current Bal│
├─────────────────┼──────────────┼─────────┼─────────────┼────────────┤
│ Cash Account    │ Cash-in-Hand │ Asset   │ ₹50,000.00  │ ₹84,500.00 │
│ HDFC Bank       │ Bank Accts   │ Asset   │ ₹100,000.00 │ ₹125,000.00│
│ ABC Suppliers   │ Sund Cred    │ Liab    │ ₹0.00       │ -₹25,000.00│
│ XYZ Customer    │ Sund Debt    │ Asset   │ ₹0.00       │ ₹45,000.00 │
│ Sales Account   │ Sales Accts  │ Revenue │ ₹0.00       │ ₹250,000.00│
│ Rent Expense    │ Indir Exp    │ Expense │ ₹0.00       │ ₹30,000.00 │
│ ...             │              │         │             │            │
├──────────────────────────────────────────────────────────────────────┤
│ Showing 1 to 8 of 8 ledgers          [Previous] [Next]              │
└──────────────────────────────────────────────────────────────────────┘
```

**Color Indicators:**
- Type badges: Green (Asset), Red (Liability), Blue (Revenue), Yellow (Expense)
- Balance amounts: Green (positive), Red (negative)

### 2. Voucher List Table

```
┌──────────────────────────────────────────────────────────────────────┐
│ Vouchers                                       [Create Voucher]      │
│ View and manage all vouchers                                         │
├──────────────────────────────────────────────────────────────────────┤
│ [Search by number, party, narration...]                             │
│ [2026-04-01] to [2026-04-30] [All Types ▾] [All Parties ▾]         │
│ [Delete (2)] [Export]                                                │
├──────────────────────────────────────────────────────────────────────┤
│☐│ Date ↓    │ Type    │ Number  │ Party        │ Amount   │ Narr... │
├─┼───────────┼─────────┼─────────┼──────────────┼──────────┼─────────┤
│☐│ 28-Apr-26 │ Payment │ PAY-001 │ ABC Suppli.. │ ₹15,000  │ Payment │
│☑│ 29-Apr-26 │ Receipt │ RCV-001 │ XYZ Customer │ ₹25,000  │ Receiv..│
│☑│ 30-Apr-26 │ Journal │ JV-001  │ N/A          │ ₹5,000   │ Deprec..│
│☐│ 27-Apr-26 │ Sales   │ SAL-045 │ Retail Cust  │ ₹32,000  │ Sale o..│
│☐│ 26-Apr-26 │ Purchase│ PUR-089 │ ABC Suppli.. │ ₹18,000  │ Purcha..│
│ ...                                                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Showing 1 to 8 of 8 vouchers         [Previous] [Next]              │
└──────────────────────────────────────────────────────────────────────┘
```

**Color Indicators:**
- Type badges: Red (Payment), Green (Receipt), Purple (Journal), 
  Blue (Contra), Emerald (Sales), Orange (Purchase), Pink (Credit Note),
  Yellow (Debit Note)

### 3. Stock Items Table

```
┌──────────────────────────────────────────────────────────────────────┐
│ Stock Items                                    [Add Stock Item]      │
│ Inventory management and stock tracking                              │
├──────────────────────────────────────────────────────────────────────┤
│ ⚠ Low Stock Alert                                [View Low Stock]    │
│   3 items are running low on stock. Review and reorder.              │
├──────────────────────────────────────────────────────────────────────┤
│ [Search stock items...] [All Groups ▾] [All Units ▾] [Export]       │
├──────────────────────────────────────────────────────────────────────┤
│ Name ↑           │ Group    │ Unit │ Rate    │ Stock Qty │ Value   ⚑│
├──────────────────┼──────────┼──────┼─────────┼───────────┼─────────┤
│ Steel Rods-10mm  │ Raw Mat  │ Kgs  │ ₹55.00  │ 450 Kgs   │ ₹24,750 │
│ Cement 50kg bags │ Raw Mat  │ Box  │ ₹350.00 │ 85 Box    │ ₹29,750 │
│ Finished Prod A  │ Fin Good │ Nos  │ ₹1200.00│ 150 Nos   │ ₹180,000│
│ Paint - White    │ Consumbl │ Ltrs │ ₹280.00 │ 25 Ltrs ⚠ │ ₹7,000  │ ← LOW
│ Sandpaper Sheets │ Consumbl │ Nos  │ ₹15.00  │ 0 Nos  ⚠⚠│ ₹0      │ ← OUT
│ Wooden Planks    │ Raw Mat  │ Nos  │ ₹450.00 │ 200 Nos   │ ₹90,000 │
│ ...                                                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Showing 1 to 8 of 8 items             [Previous] [Next]             │
└──────────────────────────────────────────────────────────────────────┘
```

**Color Indicators:**
- Status badges: Green (In Stock), Yellow (Low Stock), Red (Out of Stock)
- Low stock rows: Yellow background highlight
- Alert banner: Yellow with warning icon

### 4. Outstanding Bills Table

```
┌──────────────────────────────────────────────────────────────────────┐
│ Outstanding Bills                              [Allocate Payment]    │
│ Track receivables and payables                                       │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐       │
│ │Total Outstnd │ Receivables  │ Payables     │ Overdue      │       │
│ │ ₹2,81,500    │ ₹1,86,000    │ ₹95,500      │ ₹1,40,500    │       │
│ └──────────────┴──────────────┴──────────────┴──────────────┘       │
├──────────────────────────────────────────────────────────────────────┤
│ [Search by party/bill...] [All Bills ▾] [All Aging ▾] [Export]      │
│ [All Parties ▾]                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ Party ↑      │Bill No│Bill Date│Due Date│Amount │Pending│Overd⚠│Type│
├──────────────┼───────┼─────────┼────────┼───────┼───────┼──────┼────┤
│ABC Cust Ltd  │INV-001│15-Mar-26│15-Apr  │₹45,000│₹45,000│15 d  │Recv│ ← OVERDUE
│XYZ Traders   │INV-015│10-Apr-26│10-May  │₹28,000│₹28,000│  -   │Recv│
│PQR Suppliers │BILL890│20-Feb-26│22-Mar  │₹35,000│₹35,000│39 d ⚠│Payb│ ← OVERDUE
│MNO Enterp    │INV-020│25-Apr-26│25-May  │₹52,000│₹52,000│  -   │Recv│
│LMN Services  │BILL456│05-Mar-26│05-Apr  │₹18,500│₹18,500│25 d  │Payb│ ← OVERDUE
│DEF Corp      │INV-008│20-Apr-26│20-May  │₹67,000│₹30,000│  -   │Recv│ ← PARTIAL
│GHI Suppliers │BILL789│15-Jan-26│15-Feb  │₹42,000│₹42,000│74 d⚠⚠│Payb│ ← OVERDUE
│ ...                                                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Showing 1 to 8 of 8 bills             [Previous] [Next]             │
└──────────────────────────────────────────────────────────────────────┘
```

**Color Indicators:**
- Type badges: Green (Receivable), Red (Payable)
- Overdue badges: Yellow (≤30 days), Orange (31-60 days), Red (60+ days)
- Overdue rows: Red background highlight
- Summary cards: White (total), Green (receivables), Red (payables), Orange (overdue)

## Common UI Elements

### Search Box
```
┌─────────────────────────────────────┐
│ 🔍 Search ledger by name...         │
└─────────────────────────────────────┘
```

### Filter Dropdown
```
┌────────────────┐
│ All Groups   ▾ │ ← Click to expand
└────────────────┘
  │
  ├─ Sundry Debtors
  ├─ Sundry Creditors
  ├─ Bank Accounts
  ├─ Cash-in-Hand
  └─ Sales Accounts
```

### Sort Indicator
```
Name ↑          ← Ascending (A→Z)
Name ↓          ← Descending (Z→A)
Name            ← Not sorted
```

### Pagination
```
Showing 1 to 10 of 45 entries    [Previous] [Next]
                                 [1] 2 3 4 5
```

### Export Button
```
┌─────────────────┐
│ ⬇ Export Excel  │
└─────────────────┘
```

### Action Buttons
```
┌──────────────────┐   ┌──────────┐
│ + Create Ledger  │   │ Delete   │
└──────────────────┘   └──────────┘
```

### Batch Delete
```
☑ Selected 3 items    [Delete Selected]
```

## Status Badges

### Type Badges (Ledgers)
```
┌─────────┐  ┌───────────┐  ┌─────────┐  ┌─────────┐
│ Asset   │  │ Liability │  │ Revenue │  │ Expense │
└─────────┘  └───────────┘  └─────────┘  └─────────┘
  Green         Red           Blue         Yellow
```

### Voucher Type Badges
```
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────┐
│ Payment │  │ Receipt │  │ Journal │  │ Sales│
└─────────┘  └─────────┘  └─────────┘  └──────┘
   Red        Green        Purple       Emerald
```

### Stock Status Badges
```
┌──────────┐  ┌───────────┐  ┌──────────────┐
│ In Stock │  │ Low Stock │  │ Out of Stock │
└──────────┘  └───────────┘  └──────────────┘
   Green         Yellow           Red
```

### Overdue Badges
```
┌─────────┐  ┌──────────┐  ┌──────────┐
│ 15 days │  │ 45 days  │  │ 75 days  │
└─────────┘  └──────────┘  └──────────┘
  Yellow       Orange         Red
 (0-30 d)     (31-60 d)      (60+ d)
```

## Interactive States

### Row Hover
```
Normal:   │ Cash Account    │ Cash-in-Hand │
Hover:    │ Cash Account    │ Cash-in-Hand │ ← Blue highlight
Focused:  │ Cash Account    │ Cash-in-Hand │ ← Blue ring outline
```

### Row Selection
```
☐ │ Cash Account       ← Not selected
☑ │ HDFC Bank          ← Selected (blue checkbox)
```

### Button States
```
[Create Ledger]     ← Normal (blue)
[Create Ledger]     ← Hover (darker blue)
[Create Ledger]     ← Disabled (gray, 50% opacity)
```

## Responsive Breakpoints

### Desktop (>768px)
- Full table width
- All columns visible
- Side-by-side filters

### Tablet (768px - 1024px)
- Scrollable table
- All columns visible
- Stacked filters

### Mobile (<768px)
- Card view (recommended)
- Essential columns only
- Vertical filters

## Keyboard Navigation

```
Row 1  │ ABC Customer    │ ← Current focus (blue outline)
Row 2  │ XYZ Supplier    │
Row 3  │ Cash Account    │

Press ↓ → Move to Row 2
Press ↑ → Move back to Row 1
Press Enter → Open row for editing
Press Tab → Move to next filter/button
```

## Empty States

```
┌──────────────────────────────────────┐
│                                      │
│          📄                          │
│                                      │
│      No records found                │
│                                      │
│   Try adjusting your filters         │
│                                      │
└──────────────────────────────────────┘
```

## Loading States (Future)

```
┌──────────────────────────────────────┐
│                                      │
│          ⟳                           │
│                                      │
│      Loading data...                 │
│                                      │
└──────────────────────────────────────┘
```

## Color Palette

### Primary Colors
- Blue-600: #2563eb (Primary buttons, selected state)
- Blue-50: #eff6ff (Hover background)
- Blue-700: #1d4ed8 (Text on selected)

### Status Colors
- Green-600: #16a34a (Positive/In Stock)
- Red-600: #dc2626 (Negative/Overdue)
- Yellow-600: #ca8a04 (Warning/Low Stock)
- Orange-600: #ea580c (Alert)
- Purple-600: #9333ea (Info)

### Neutral Colors
- Gray-50: #f9fafb (Table header background)
- Gray-100: #f3f4f6 (Hover state)
- Gray-200: #e5e7eb (Borders)
- Gray-600: #4b5563 (Secondary text)
- Gray-900: #111827 (Primary text)

## Typography

### Font Sizes
- Table Headers: text-xs (12px) uppercase
- Table Data: text-sm (14px)
- Page Title: text-2xl (24px)
- Button Text: text-sm (14px)

### Font Weights
- Headers: font-semibold (600)
- Data: font-normal (400)
- Amounts: font-semibold (600)
- Buttons: font-medium (500)

## Spacing

- Table padding: px-6 py-4 (24px 16px)
- Row padding: px-6 py-4 (24px 16px)
- Button padding: px-4 py-2 (16px 8px)
- Section gap: gap-6 (24px)

## Icons (Heroicons)

- Search: 🔍 magnifying glass
- Sort: ↑↓ arrows
- Export: ⬇ download
- Create: ➕ plus
- Delete: 🗑️ trash
- Warning: ⚠ triangle exclamation
- Success: ✓ check circle
- Info: ℹ information circle
