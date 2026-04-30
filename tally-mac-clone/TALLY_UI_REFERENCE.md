# Tally UI/UX Reference - The REAL Interface

**Source:** tmv-recon production usage analysis, TallyPrime 7.0 actual workflows

---

## Core Philosophy

**Tally is NOT a chat app. It's a keyboard-driven accounting terminal.**

- Primary input: **Function keys (F1-F12)** + **Alt combos**
- Mouse optional (power users never touch it)
- Every screen has keyboard shortcuts displayed at bottom
- Navigation: Tab/Shift+Tab between fields, Enter to accept, Esc to cancel
- Speed: Expert users can create vouchers in <10 seconds

---

## Main Navigation Structure

### Gateway of Tally (Alt+G or first screen)

```
┌─────────────────────────────────────────────┐
│         GATEWAY OF TALLY                    │
├─────────────────────────────────────────────┤
│ 1. Masters                     (Alt+K)      │
│ 2. Transactions / Vouchers                  │
│ 3. Display / Reports           (Alt+R)      │
│ 4. Import / Export             (Alt+X)      │
│ 5. Utilities                   (Alt+U)      │
│ 6. Quit                        (Ctrl+Q)     │
└─────────────────────────────────────────────┘
```

### Function Key Map

| Key | Voucher Type | Purpose |
|-----|-------------|---------|
| **F1** | Help | Context-sensitive help |
| **F2** | Date | Change voucher date |
| **F3** | Company | Select/change company |
| **F4** | Contra | Bank-to-bank transfer |
| **F5** | Payment | Money out (vendor payment, expenses) |
| **F6** | Receipt | Money in (customer payment, income) |
| **F7** | Journal | General journal entry |
| **F8** | Sales | Customer invoice |
| **F9** | Purchase | Vendor bill |
| **F10** | Reversing Journal | Period-end reversals |
| **F11** | Features | Configuration (GST, inventory on/off) |
| **F12** | Configure | Settings |

### Alt Key Shortcuts

| Combo | Action |
|-------|--------|
| **Alt+K** | Masters menu |
| **Alt+G** | Gateway (main menu) |
| **Alt+R** | Reports/Display menu |
| **Alt+X** | Import/Export |
| **Alt+U** | Utilities |
| **Alt+D** | Delete current item |
| **Alt+F** | Fill voucher details |
| **Ctrl+A** | Accept/Save |
| **Esc** | Cancel/Go back |

---

## Screen Layouts

### 1. Voucher Entry Screen (F5-F9)

**Example: Sales Voucher (F8)**

```
┌────────────────────────────────────────────────────────────────┐
│ Sales Voucher                                   [F1: Help]      │
├────────────────────────────────────────────────────────────────┤
│ Ref No:   [SV-001        ]     Date: [28-Apr-2026] (F2: Change)│
│                                                                  │
│ Party A/c Name: [Sundry Debtors        ] ← (autocomplete)      │
│                 Dr   50,000.00                                   │
│                                                                  │
│ Particulars:                                                     │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ Ledger              │ Rate │ Qty │     Amount │  GST │ Total ││
│ ├─────────────────────┼──────┼─────┼────────────┼──────┼───────┤│
│ │ Room Rent (18% GST) │      │     │  42,372.88 │      │       ││
│ │   CGST @ 9%         │      │     │   3,813.56 │      │       ││
│ │   SGST @ 9%         │      │     │   3,813.56 │      │       ││
│ │                     │      │     │            │      │       ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│ Narration: [Invoice for guest stay - Room 101]                 │
│                                                                  │
│ Total:     Cr   50,000.00                                       │
│                                                                  │
│ [Ctrl+A: Accept] [Esc: Cancel] [Alt+D: Delete] [F12: Configure]│
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Tab between fields
- Ledger names autocomplete (type to search)
- GST auto-calculated based on ledger config
- Dr/Cr balances must sum to zero
- Enter to add new ledger line

### 2. Masters Screen (Alt+K)

```
┌────────────────────────────────────────────────────────────────┐
│ Masters                                                         │
├────────────────────────────────────────────────────────────────┤
│ 1. Groups                                                       │
│ 2. Ledgers                                                      │
│ 3. Stock Items                                                  │
│ 4. Stock Groups                                                 │
│ 5. Units of Measure                                             │
│ 6. Voucher Types                                                │
│ 7. Godowns                                                      │
│ 8. Cost Centers                                                 │
│ 9. Cost Categories                                              │
│ 10. Currencies                                                  │
│ 11. Employees                                                   │
│                                                                  │
│ [Enter: Select] [Esc: Return] [F12: Configure]                 │
└────────────────────────────────────────────────────────────────┘
```

**Ledger List View:**

```
┌────────────────────────────────────────────────────────────────┐
│ List of Ledgers                            [F12: Filter]        │
├────────────────────────────────────────────────────────────────┤
│ Search: [____________________]  ← (type to filter)             │
│                                                                  │
│ Name                  │ Group           │ Closing Balance      │
│ ─────────────────────────────────────────────────────────────  │
│ Cash in Hand          │ Cash            │     12,450.00 Dr     │
│ HDFC Bank CC          │ Bank Accounts   │    145,230.50 Cr     │
│ Sundry Debtors        │ Sundry Debtors  │    567,890.00 Dr     │
│ ABC Suppliers         │ Sundry Creditors│     89,450.00 Cr     │
│ Room Rent (18% GST)   │ Sales Accounts  │  1,234,567.00 Cr     │
│ ...                                                              │
│                                                                  │
│ [Enter: Alter] [Alt+C: Create] [Alt+D: Delete] [Esc: Return]   │
└────────────────────────────────────────────────────────────────┘
```

### 3. Reports Screen (Alt+R → Display)

```
┌────────────────────────────────────────────────────────────────┐
│ Display                                                         │
├────────────────────────────────────────────────────────────────┤
│ 1. Day Book                                                     │
│ 2. Trial Balance                                                │
│ 3. Balance Sheet                                                │
│ 4. Profit & Loss                                                │
│ 5. Cash Flow                                                    │
│ 6. Funds Flow                                                   │
│ 7. Ratio Analysis                                               │
│ ─────────────────────────────────────────────────────────────  │
│ 8. Sales Register                                               │
│ 9. Purchase Register                                            │
│ 10. Payment Register                                            │
│ 11. Receipt Register                                            │
│ 12. Journal Register                                            │
│ ─────────────────────────────────────────────────────────────  │
│ 13. Bills Receivable                                            │
│ 14. Bills Payable                                               │
│ 15. Outstanding (Group/Ledger)                                  │
│ 16. Stock Summary                                               │
│                                                                  │
│ [Enter: Select] [Alt+E: Export] [Esc: Return]                  │
└────────────────────────────────────────────────────────────────┘
```

**Trial Balance View (with drill-down):**

```
┌────────────────────────────────────────────────────────────────┐
│ Trial Balance as on 30-Apr-2026            [Alt+F5: Explode]   │
├────────────────────────────────────────────────────────────────┤
│ Period: 01-Apr-2026 to 30-Apr-2026        [F2: Change Period]  │
│                                                                  │
│ Particulars                    │    Debit    │    Credit       │
│ ──────────────────────────────────────────────────────────────│
│ ► Capital Account              │             │   500,000.00    │
│ ► Current Assets               │ 1,234,567.89│                 │
│   ► Bank Accounts              │   145,230.50│                 │
│   ► Cash                       │    12,450.00│                 │
│   ► Sundry Debtors             │   567,890.00│                 │
│ ► Current Liabilities          │             │   423,456.78    │
│   ► Sundry Creditors           │             │   234,567.00    │
│ ► Sales Accounts               │             │ 1,234,567.89    │
│   ► Room Rent                  │             │ 1,045,678.90    │
│   ► F&B Sales                  │             │   188,888.99    │
│ ...                                                              │
│ ──────────────────────────────────────────────────────────────│
│ Total                          │ 2,345,678.90│ 2,345,678.90    │
│                                                                  │
│ [Enter: Drill] [Alt+P: Print] [Alt+E: Export] [Esc: Return]    │
└────────────────────────────────────────────────────────────────┘
```

**Drill-down behavior:**
- Click/Enter on group → expands to show ledgers
- Click/Enter on ledger → shows Day Book for that ledger
- Esc goes back up one level

### 4. Day Book (Transaction List)

```
┌────────────────────────────────────────────────────────────────┐
│ Day Book                                      01-Apr to 30-Apr │
├────────────────────────────────────────────────────────────────┤
│ Date    │ Particulars      │ Vch Type │ Vch No  │ Dr      │ Cr  │
│ ────────┼──────────────────┼──────────┼─────────┼─────────┼────│
│ 01-Apr  │ Cash in Hand     │ Receipt  │ RC-001  │ 10,000  │     │
│         │   To Room Rent   │          │         │         │10000│
│ 02-Apr  │ ABC Suppliers    │ Payment  │ PY-023  │         │ 5000│
│         │   By HDFC Bank   │          │         │  5,000  │     │
│ 05-Apr  │ Sundry Debtors   │ Sales    │ SV-126  │ 50,000  │     │
│         │   To Room Rent   │          │         │         │42373│
│         │   To CGST@9%     │          │         │         │ 3814│
│         │   To SGST@9%     │          │         │         │ 3814│
│ ...                                                              │
│                                                                  │
│ [Enter: View] [Alt+E: Export] [F12: Filter] [Esc: Return]      │
└────────────────────────────────────────────────────────────────┘
```

---

## Export Formats

All reports support:
- **Excel** (.xlsx) - most common
- **PDF** - for printing
- **XML** - for programmatic access
- **CSV** - for simple data transfer
- **Print** - direct to printer

Export triggered via **Alt+E** from any report screen.

---

## Import Workflow

**Gateway → Import → Excel**

1. Download template (predefined for each master type)
2. Fill Excel with data (ledgers, items, vouchers)
3. Import → validates → shows summary
4. Accept or reject import

**Gateway → Import → XML**

For programmatic bulk imports (what tmv-recon uses).

---

## Company Selection

**F3** at any time:
```
┌────────────────────────────────────────────┐
│ Select Company                             │
├────────────────────────────────────────────┤
│ 1. THE MANGAL VIEW RESIDENCY Final         │
│ 2. XYZ Private Limited                     │
│ 3. Create New Company                      │
│                                            │
│ [Enter: Select] [Esc: Cancel]             │
└────────────────────────────────────────────┘
```

---

## Key UI/UX Principles for Clone

1. **Keyboard First** - Every action must have keyboard shortcut
2. **Autocomplete** - Ledger/item names type-to-search
3. **Validation** - Dr/Cr must balance before save
4. **Speed** - No loading spinners, instant response
5. **Bottom Bar** - Always show available shortcuts
6. **Drill-down** - Reports allow drilling to detail
7. **Minimal Chrome** - No fancy graphics, max info density
8. **Status Bar** - Company name, financial year, user always visible
9. **Escape Path** - Esc always goes back/cancels
10. **No Modals** - Everything in main workspace (Tally uses full-screen forms)

---

## What We Built vs What Tally Has

### Current RecordX.Finance UI
```
┌─────────────────────────────────────────────┐
│ Chat (30%)  │  Workspace (70%)              │
│             │                                │
│ "Create     │  [voucher form or dashboard]  │
│  voucher"   │                                │
│             │                                │
└─────────────────────────────────────────────┘
```

❌ Primary interface = chat  
❌ No keyboard shortcuts  
❌ No Gateway menu  
❌ No F-key voucher entry  
❌ No reports drill-down  
❌ No export functionality  
❌ No autocomplete  
❌ No masters management  

### What Tally Actually Is
```
┌─────────────────────────────────────────────┐
│ [Menu Bar: Gateway | Masters | Reports]     │
├─────────────────────────────────────────────┤
│                                              │
│   [Full-screen voucher entry form]          │
│   OR                                         │
│   [Full-screen report with drill-down]      │
│   OR                                         │
│   [Full-screen masters list]                │
│                                              │
├─────────────────────────────────────────────┤
│ Status: Company | FY 2025-26 | User: Admin │
│ F5:Pmt F6:Rcp F8:Sales F12:Config ESC:Back  │
└─────────────────────────────────────────────┘
```

✅ Keyboard-driven  
✅ F-keys everywhere  
✅ Context-sensitive help (F1)  
✅ Instant autocomplete  
✅ Drill-down reports  
✅ Export to Excel/PDF/XML  
✅ Full masters CRUD  
✅ Gateway navigation  

---

## Rebuild Plan

**Phase 1: UI Framework**
- Implement keyboard event handling (F1-F12, Alt combos)
- Build Gateway menu system
- Create voucher entry form template
- Add status bar with shortcuts

**Phase 2: Voucher Entry**
- F5 (Payment), F6 (Receipt), F7 (Journal), F8 (Sales), F9 (Purchase)
- Autocomplete for ledgers
- Real-time Dr/Cr validation
- GST auto-calculation

**Phase 3: Masters**
- Ledger list with search/filter
- Create/Edit/Delete forms
- Group hierarchy tree view
- Stock items, units, cost centers

**Phase 4: Reports**
- Day Book with filters
- Trial Balance with drill-down
- Balance Sheet, P&L, Cash Flow
- Export to Excel/PDF/XML

**Phase 5: Import/Export**
- Excel template download
- Bulk import UI with validation
- XML import/export
- Bank statement import

**Phase 6: Polish**
- Reposition chat as collapsible assistant
- Add keyboard shortcuts help (F1)
- Improve autocomplete speed
- Add voucher templates

---

**Status:** UI research complete. Ready to rebuild.
