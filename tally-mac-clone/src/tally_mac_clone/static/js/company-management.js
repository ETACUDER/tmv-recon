/**
 * Company Management Module
 * Handles company CRUD operations, switcher, and settings
 */

window.CompanyManagement = {
    /**
     * Initialize company management state
     */
    initState() {
        return {
            // Company data
            companies: [],
            activeCompany: null,
            currencies: [],
            financialYear: '2026-27',

            // UI state
            showCompanySwitcher: false,
            showDeleteConfirm: false,
            companyToDelete: null,

            // Forms
            companyForm: this.getEmptyCompanyForm(),
            settings: this.getEmptySettings(),
        };
    },

    /**
     * Get empty company form
     */
    getEmptyCompanyForm() {
        return {
            id: null,
            name: '',
            mailing_name: '',
            address: '',
            state: '',
            country: 'India',
            pincode: '',
            phone: '',
            email: '',
            website: '',
            gstin: '',
            pan: '',
            cin: '',
            tan: '',
            gst_registration_type: '',
            financial_year_start: '2026-04-01',
            books_beginning_from: '2026-04-01',
            base_currency_id: null,
            maintain_bill_wise: true,
            use_cost_centers: false,
            enable_multi_currency: false,
            maintain_inventory: false,
            maintain_payroll: false,
            enable_gst: true,
            maintain_accounts_only: false,
            tally_vault_password: ''
        };
    },

    /**
     * Get empty settings
     */
    getEmptySettings() {
        return {
            maintain_inventory: false,
            maintain_payroll: false,
            use_cost_centers: false,
            maintain_bill_wise: true,
            enable_multi_currency: false,
            enable_gst: true,
            gstin: '',
            gst_registration_type: '',
            gst_filing_frequency: 'Monthly'
        };
    },

    /**
     * Initialize company management
     */
    async init(alpine) {
        await this.loadCompanies(alpine);
        await this.loadCurrencies(alpine);

        if (alpine.companies.length > 0) {
            alpine.activeCompany = alpine.companies[0];
            this.updateFinancialYear(alpine);
        }

        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts(alpine);
    },

    /**
     * Load companies from API
     */
    async loadCompanies(alpine) {
        try {
            const response = await fetch('/api/companies');
            if (!response.ok) throw new Error('Failed to load companies');
            alpine.companies = await response.json();
        } catch (error) {
            console.error('Failed to load companies:', error);
            this.showError('Failed to load companies');
        }
    },

    /**
     * Load currencies from API
     */
    async loadCurrencies(alpine) {
        try {
            const response = await fetch('/api/currencies');
            if (!response.ok) throw new Error('Failed to load currencies');
            alpine.currencies = await response.json();
        } catch (error) {
            console.error('Failed to load currencies:', error);
        }
    },

    /**
     * Open company switcher modal
     */
    openCompanySwitcher(alpine) {
        alpine.showCompanySwitcher = true;
    },

    /**
     * Switch to a different company
     */
    async switchCompany(alpine, companyId) {
        try {
            const response = await fetch(`/api/companies/${companyId}/set-active`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to switch company');

            const data = await response.json();
            alpine.activeCompany = alpine.companies.find(c => c.id === companyId);
            alpine.showCompanySwitcher = false;
            this.updateFinancialYear(alpine);
            this.showSuccess(data.message);

            // Reload data for new company
            window.location.reload();
        } catch (error) {
            console.error('Failed to switch company:', error);
            this.showError('Failed to switch company');
        }
    },

    /**
     * Create new company
     */
    createNewCompany(alpine) {
        alpine.companyForm = this.getEmptyCompanyForm();
        alpine.workspaceMode = 'company-info';
        alpine.showCompanySwitcher = false;
    },

    /**
     * Edit existing company
     */
    async editCompany(alpine, companyId) {
        try {
            const response = await fetch(`/api/companies/${companyId}`);
            if (!response.ok) throw new Error('Failed to load company');

            const company = await response.json();
            alpine.companyForm = {...company};
            alpine.workspaceMode = 'company-info';
            alpine.showCompanySwitcher = false;
        } catch (error) {
            console.error('Failed to load company:', error);
            this.showError('Failed to load company details');
        }
    },

    /**
     * Confirm delete company
     */
    confirmDeleteCompany(alpine, company) {
        alpine.companyToDelete = company;
        alpine.showDeleteConfirm = true;
    },

    /**
     * Delete company
     */
    async deleteCompany(alpine) {
        if (!alpine.companyToDelete) return;

        try {
            const response = await fetch(`/api/companies/${alpine.companyToDelete.id}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete company');

            const data = await response.json();
            alpine.showDeleteConfirm = false;
            alpine.companyToDelete = null;

            await this.loadCompanies(alpine);

            if (alpine.activeCompany?.id === alpine.companyToDelete.id) {
                alpine.activeCompany = alpine.companies[0] || null;
            }

            this.showSuccess(data.message);
        } catch (error) {
            console.error('Failed to delete company:', error);
            this.showError('Failed to delete company');
        }
    },

    /**
     * Save company info
     */
    async saveCompanyInfo(alpine) {
        try {
            const url = alpine.companyForm.id
                ? `/api/companies/${alpine.companyForm.id}`
                : '/api/companies';
            const method = alpine.companyForm.id ? 'PATCH' : 'POST';

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(alpine.companyForm)
            });

            if (!response.ok) throw new Error('Failed to save company');

            const data = await response.json();
            this.showSuccess(data.message);

            await this.loadCompanies(alpine);
            alpine.workspaceMode = 'dashboard';

            // If this was the active company, refresh it
            if (alpine.companyForm.id === alpine.activeCompany?.id) {
                alpine.activeCompany = alpine.companies.find(c => c.id === alpine.companyForm.id);
                this.updateFinancialYear(alpine);
            }
        } catch (error) {
            console.error('Failed to save company:', error);
            this.showError('Failed to save company');
        }
    },

    /**
     * Open settings screen
     */
    async openSettings(alpine) {
        alpine.workspaceMode = 'settings';

        if (alpine.activeCompany) {
            try {
                const response = await fetch(`/api/companies/${alpine.activeCompany.id}/settings`);
                if (response.ok) {
                    alpine.settings = await response.json();
                }
            } catch (error) {
                console.error('Failed to load settings:', error);
            }
        }
    },

    /**
     * Save settings
     */
    async saveSettings(alpine) {
        if (!alpine.activeCompany) {
            this.showError('No active company selected');
            return;
        }

        try {
            const response = await fetch(`/api/companies/${alpine.activeCompany.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(alpine.settings)
            });

            if (!response.ok) throw new Error('Failed to save settings');

            const data = await response.json();
            this.showSuccess(data.message);

            await this.loadCompanies(alpine);
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showError('Failed to save settings');
        }
    },

    /**
     * Update financial year display
     */
    updateFinancialYear(alpine) {
        if (!alpine.activeCompany) return;

        const fyStart = new Date(alpine.activeCompany.financial_year_start);
        const startYear = fyStart.getFullYear();
        const endYear = startYear + 1;

        alpine.financialYear = `${startYear}-${endYear.toString().slice(-2)}`;
    },

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts(alpine) {
        document.addEventListener('keydown', (e) => {
            // F3 - Company Switcher
            if (e.key === 'F3') {
                e.preventDefault();
                this.openCompanySwitcher(alpine);
            }

            // F12 - Settings
            if (e.key === 'F12') {
                e.preventDefault();
                this.openSettings(alpine);
            }

            // Escape - Close modals
            if (e.key === 'Escape') {
                alpine.showCompanySwitcher = false;
                alpine.showDeleteConfirm = false;
            }
        });
    },

    /**
     * Show success message
     */
    showSuccess(message) {
        // Simple alert for now, can be replaced with toast notifications
        alert(message);
    },

    /**
     * Show error message
     */
    showError(message) {
        // Simple alert for now, can be replaced with toast notifications
        alert('Error: ' + message);
    }
};
