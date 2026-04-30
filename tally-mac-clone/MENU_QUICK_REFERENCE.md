# Gateway Menu System - Quick Reference

## For Developers Building Voucher/Report Views

---

## How to Add a New View

### 1. Register in Menu Structure (`/static/menu.js`)

Add to appropriate submenu:

```javascript
{
    id: 'my-feature',
    label: 'My Feature',
    shortcut: 'Alt+F',  // optional
    view: 'category-my-feature'  // view ID
}
```

### 2. Create View in Workspace

In `index.html` or component file:

```html
<div x-show="$store.nav.currentView === 'category-my-feature'" class="space-y-6">
    <h2 class="text-2xl font-bold">My Feature</h2>
    <!-- Your content here -->
</div>
```

### 3. Add Keyboard Shortcut (Optional)

In `/static/menu.js` keyboard store:

```javascript
'Alt+F': () => Alpine.store('nav').navigateTo('category-my-feature', 'My Feature')
```

---

## Navigation API

### Navigate to View

```javascript
// From Alpine component
@click="$store.nav.navigateTo('voucher-payment', 'Payment')"

// From JavaScript
Alpine.store('nav').navigateTo('voucher-payment', 'Payment')
```

### Navigate Back

```javascript
// Go back one level
@click="$store.nav.goBack()"

// Go to specific breadcrumb
@click="$store.nav.navigateBack(index)"
```

### Check Current View

```javascript
// In template
x-show="$store.nav.currentView === 'dashboard'"

// In JavaScript
if (Alpine.store('nav').currentView === 'voucher-sales') {
    // Do something
}
```

---

## Menu API

### Open Menu

```javascript
@click="$store.menu.openMenu('masters')"
@click="$store.menu.openMenu('reports')"
```

### Close All Menus

```javascript
@click="$store.menu.closeMenus()"
```

### Check Active Menu

```javascript
x-show="$store.menu.activeMenu === 'gateway'"
```

---

## View Naming Convention

**Pattern:** `{category}-{name}`

**Categories:**
- `voucher-*` - Voucher screens (payment, sales, etc.)
- `report-*` - Reports (trial-balance, day-book, etc.)
- `masters-*` - Master data (ledgers, groups, etc.)
- `utilities-*` - Utilities (settings, backup, etc.)
- `import-*` / `export-*` - Import/Export screens

**Examples:**
```
voucher-payment
voucher-sales
report-trial-balance
report-balance-sheet
masters-ledgers
masters-groups
utilities-settings
import-excel
export-pdf
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Alt+G | Gateway/Dashboard |
| Alt+K | Masters Menu |
| Alt+R | Reports Menu |
| Alt+X | Import/Export |
| Alt+U | Utilities |
| F4 | Contra Voucher |
| F5 | Payment Voucher |
| F6 | Receipt Voucher |
| F7 | Journal Voucher |
| F8 | Sales Voucher |
| F9 | Purchase Voucher |
| F12 | Settings |
| ESC | Back/Close |

---

## Common Patterns

### Voucher Entry Screen

```html
<div x-show="$store.nav.currentView === 'voucher-payment'" class="p-6">
    <div class="max-w-4xl mx-auto">
        <h2 class="text-2xl font-bold text-gray-900">Payment Voucher</h2>
        <p class="text-gray-600 mt-1">Record money out transactions</p>

        <form class="mt-6 bg-white rounded-lg shadow p-6 space-y-4">
            <!-- Form fields -->
        </form>

        <!-- Bottom actions -->
        <div class="mt-4 flex gap-2">
            <button class="px-4 py-2 bg-blue-600 text-white rounded">
                Save (Ctrl+A)
            </button>
            <button
                @click="$store.nav.goBack()"
                class="px-4 py-2 border border-gray-300 rounded">
                Cancel (ESC)
            </button>
        </div>
    </div>
</div>
```

### Report View

```html
<div x-show="$store.nav.currentView === 'report-trial-balance'" class="p-6">
    <div class="flex items-center justify-between mb-6">
        <div>
            <h2 class="text-2xl font-bold">Trial Balance</h2>
            <p class="text-gray-600">As on <span x-text="currentDate"></span></p>
        </div>
        <button class="px-4 py-2 border rounded flex items-center gap-2">
            <svg class="w-4 h-4"><!-- icon --></svg>
            Export (Alt+E)
        </button>
    </div>

    <div class="bg-white rounded-lg shadow overflow-hidden">
        <table class="w-full">
            <!-- Table content -->
        </table>
    </div>
</div>
```

### Masters List View

```html
<div x-show="$store.nav.currentView === 'masters-ledgers'" class="p-6">
    <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold">Ledgers</h2>
        <div class="flex gap-2">
            <input
                type="text"
                placeholder="Search ledgers..."
                class="px-4 py-2 border rounded" />
            <button class="px-4 py-2 bg-blue-600 text-white rounded">
                Create (Alt+C)
            </button>
        </div>
    </div>

    <div class="bg-white rounded-lg shadow overflow-hidden">
        <!-- List items -->
    </div>
</div>
```

---

## Breadcrumb Integration

Breadcrumbs auto-generate, but you can customize:

```javascript
// In menu.js, update _getParentLabel() to add new categories
_getParentLabel(type) {
    const labels = {
        'voucher': 'Transactions/Vouchers',
        'report': 'Reports',
        'masters': 'Masters',
        'mycat': 'My Category',  // Add custom
        // ...
    };
    return labels[type] || null;
}
```

---

## Linking from Chat to Views

In your AI chat response handler:

```javascript
// Example: Chat triggers view change
if (userQuery.includes('sales voucher')) {
    Alpine.store('nav').navigateTo('voucher-sales', 'Sales');
}

if (userQuery.includes('trial balance')) {
    Alpine.store('nav').navigateTo('report-trial-balance', 'Trial Balance');
}
```

---

## Multi-View Workspace

If you need tabs within a view:

```html
<div x-show="$store.nav.currentView === 'voucher-sales'" x-data="{ tab: 'entry' }">
    <!-- Sub-tabs -->
    <div class="flex gap-2 mb-4">
        <button
            @click="tab = 'entry'"
            :class="tab === 'entry' ? 'bg-blue-600 text-white' : 'bg-gray-200'"
            class="px-4 py-2 rounded">
            Entry
        </button>
        <button
            @click="tab = 'preview'"
            :class="tab === 'preview' ? 'bg-blue-600 text-white' : 'bg-gray-200'"
            class="px-4 py-2 rounded">
            Preview
        </button>
    </div>

    <!-- Tab content -->
    <div x-show="tab === 'entry'">...</div>
    <div x-show="tab === 'preview'">...</div>
</div>
```

---

## Status Bar Integration

Include `/static/status-bar.html` at bottom of layout:

```html
<div class="h-screen flex flex-col">
    <header>...</header>
    <nav><!-- menu --></nav>
    <main class="flex-1 overflow-auto">
        <!-- workspace -->
    </main>

    <!-- Include status bar -->
    <?php include 'status-bar.html'; ?>
</div>
```

---

## Testing Your View

1. Add menu item in `menu.js`
2. Create view in workspace
3. Test navigation:
   - Click menu item
   - Check breadcrumb updates
   - Press ESC to go back
   - Test keyboard shortcut if added

4. Verify:
   - View renders correctly
   - Breadcrumb shows proper hierarchy
   - ESC goes back
   - Navigation persists state

---

## Common Issues

### View not showing?
- Check view name matches exactly: `$store.nav.currentView === 'your-view-id'`
- Ensure `x-show` not `x-if` for performance
- Verify menu.js loaded before Alpine

### Keyboard shortcuts not working?
- Ensure menu.js loaded
- Check browser console for errors
- Verify shortcut registered in `shortcuts` object

### Breadcrumbs wrong?
- Check view naming follows `category-name` pattern
- Verify `_getParentLabel()` has your category
- Test `_formatLabel()` with your view name

---

## Performance Tips

- Use `x-show` not `x-if` to keep views in DOM
- Lazy load heavy reports
- Debounce search inputs
- Use Alpine `x-cloak` to prevent flash

---

**Need Help?** Check `/GATEWAY_MENU_SYSTEM.md` for full documentation.
