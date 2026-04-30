// Tally Keyboard Navigation System
// Based on TALLY_UI_REFERENCE.md patterns

document.addEventListener('alpine:init', () => {
    Alpine.data('keyboardNav', () => ({
        // Navigation state
        escapeStack: [],
        currentView: 'dashboard',
        activeMenu: null,
        statusMessage: 'Ready',

        // Key mappings reference
        keyMappings: {
            'F1': { name: 'Help', action: 'showHelp' },
            'F2': { name: 'Date', action: 'changeDate' },
            'F3': { name: 'Company', action: 'selectCompany' },
            'F4': { name: 'Contra', action: 'createContra' },
            'F5': { name: 'Payment', action: 'createPayment' },
            'F6': { name: 'Receipt', action: 'createReceipt' },
            'F7': { name: 'Journal', action: 'createJournal' },
            'F8': { name: 'Sales', action: 'createSales' },
            'F9': { name: 'Purchase', action: 'createPurchase' },
            'F10': { name: 'Reversing', action: 'createReversing' },
            'F11': { name: 'Features', action: 'showFeatures' },
            'F12': { name: 'Config', action: 'showConfig' }
        },

        init() {
            // Global keyboard event handler
            window.addEventListener('keydown', this.handleKeyDown.bind(this));
            this.setStatusBar();
        },

        handleKeyDown(e) {
            const key = e.key;
            const alt = e.altKey;
            const ctrl = e.ctrlKey;

            // Prevent default for function keys and shortcuts
            if (key.startsWith('F') || (alt && ['g', 'k', 'r', 'x', 'u', 'd', 'f', 'e', 'c', 'p', 'a'].includes(key.toLowerCase()))) {
                e.preventDefault();
            }

            // Function keys (F1-F12)
            if (key.startsWith('F')) {
                this.handleFunctionKey(key);
                return;
            }

            // Alt combinations
            if (alt) {
                this.handleAltKey(key.toLowerCase());
                return;
            }

            // Ctrl combinations
            if (ctrl) {
                this.handleCtrlKey(key.toLowerCase());
                return;
            }

            // Escape key
            if (key === 'Escape') {
                this.handleEscape();
                return;
            }
        },

        handleFunctionKey(key) {
            const mapping = this.keyMappings[key];
            if (!mapping) return;

            this.statusMessage = `${mapping.name} activated`;
            this.setStatusBar();

            switch (key) {
                case 'F1':
                    this.showHelp();
                    break;
                case 'F2':
                    this.changeDate();
                    break;
                case 'F3':
                    this.selectCompany();
                    break;
                case 'F4':
                    this.createVoucher('contra');
                    break;
                case 'F5':
                    this.createVoucher('payment');
                    break;
                case 'F6':
                    this.createVoucher('receipt');
                    break;
                case 'F7':
                    this.createVoucher('journal');
                    break;
                case 'F8':
                    this.createVoucher('sales');
                    break;
                case 'F9':
                    this.createVoucher('purchase');
                    break;
                case 'F10':
                    this.createVoucher('reversing');
                    break;
                case 'F11':
                    this.showFeatures();
                    break;
                case 'F12':
                    this.showConfig();
                    break;
            }
        },

        handleAltKey(key) {
            switch (key) {
                case 'g':
                    this.showGateway();
                    break;
                case 'k':
                    this.showMasters();
                    break;
                case 'r':
                    this.showReports();
                    break;
                case 'x':
                    this.showImportExport();
                    break;
                case 'u':
                    this.showUtilities();
                    break;
                case 'd':
                    this.deleteCurrentItem();
                    break;
                case 'f':
                    this.fillVoucherDetails();
                    break;
                case 'e':
                    this.exportReport();
                    break;
                case 'c':
                    this.createNew();
                    break;
                case 'p':
                    this.printReport();
                    break;
                case 'a':
                    this.acceptSave();
                    break;
            }
        },

        handleCtrlKey(key) {
            switch (key) {
                case 'a':
                    this.acceptSave();
                    break;
                case 'q':
                    this.quit();
                    break;
            }
        },

        handleEscape() {
            if (this.escapeStack.length > 0) {
                const previousView = this.escapeStack.pop();
                this.currentView = previousView;
                this.statusMessage = 'Back';
            } else {
                this.statusMessage = 'Already at top level';
            }
            this.setStatusBar();
            this.closeActiveMenu();
        },

        // Navigation actions
        createVoucher(type) {
            this.escapeStack.push(this.currentView);
            this.currentView = 'voucher';

            // Get parent Alpine instance to change workspace mode
            const appData = Alpine.$data(document.querySelector('[x-data="appData()"]'));
            if (appData) {
                appData.workspaceMode = 'voucher';
                appData.voucherType = type;
            }

            this.statusMessage = `Creating ${type} voucher`;
            this.setStatusBar();
        },

        showGateway() {
            this.toggleMenu('gateway');
            this.statusMessage = 'Gateway menu';
            this.setStatusBar();
        },

        showMasters() {
            this.toggleMenu('masters');
            this.statusMessage = 'Masters menu';
            this.setStatusBar();
        },

        showReports() {
            this.toggleMenu('reports');
            this.statusMessage = 'Reports menu';
            this.setStatusBar();
        },

        showImportExport() {
            this.toggleMenu('import');
            this.statusMessage = 'Import/Export menu';
            this.setStatusBar();
        },

        showUtilities() {
            this.statusMessage = 'Utilities';
            this.setStatusBar();
        },

        showHelp() {
            this.statusMessage = 'Help: F1-F12 function keys, Alt+G/K/R/X/U menus, Esc=Back, Ctrl+A=Accept';
            this.setStatusBar();
        },

        changeDate() {
            this.statusMessage = 'Change date (F2)';
            this.setStatusBar();
        },

        selectCompany() {
            this.statusMessage = 'Select company (F3)';
            this.setStatusBar();
        },

        showFeatures() {
            this.statusMessage = 'Features configuration (F11)';
            this.setStatusBar();
        },

        showConfig() {
            this.statusMessage = 'Settings (F12)';
            this.setStatusBar();
        },

        deleteCurrentItem() {
            this.statusMessage = 'Delete item (Alt+D)';
            this.setStatusBar();
        },

        fillVoucherDetails() {
            this.statusMessage = 'Fill details (Alt+F)';
            this.setStatusBar();
        },

        exportReport() {
            this.statusMessage = 'Export (Alt+E)';
            this.setStatusBar();
        },

        createNew() {
            this.statusMessage = 'Create new (Alt+C)';
            this.setStatusBar();
        },

        printReport() {
            this.statusMessage = 'Print (Alt+P)';
            this.setStatusBar();
        },

        acceptSave() {
            this.statusMessage = 'Save/Accept (Ctrl+A)';
            this.setStatusBar();
        },

        quit() {
            if (confirm('Quit application?')) {
                this.statusMessage = 'Goodbye';
                this.setStatusBar();
            }
        },

        // Menu management
        toggleMenu(menu) {
            if (this.activeMenu === menu) {
                this.activeMenu = null;
            } else {
                this.activeMenu = menu;
            }
        },

        closeActiveMenu() {
            this.activeMenu = null;
        },

        isMenuActive(menu) {
            return this.activeMenu === menu;
        },

        // Status bar
        setStatusBar() {
            // Update status bar dynamically
            this.$nextTick(() => {
                const statusEl = document.getElementById('statusMessage');
                if (statusEl) {
                    statusEl.textContent = this.statusMessage;
                }
            });
        },

        getShortcutHints() {
            return [
                { key: 'F5', label: 'Payment' },
                { key: 'F6', label: 'Receipt' },
                { key: 'F7', label: 'Journal' },
                { key: 'F8', label: 'Sales' },
                { key: 'F9', label: 'Purchase' },
                { key: 'F12', label: 'Config' },
                { key: 'ESC', label: 'Back' },
                { key: 'Alt+G', label: 'Gateway' },
                { key: 'Ctrl+A', label: 'Save' }
            ];
        }
    }));
});
