# Gateway Menu Structure - Visual Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  RecordX.Finance - Tally Clone                    Connected | Date  │
├─────────────────────────────────────────────────────────────────────┤
│  [Gateway (Alt+G)] [Masters (Alt+K)] [Reports (Alt+R)] [Import]    │
├─────────────────────────────────────────────────────────────────────┤
│  Gateway > Transactions/Vouchers > Payment                  [ESC ↩] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│                     WORKSPACE AREA                                   │
│                  (Dynamic Content Here)                              │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│ RecordX | FY 25-26 | Admin   [F4] [F5] [F6] [F7] [F8] [F9] [ESC]  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Full Menu Hierarchy

```
┌─ GATEWAY OF TALLY ──────────────────────────────────────┐
│                                                          │
│  Alt+G - Return to Gateway/Dashboard                    │
│                                                          │
├─ 1. MASTERS (Alt+K) ────────────────────────────────────┤
│  │                                                       │
│  ├─ Ledgers              → masters-ledgers              │
│  ├─ Groups               → masters-groups               │
│  ├─ Stock Items          → masters-stock-items          │
│  ├─ Units                → masters-units                │
│  ├─ Cost Centers         → masters-cost-centers         │
│  └─ Currencies           → masters-currencies           │
│                                                          │
├─ 2. TRANSACTIONS/VOUCHERS ──────────────────────────────┤
│  │                                                       │
│  ├─ Payment (F5)         → voucher-payment              │
│  ├─ Receipt (F6)         → voucher-receipt              │
│  ├─ Journal (F7)         → voucher-journal              │
│  ├─ Sales (F8)           → voucher-sales                │
│  ├─ Purchase (F9)        → voucher-purchase             │
│  └─ Contra (F4)          → voucher-contra               │
│                                                          │
├─ 3. REPORTS (Alt+R) ────────────────────────────────────┤
│  │                                                       │
│  ├─ Day Book             → report-day-book              │
│  ├─ Trial Balance        → report-trial-balance         │
│  ├─ Balance Sheet        → report-balance-sheet         │
│  ├─ Profit & Loss        → report-profit-loss           │
│  ├─ Cash Flow            → report-cash-flow             │
│  └─ All Registers        → report-all-registers         │
│                                                          │
├─ 4. IMPORT/EXPORT (Alt+X) ──────────────────────────────┤
│  │                                                       │
│  ├─ Import Excel         → import-excel                 │
│  ├─ Export Data          → export-data                  │
│  ├─ Bank Statement       → bank-statement               │
│  └─ Import XML           → import-xml                   │
│                                                          │
├─ 5. UTILITIES (Alt+U) ──────────────────────────────────┤
│  │                                                       │
│  ├─ Backup/Restore       → utilities-backup             │
│  └─ Settings (F12)       → utilities-settings           │
│                                                          │
└─ 6. QUIT (Ctrl+Q) ──────────────────────────────────────┘
```

---

## View State Flow Diagram

```
          [Start: Dashboard]
                  │
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
[Masters]    [Vouchers]    [Reports]
    │             │             │
    │             │             │
    ▼             ▼             ▼
[Ledgers]    [Payment]    [Trial Bal]
                  │
                  │
            [ESC pressed]
                  │
                  ▼
           [Back to Dashboard]
```

---

## Breadcrumb Evolution Examples

### Example 1: Navigate to Payment Voucher

```
Step 1:  Gateway
           ↓ (click Masters > Payment)
Step 2:  Gateway > Transactions/Vouchers > Payment
           ↓ (press ESC)
Step 3:  Gateway > Transactions/Vouchers
           ↓ (press ESC)
Step 4:  Gateway
```

### Example 2: Navigate to Trial Balance

```
Step 1:  Gateway
           ↓ (Alt+R, click Trial Balance)
Step 2:  Gateway > Reports > Trial Balance
           ↓ (click "Reports" in breadcrumb)
Step 3:  Gateway > Reports
```

---

## Keyboard Navigation Flow

```
┌─────────────────────────────────────────────────────────┐
│                   USER INPUT                            │
└──────────┬──────────────────────────────────────────────┘
           │
           ├─ Alt+G ──→ Navigate to Dashboard
           │
           ├─ Alt+K ──→ Open Masters Menu
           │             │
           │             └─ Click item ──→ Navigate to Master
           │
           ├─ Alt+R ──→ Open Reports Menu
           │             │
           │             └─ Click item ──→ Navigate to Report
           │
           ├─ F5 ─────→ Navigate to Payment Voucher
           ├─ F6 ─────→ Navigate to Receipt Voucher
           ├─ F7 ─────→ Navigate to Journal
           ├─ F8 ─────→ Navigate to Sales Voucher
           ├─ F9 ─────→ Navigate to Purchase Voucher
           │
           ├─ F12 ────→ Navigate to Settings
           │
           └─ ESC ────→ Close Menu OR Navigate Back
                         │
                         ├─ If menu open: Close menu
                         └─ If no menu: Go back in breadcrumbs
```

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     index.html                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Header (Company Info)                         │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Menu Bar (Gateway, Masters, Reports, etc.)    │    │
│  │  - Alpine.js $store.menu                       │    │
│  │  - Dropdowns with x-show                       │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Breadcrumb Navigation                         │    │
│  │  - Alpine.js $store.nav.breadcrumbs            │    │
│  │  - Click to navigate back                      │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │                                                 │    │
│  │           Workspace Area                       │    │
│  │                                                 │    │
│  │  ┌──────────────────────────────────────────┐ │    │
│  │  │ View: Dashboard                          │ │    │
│  │  │ x-show="$store.nav.currentView ==='dash'"│ │    │
│  │  └──────────────────────────────────────────┘ │    │
│  │                                                 │    │
│  │  ┌──────────────────────────────────────────┐ │    │
│  │  │ View: Payment Voucher                    │ │    │
│  │  │ x-show="$store.nav.currentView ==='vou..'│ │    │
│  │  └──────────────────────────────────────────┘ │    │
│  │                                                 │    │
│  │  ┌──────────────────────────────────────────┐ │    │
│  │  │ View: Trial Balance                      │ │    │
│  │  │ x-show="$store.nav.currentView ==='rep..'│ │    │
│  │  └──────────────────────────────────────────┘ │    │
│  │                                                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Status Bar (F-key shortcuts)                  │    │
│  │  - Click handlers                              │    │
│  │  - Company info, FY, User                      │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     menu.js                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Alpine.store('menu')                                   │
│  - activeMenu                                           │
│  - structure                                            │
│  - openMenu()                                           │
│  - closeMenus()                                         │
│                                                          │
│  Alpine.store('nav')                                    │
│  - currentView                                          │
│  - breadcrumbs[]                                        │
│  - navigateTo()                                         │
│  - navigateBack()                                       │
│  - goBack()                                             │
│                                                          │
│  Alpine.store('keyboard')                               │
│  - shortcuts{}                                          │
│  - init()                                               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow: User Clicks "Sales Voucher"

```
1. User clicks "Sales" in Transactions menu
   ↓
2. Menu item calls: $store.nav.navigateTo('voucher-sales', 'Sales')
   ↓
3. Alpine.store('nav').navigateTo() executes:
   - Sets currentView = 'voucher-sales'
   - Updates breadcrumbs = [
       { label: 'Gateway', view: 'dashboard' },
       { label: 'Transactions/Vouchers', view: 'voucher' },
       { label: 'Sales', view: 'voucher-sales' }
     ]
   - Calls $store.menu.closeMenus()
   ↓
4. Alpine reactivity triggers:
   - Hides all other views (x-show becomes false)
   - Shows voucher-sales view (x-show becomes true)
   - Updates breadcrumb display
   ↓
5. User sees Sales Voucher form with breadcrumb:
   "Gateway > Transactions/Vouchers > Sales"
```

---

## State Management

```
┌──────────────────────────────────────────────┐
│         Alpine.js Global Stores              │
├──────────────────────────────────────────────┤
│                                              │
│  $store.menu {                               │
│    activeMenu: 'masters' | 'reports' | null  │
│    structure: { ... menu items ... }         │
│  }                                           │
│                                              │
│  $store.nav {                                │
│    currentView: 'voucher-payment'            │
│    breadcrumbs: [                            │
│      { label: 'Gateway', view: 'dashboard' } │
│      { label: 'Payment', view: 'voucher-..' }│
│    ]                                         │
│  }                                           │
│                                              │
│  $store.keyboard {                           │
│    shortcuts: {                              │
│      'F5': () => nav.navigateTo(...)         │
│      'Alt+R': () => menu.openMenu(...)       │
│    }                                         │
│  }                                           │
│                                              │
└──────────────────────────────────────────────┘
```

---

## Integration Points for Other Systems

```
┌─────────────────────────────────────────────────────────┐
│                   Gateway Menu System                    │
│                    (menu.js + UI)                        │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─── Integrates with ────┐
               │                         │
               ▼                         ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │   keyboard.js    │    │  Workspace Views     │
    │   (other agent)  │    │  (vouchers, reports) │
    │                  │    │                      │
    │  - F-key handlers│    │  - Payment form      │
    │  - Alt combos    │    │  - Trial Balance     │
    │  - Navigation    │    │  - Ledger CRUD       │
    └──────────────────┘    └──────────────────────┘
               │                         │
               └─────────┬───────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │   AI Chat        │
               │   (triggers nav) │
               └──────────────────┘
```

---

**Legend:**
- `→` Navigation/Flow
- `├─` Menu branch
- `│` Hierarchy
- `▼` Downward flow
- `[...]` UI Component
- `$store.x` Alpine.js store

---

**Files:**
- `/static/menu.js` - Core logic
- `/static/index.html` - UI implementation
- `/static/menu-components.html` - Reusable components
- `/static/status-bar.html` - Status bar template
