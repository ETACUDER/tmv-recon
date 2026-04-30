# Company Management - Quick Integration Guide

## Overview
This guide shows how to integrate the company management module into your existing RecordX.Finance application.

## Files Created

### Backend (Python)
- **Modified:** `/src/tally_mac_clone/app.py`
  - Added `CompanyCreate` model
  - Added `POST /api/companies` endpoint
  - Enhanced `GET /api/companies` with more fields
  - Added `DELETE /api/companies/{id}`
  - Added `POST /api/companies/{id}/set-active`

### Frontend (HTML/JS)
- **Created:** `/static/components/company-management.html` - Company info form
- **Created:** `/static/components/company-switcher.html` - Company switcher modal
- **Created:** `/static/components/settings-screen.html` - Settings screen
- **Created:** `/static/js/company-management.js` - Management logic
- **Modified:** `/static/status-bar.html` - Enhanced with company info

## Integration Steps

### 1. Load JavaScript Module

Add to `<head>` section of `index.html`:

```html
<script src="/static/js/company-management.js"></script>
```

### 2. Update Alpine.js Data

Merge company management into your `appData()` function:

```javascript
function appData() {
    return {
        // EXISTING STATE
        leftWidth: 30,
        workspaceMode: 'dashboard',
        // ... keep existing state ...
        
        // ADD COMPANY STATE
        ...window.CompanyManagement.initState(),
        
        // ADD INIT
        async init() {
            await window.CompanyManagement.init(this);
        },
        
        // EXISTING METHODS
        sendMessage() { /* keep */ },
        startResize() { /* keep */ },
        
        // ADD COMPANY METHODS
        openCompanySwitcher() {
            window.CompanyManagement.openCompanySwitcher(this);
        },
        switchCompany(id) {
            return window.CompanyManagement.switchCompany(this, id);
        },
        createNewCompany() {
            window.CompanyManagement.createNewCompany(this);
        },
        editCompany(id) {
            return window.CompanyManagement.editCompany(this, id);
        },
        confirmDeleteCompany(company) {
            window.CompanyManagement.confirmDeleteCompany(this, company);
        },
        deleteCompany() {
            return window.CompanyManagement.deleteCompany(this);
        },
        saveCompanyInfo() {
            return window.CompanyManagement.saveCompanyInfo(this);
        },
        openSettings() {
            return window.CompanyManagement.openSettings(this);
        },
        saveSettings() {
            return window.CompanyManagement.saveSettings(this);
        }
    };
}
```

### 3. Update Body Tag

Add `x-init` to initialize on mount:

```html
<body x-data="appData()" x-init="init()" x-cloak>
```

### 4. Add Workspace Views

In your workspace content area (around line 220-280), add after existing views:

```html
<div class="p-6">
    <!-- EXISTING VIEWS -->
    <div x-show="workspaceMode === 'dashboard'">...</div>
    <div x-show="workspaceMode === 'voucher'">...</div>
    
    <!-- ADD COMPANY INFO VIEW -->
    <template x-if="workspaceMode === 'company-info'">
        <div x-html="await (await fetch('/static/components/company-management.html')).text()"></div>
    </template>

    <!-- ADD SETTINGS VIEW -->
    <template x-if="workspaceMode === 'settings'">
        <div x-html="await (await fetch('/static/components/settings-screen.html')).text()"></div>
    </template>
</div>
```

### 5. Add Company Switcher Modal

Before closing `</body>` tag:

```html
<!-- Company Switcher Modal -->
<div x-html="await (await fetch('/static/components/company-switcher.html')).text()"></div>

</body>
</html>
```

### 6. Update Status Bar

The status bar is already updated with company info. Make sure you're using the latest `/static/status-bar.html`.

## Keyboard Shortcuts

The module adds these shortcuts:
- **F3:** Open company switcher
- **F12:** Open settings
- **ESC:** Close modals

## Testing

1. **Start Server:**
   ```bash
   cd /Volumes/CRESCENT/dev/project-sonnet/tmv-recon/tally-mac-clone
   python -m src.tally_mac_clone.app
   ```

2. **Open Browser:**
   ```
   http://localhost:8000
   ```

3. **Test F3:**
   - Press F3
   - Should show company switcher
   - Create new company
   - Fill form and save
   - Should appear in list

4. **Test F12:**
   - Press F12
   - Should show settings screen
   - Toggle features
   - Save settings

5. **Test Status Bar:**
   - Should show company name
   - Should show FY (e.g., "2026-27")
   - Click F3 button should open switcher

## API Verification

Test the endpoints:

```bash
# List companies
curl http://localhost:8000/api/companies

# Get company details
curl http://localhost:8000/api/companies/1

# Create company
curl -X POST http://localhost:8000/api/companies \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Corp","financial_year_start":"2026-04-01"}'

# Update company
curl -X PATCH http://localhost:8000/api/companies/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Corp"}'

# Delete company
curl -X DELETE http://localhost:8000/api/companies/1

# Set active company
curl -X POST http://localhost:8000/api/companies/1/set-active
```

## Common Issues

### "CompanyManagement is not defined"
**Fix:** Load `company-management.js` before Alpine.js initializes.

### Modals not showing
**Fix:** Check z-index values (should be 50+).

### "Cannot read property 'name' of null"
**Fix:** Ensure `init()` is called on mount.

### Forms not saving
**Fix:** Check browser console for API errors.

## Features Included

- [x] Create/Edit/Delete companies
- [x] Company switcher modal (F3)
- [x] Settings screen (F12)
- [x] Status bar integration
- [x] Financial year display
- [x] All company fields (GSTIN, PAN, CIN, etc.)
- [x] Feature toggles
- [x] GST configuration
- [x] Voucher numbering setup
- [x] Keyboard shortcuts

## Next Steps

After integration:
1. Test all CRUD operations
2. Create multiple companies
3. Switch between companies
4. Configure settings for each company
5. Test keyboard shortcuts

## Documentation

For more details:
- See `COMPANY_MANAGEMENT_IMPLEMENTATION.md` for full documentation
- Check component files for inline comments
- Review `company-management.js` for API methods

## Support

If you encounter issues:
1. Check browser console
2. Check network tab for API errors
3. Verify all files are in correct locations
4. Ensure Alpine.js version is 3.x
5. Clear browser cache

---
**Integration Time:** ~15-20 minutes
**Status:** Ready to integrate
**Last Updated:** 2026-04-30
