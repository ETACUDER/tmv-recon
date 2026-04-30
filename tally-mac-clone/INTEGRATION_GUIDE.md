# Masters Management - Quick Integration Guide

## What Was Built

Complete masters management system with:
- Ledgers (list, create, edit, delete)
- Groups (tree view, CRUD)
- Cost Centers (list, CRUD)
- Currencies (list, CRUD)  
- Stock Items (placeholder)
- Keyboard navigation (Alt+K, Enter, Esc, Tab)

## Files Already Modified

✅ `src/tally_mac_clone/app.py` - Added:
- Ledger update/delete endpoints
- Group CRUD endpoints (POST, GET, PUT, DELETE)
- GroupCreate model

## Files To Manually Integrate

### 1. Complete API Endpoints

**File:** `masters_api_additions.py`

**Action:** Copy the remaining endpoint code into `app.py` before `if __name__ == "__main__":`

**Endpoints to add:**
- Cost center GET/PUT/DELETE
- Currency GET/PUT/DELETE

**Quick method:**
```bash
# View the file
cat masters_api_additions.py

# Then manually copy-paste into app.py at line ~1300 (before if __name__)
```

### 2. Frontend UI Components

**File:** `masters_ui.html`

**Action:** Add UI components to `src/tally_mac_clone/static/index.html`

**Location 1 - Add Masters Tab (line ~226):**
```html
<!-- After Purchase (F9) button, before Reports button -->
<button
    @click="workspaceMode = 'masters'"
    :class="workspaceMode === 'masters' ? 'bg-blue-50 text-blue-700 border-blue-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'"
    class="px-4 py-2 rounded-lg border font-medium text-sm transition-colors">
    Masters (Alt+K)
</button>
```

**Location 2 - Add Masters Views (after dashboard view, line ~280):**
Copy all view components from `masters_ui.html` into the workspace content section.

### 3. JavaScript Functionality

**File:** `masters_js.js`

**Action:** Merge into `index.html` script section (starting line ~624)

**In appData() return object, add:**
```javascript
// Add all properties from masters_js.js
mastersSubMode: null,
ledgers: [],
groups: [],
// ... etc

// Add all methods from masters_js.js
fetchLedgers() { ... },
createNewLedger() { ... },
// ... etc

// Add init() method
init() {
    this.initKeyboardShortcuts();
    this.$watch('workspaceMode', (value) => {
        if (value === 'masters') {
            this.loadMastersData();
        }
    });
}
```

## Automated Integration Script

**Option:** Create a simple merge script:

```bash
#!/bin/bash
# merge_masters.sh

echo "Backing up files..."
cp src/tally_mac_clone/app.py src/tally_mac_clone/app.py.backup
cp src/tally_mac_clone/static/index.html src/tally_mac_clone/static/index.html.backup

echo "Files backed up. Now manually merge:"
echo "1. masters_api_additions.py → app.py"
echo "2. masters_ui.html → index.html (2 locations)"
echo "3. masters_js.js → index.html (script section)"
echo ""
echo "See INTEGRATION_GUIDE.md for details"
```

## Testing After Integration

```bash
# 1. Start server
cd /Volumes/CRESCENT/dev/project-sonnet/tmv-recon/tally-mac-clone
python -m src.tally_mac_clone.app

# 2. Open browser
open http://localhost:8000

# 3. Test keyboard shortcut
# Press Alt+K → Should show Masters menu

# 4. Test Ledgers
# Click "Ledgers" → Should show list
# Click "Create" → Should show form
# Fill form → Tab between fields
# Press Enter → Should save
# Press Esc → Should cancel

# 5. Test Groups
# Click "Groups" → Should show tree
# Click "Create" → Should show form

# 6. Test API directly
curl http://localhost:8000/api/ledgers
curl http://localhost:8000/api/groups
```

## Manual Integration Steps

### Step 1: API Endpoints (5 minutes)

1. Open `src/tally_mac_clone/app.py`
2. Find line with `if __name__ == "__main__":`
3. Copy all code from `masters_api_additions.py`
4. Paste BEFORE the `if __name__` line
5. Save file

### Step 2: UI Components (10 minutes)

1. Open `src/tally_mac_clone/static/index.html`
2. Find line ~226 (after Purchase button)
3. Add Masters tab button
4. Find line ~280 (after dashboard view)
5. Copy all views from `masters_ui.html`
6. Paste after trial-balance view
7. Save file

### Step 3: JavaScript (15 minutes)

1. Still in `index.html`
2. Find line ~624 (inside `function appData()`)
3. After `workspaceMode: 'dashboard',` add:
   - `mastersSubMode: null,`
   - `ledgers: [],`
   - `groups: [],`
   - All other properties from `masters_js.js`
4. After `startResize()` method, add all methods from `masters_js.js`
5. Add `init()` method at the end
6. Save file

### Step 4: Test (5 minutes)

1. Restart server
2. Open browser
3. Press Alt+K
4. Test create/edit/delete for each master type

## Troubleshooting

**Issue:** Alt+K doesn't work
- **Fix:** Check `initKeyboardShortcuts()` is called in `init()`
- **Fix:** Ensure `x-init="init()"` is on body tag

**Issue:** API endpoints return 404
- **Fix:** Check endpoints were added to `app.py`
- **Fix:** Restart server

**Issue:** Forms don't show data
- **Fix:** Check `fetchLedgers()` etc are called in `loadMastersData()`
- **Fix:** Check API responses in browser console

**Issue:** Save doesn't work
- **Fix:** Check fetch URL matches API endpoint
- **Fix:** Check request body has correct fields
- **Fix:** Check console for errors

## Quick Reference

**Keyboard Shortcuts:**
- Alt+K: Masters
- Alt+C: Create
- Enter: Save
- Esc: Cancel
- Tab: Next field

**API Endpoints:**
```
GET    /api/ledgers
POST   /api/ledgers
PUT    /api/ledgers/{id}
DELETE /api/ledgers/{id}

GET    /api/groups
POST   /api/groups
PUT    /api/groups/{id}
DELETE /api/groups/{id}

GET    /api/cost-centers
POST   /api/cost-centers
PUT    /api/cost-centers/{id}
DELETE /api/cost-centers/{id}

GET    /api/currencies
POST   /api/currencies
PUT    /api/currencies/{id}
DELETE /api/currencies/{id}
```

## Verification Checklist

After integration, verify:
- [ ] Server starts without errors
- [ ] Alt+K opens Masters menu
- [ ] Clicking Ledgers shows list
- [ ] Create button opens form
- [ ] Save creates new ledger
- [ ] Edit button loads form
- [ ] Delete removes ledger
- [ ] Same for Groups
- [ ] Same for Cost Centers
- [ ] Same for Currencies
- [ ] Keyboard nav works (Tab, Enter, Esc)
- [ ] Search filters ledgers
- [ ] Groups show tree structure
- [ ] Error messages display

## Need Help?

Check these files:
- `MASTERS_IMPLEMENTATION_SUMMARY.md` - Full documentation
- `masters_api_additions.py` - API code reference
- `masters_ui.html` - UI code reference
- `masters_js.js` - JavaScript reference

## Estimated Time

- API integration: 5 min
- UI integration: 10 min
- JS integration: 15 min
- Testing: 5 min
- **Total: ~35 minutes**

---

**Status:** Ready for manual integration
**Last Updated:** 2026-04-30
