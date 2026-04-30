# Gateway Menu Integration Checklist

For developers integrating Gateway menu with voucher/report views.

---

## ✅ Already Complete

- [x] Menu structure defined in `/static/menu.js`
- [x] Alpine.js stores created (menu, nav, keyboard)
- [x] Menu bar integrated in `index.html`
- [x] Keyboard shortcuts configured (Alt+G/K/R/X/U, F4-F9, F12, ESC)
- [x] Breadcrumb navigation implemented
- [x] Menu dropdowns with transitions
- [x] Status bar component created
- [x] Documentation written

---

## 🔲 Next Steps for Integration

### Step 1: Install Status Bar
Add status bar to bottom of layout in `index.html`:

```html
<!-- Before closing main container div -->
<footer class="bg-gray-800 text-gray-200 border-t border-gray-700">
    <!-- Copy content from /static/status-bar.html -->
</footer>
```

**File:** `/static/status-bar.html`  
**Location:** Bottom of `<div class="h-screen flex flex-col">`

---

### Step 2: Create Voucher Views

Create view containers in workspace area of `index.html`:

```html
<!-- Payment Voucher -->
<div x-show="$store.nav.currentView === 'voucher-payment'" class="p-6">
    <h2 class="text-2xl font-bold">Payment Voucher</h2>
    <!-- Form fields here -->
</div>

<!-- Receipt Voucher -->
<div x-show="$store.nav.currentView === 'voucher-receipt'" class="p-6">
    <h2 class="text-2xl font-bold">Receipt Voucher</h2>
    <!-- Form fields here -->
</div>

<!-- Sales Voucher -->
<div x-show="$store.nav.currentView === 'voucher-sales'" class="p-6">
    <h2 class="text-2xl font-bold">Sales Voucher</h2>
    <!-- Form fields here -->
</div>
```

**Required Views:**
- [ ] voucher-payment (F5)
- [ ] voucher-receipt (F6)
- [ ] voucher-journal (F7)
- [ ] voucher-sales (F8)
- [ ] voucher-purchase (F9)
- [ ] voucher-contra (F4)

---

### Step 3: Create Report Views

```html
<!-- Trial Balance -->
<div x-show="$store.nav.currentView === 'report-trial-balance'" class="p-6">
    <h2 class="text-2xl font-bold">Trial Balance</h2>
    <!-- Report table here -->
</div>

<!-- Day Book -->
<div x-show="$store.nav.currentView === 'report-day-book'" class="p-6">
    <h2 class="text-2xl font-bold">Day Book</h2>
    <!-- Transaction list here -->
</div>
```

**Required Views:**
- [ ] report-day-book
- [ ] report-trial-balance
- [ ] report-balance-sheet
- [ ] report-profit-loss
- [ ] report-cash-flow
- [ ] report-all-registers

---

### Step 4: Create Masters Views

```html
<!-- Ledgers List -->
<div x-show="$store.nav.currentView === 'masters-ledgers'" class="p-6">
    <h2 class="text-2xl font-bold">Ledgers</h2>
    <!-- Ledger list with search -->
</div>

<!-- Groups -->
<div x-show="$store.nav.currentView === 'masters-groups'" class="p-6">
    <h2 class="text-2xl font-bold">Groups</h2>
    <!-- Group hierarchy tree -->
</div>
```

**Required Views:**
- [ ] masters-ledgers
- [ ] masters-groups
- [ ] masters-stock-items
- [ ] masters-units
- [ ] masters-cost-centers
- [ ] masters-currencies

---

### Step 5: Update Chat Integration

Modify chat response handler in `index.html`:

```javascript
// In sendMessage() function
if (userQuery.includes('payment voucher')) {
    Alpine.store('nav').navigateTo('voucher-payment', 'Payment');
    response = 'Opening Payment Voucher form...';
}

if (userQuery.includes('trial balance')) {
    Alpine.store('nav').navigateTo('report-trial-balance', 'Trial Balance');
    response = 'Loading Trial Balance...';
}
```

---

### Step 6: Integrate keyboard.js

When keyboard.js is ready:

```javascript
// In keyboard.js
function keyboardNav() {
    return {
        init() {
            // Hook into Alpine stores
            const shortcuts = Alpine.store('keyboard').shortcuts;

            // Register handlers
            Object.keys(shortcuts).forEach(key => {
                this.registerKey(key, shortcuts[key]);
            });
        }
    }
}
```

---

### Step 7: Add View-Specific Shortcuts

For forms, add Ctrl+A (Accept), Ctrl+D (Delete):

```html
<div x-show="$store.nav.currentView === 'voucher-payment'"
     @keydown.ctrl.a.prevent="saveVoucher()"
     @keydown.ctrl.d.prevent="deleteVoucher()">
    <!-- Voucher form -->
</div>
```

---

## Testing Checklist

After integration, verify:

### Menu Navigation
- [ ] Gateway menu opens/closes
- [ ] Masters submenu expands
- [ ] Reports submenu expands
- [ ] Import/Export submenu expands
- [ ] Utilities submenu expands

### Keyboard Shortcuts
- [ ] Alt+G goes to dashboard
- [ ] Alt+K opens Masters menu
- [ ] Alt+R opens Reports menu
- [ ] F5 opens Payment voucher
- [ ] F6 opens Receipt voucher
- [ ] F7 opens Journal voucher
- [ ] F8 opens Sales voucher
- [ ] F9 opens Purchase voucher
- [ ] F12 opens Settings
- [ ] ESC closes menus
- [ ] ESC navigates back

### Breadcrumb Navigation
- [ ] Breadcrumbs update on view change
- [ ] Click breadcrumb navigates back
- [ ] Current view highlighted
- [ ] ESC hint visible

### Views Rendering
- [ ] Dashboard shows on load
- [ ] Voucher views render correctly
- [ ] Report views render correctly
- [ ] Masters views render correctly
- [ ] Only one view visible at a time
- [ ] No flash of content

### Chat Integration
- [ ] Chat can navigate to views
- [ ] Chat messages trigger correct views
- [ ] Navigation persists after chat interaction

---

## Common Issues & Solutions

### Menu not opening
**Check:**
- Alpine.js loaded before menu.js
- No console errors
- `$store.menu` exists in console

**Fix:**
```javascript
// In browser console
Alpine.store('menu')  // Should return menu store
```

### View not showing
**Check:**
- View name matches exactly
- Using `x-show` not `x-if`
- `currentView` value in console

**Fix:**
```javascript
// In browser console
Alpine.store('nav').currentView  // Check current value
Alpine.store('nav').navigateTo('voucher-payment', 'Payment')  // Test
```

### Keyboard shortcuts not working
**Check:**
- menu.js loaded
- No key conflicts with browser
- `init()` called

**Fix:**
```javascript
// In browser console
Alpine.store('keyboard').shortcuts  // Should show all shortcuts
```

### Breadcrumbs wrong
**Check:**
- View naming follows `category-name` pattern
- `_getParentLabel()` has your category

**Fix:**
Add to `_getParentLabel()` in menu.js:
```javascript
const labels = {
    'voucher': 'Transactions/Vouchers',
    'mycategory': 'My Category',  // Add here
    // ...
};
```

---

## File Reference

| File | Purpose |
|------|---------|
| `/static/menu.js` | Core menu logic, Alpine stores |
| `/static/index.html` | Menu UI, workspace area |
| `/static/menu-components.html` | Reusable components |
| `/static/status-bar.html` | Bottom status bar |
| `GATEWAY_MENU_SYSTEM.md` | Full documentation |
| `MENU_QUICK_REFERENCE.md` | Developer guide |
| `MENU_STRUCTURE_DIAGRAM.md` | Visual diagrams |
| `GATEWAY_SUMMARY.md` | Build summary |

---

## Quick Start Code Snippets

### Add New Menu Item
```javascript
// In menu.js structure
{
    id: 'my-feature',
    label: 'My Feature',
    view: 'category-my-feature'
}
```

### Add New View
```html
<div x-show="$store.nav.currentView === 'category-my-feature'" class="p-6">
    <h2 class="text-2xl font-bold">My Feature</h2>
    <!-- Content -->
</div>
```

### Navigate Programmatically
```javascript
Alpine.store('nav').navigateTo('voucher-sales', 'Sales')
```

### Open Menu Programmatically
```javascript
Alpine.store('menu').openMenu('reports')
```

---

## Support

**Documentation:** See `MENU_QUICK_REFERENCE.md`  
**Diagrams:** See `MENU_STRUCTURE_DIAGRAM.md`  
**Full API:** See `GATEWAY_MENU_SYSTEM.md`

---

**Status:** Ready for voucher/report view integration  
**Last Updated:** April 30, 2026  
**Next Agent:** Build voucher forms and report views
