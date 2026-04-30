// Gateway Menu System for RecordX.Finance Tally Clone
// Manages menu structure, navigation, and keyboard shortcuts

document.addEventListener('alpine:init', () => {
    // Menu Store - manages menu state and navigation
    Alpine.store('menu', {
        // Current active menu
        activeMenu: null,

        // Menu structure matching Tally Gateway
        structure: {
            gateway: {
                label: 'Gateway',
                shortcut: 'Alt+G',
                items: [
                    {
                        id: 'masters',
                        label: 'Masters',
                        shortcut: 'Alt+K',
                        submenu: [
                            { id: 'ledgers', label: 'Ledgers', view: 'masters-ledgers' },
                            { id: 'groups', label: 'Groups', view: 'masters-groups' },
                            { id: 'stock-items', label: 'Stock Items', view: 'masters-stock-items' },
                            { id: 'units', label: 'Units', view: 'masters-units' },
                            { id: 'cost-centers', label: 'Cost Centers', view: 'masters-cost-centers' },
                            { id: 'currencies', label: 'Currencies', view: 'masters-currencies' }
                        ]
                    },
                    {
                        id: 'vouchers',
                        label: 'Transactions/Vouchers',
                        submenu: [
                            { id: 'payment', label: 'Payment', shortcut: 'F5', view: 'voucher-payment' },
                            { id: 'receipt', label: 'Receipt', shortcut: 'F6', view: 'voucher-receipt' },
                            { id: 'journal', label: 'Journal', shortcut: 'F7', view: 'voucher-journal' },
                            { id: 'sales', label: 'Sales', shortcut: 'F8', view: 'voucher-sales' },
                            { id: 'purchase', label: 'Purchase', shortcut: 'F9', view: 'voucher-purchase' },
                            { id: 'contra', label: 'Contra', shortcut: 'F4', view: 'voucher-contra' }
                        ]
                    },
                    {
                        id: 'reports',
                        label: 'Reports',
                        shortcut: 'Alt+R',
                        submenu: [
                            { id: 'day-book', label: 'Day Book', view: 'report-day-book' },
                            { id: 'trial-balance', label: 'Trial Balance', view: 'report-trial-balance' },
                            { id: 'balance-sheet', label: 'Balance Sheet', view: 'report-balance-sheet' },
                            { id: 'profit-loss', label: 'Profit & Loss', view: 'report-profit-loss' },
                            { id: 'cash-flow', label: 'Cash Flow', view: 'report-cash-flow' },
                            { id: 'all-registers', label: 'All Registers', view: 'report-all-registers' }
                        ]
                    },
                    {
                        id: 'import-export',
                        label: 'Import/Export',
                        shortcut: 'Alt+X',
                        submenu: [
                            { id: 'import-excel', label: 'Import Excel', view: 'import-excel' },
                            { id: 'bank-statement', label: 'Bank Statement Import', view: 'bank-statement' },
                            { id: 'import-xml', label: 'Import Tally XML', view: 'import-xml' },
                            { id: 'export-data', label: 'Export Data', view: 'export-data' }
                        ]
                    },
                    {
                        id: 'utilities',
                        label: 'Utilities',
                        shortcut: 'Alt+U',
                        submenu: [
                            { id: 'backup-restore', label: 'Backup/Restore', view: 'utilities-backup' },
                            { id: 'settings', label: 'Settings', shortcut: 'F12', view: 'utilities-settings' }
                        ]
                    }
                ]
            }
        },

        // Open specific menu
        openMenu(menuId) {
            this.activeMenu = this.activeMenu === menuId ? null : menuId;
        },

        // Close all menus
        closeMenus() {
            this.activeMenu = null;
        },

        // Get menu items
        getMenuItems() {
            return this.structure.gateway.items;
        }
    });

    // Navigation Store - manages views and breadcrumbs
    Alpine.store('nav', {
        // Current view
        currentView: 'dashboard',

        // Breadcrumb history
        breadcrumbs: [
            { label: 'Gateway', view: 'dashboard' }
        ],

        // Navigate to a view
        navigateTo(view, label) {
            this.currentView = view;

            // Update breadcrumbs
            const parts = view.split('-');
            const newBreadcrumbs = [{ label: 'Gateway', view: 'dashboard' }];

            if (parts.length > 1) {
                // Add parent breadcrumb
                const parent = this._getParentLabel(parts[0]);
                if (parent) {
                    newBreadcrumbs.push({ label: parent, view: parts[0] });
                }

                // Add current view
                newBreadcrumbs.push({ label: label || this._formatLabel(parts[1]), view: view });
            } else if (view !== 'dashboard') {
                newBreadcrumbs.push({ label: label || this._formatLabel(view), view: view });
            }

            this.breadcrumbs = newBreadcrumbs;

            // Close menus after navigation
            Alpine.store('menu').closeMenus();
        },

        // Navigate back in breadcrumbs
        navigateBack(index) {
            if (index < this.breadcrumbs.length - 1) {
                const target = this.breadcrumbs[index];
                this.navigateTo(target.view, target.label);
            }
        },

        // Go back one level (ESC key handler)
        goBack() {
            if (this.breadcrumbs.length > 1) {
                const previousIndex = this.breadcrumbs.length - 2;
                this.navigateBack(previousIndex);
            }
        },

        // Helper: Get parent label from view type
        _getParentLabel(type) {
            const labels = {
                'voucher': 'Transactions/Vouchers',
                'report': 'Reports',
                'masters': 'Masters',
                'utilities': 'Utilities',
                'import': 'Import/Export',
                'export': 'Import/Export'
            };
            return labels[type] || null;
        },

        // Helper: Format label from kebab-case
        _formatLabel(str) {
            return str
                .split('-')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
        }
    });

    // Keyboard shortcuts store - will integrate with keyboard.js
    Alpine.store('keyboard', {
        // Registered shortcuts
        shortcuts: {
            'Alt+G': () => Alpine.store('nav').navigateTo('dashboard', 'Gateway'),
            'Alt+K': () => Alpine.store('menu').openMenu('masters'),
            'Alt+R': () => Alpine.store('menu').openMenu('reports'),
            'Alt+X': () => Alpine.store('menu').openMenu('import-export'),
            'Alt+U': () => Alpine.store('menu').openMenu('utilities'),
            'F4': () => Alpine.store('nav').navigateTo('voucher-contra', 'Contra'),
            'F5': () => Alpine.store('nav').navigateTo('voucher-payment', 'Payment'),
            'F6': () => Alpine.store('nav').navigateTo('voucher-receipt', 'Receipt'),
            'F7': () => Alpine.store('nav').navigateTo('voucher-journal', 'Journal'),
            'F8': () => Alpine.store('nav').navigateTo('voucher-sales', 'Sales'),
            'F9': () => Alpine.store('nav').navigateTo('voucher-purchase', 'Purchase'),
            'F12': () => Alpine.store('nav').navigateTo('utilities-settings', 'Settings'),
            'Escape': () => {
                // First close menus, then go back if no menus open
                if (Alpine.store('menu').activeMenu) {
                    Alpine.store('menu').closeMenus();
                } else {
                    Alpine.store('nav').goBack();
                }
            }
        },

        // Initialize keyboard handlers
        init() {
            document.addEventListener('keydown', (e) => {
                const key = this._getKeyString(e);

                if (this.shortcuts[key]) {
                    e.preventDefault();
                    this.shortcuts[key]();
                }
            });

            // Close menus on outside click
            document.addEventListener('click', (e) => {
                if (!e.target.closest('[data-menu]')) {
                    Alpine.store('menu').closeMenus();
                }
            });
        },

        // Get key string from event
        _getKeyString(e) {
            const parts = [];

            if (e.ctrlKey) parts.push('Ctrl');
            if (e.altKey) parts.push('Alt');
            if (e.shiftKey) parts.push('Shift');

            // Handle function keys
            if (e.key.startsWith('F') && e.key.length <= 3) {
                parts.push(e.key);
            } else if (e.key === 'Escape') {
                parts.push('Escape');
            } else if (e.key.length === 1) {
                parts.push(e.key.toUpperCase());
            }

            return parts.join('+');
        }
    });
});

// Initialize keyboard shortcuts when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure Alpine is initialized
    setTimeout(() => {
        if (window.Alpine && Alpine.store('keyboard')) {
            Alpine.store('keyboard').init();
        }
    }, 100);
});
