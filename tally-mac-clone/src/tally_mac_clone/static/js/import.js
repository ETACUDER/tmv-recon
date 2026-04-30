// Import/Export functionality for RecordX.Finance
// Alpine.js components for Excel, Bank Statement, and XML import

// Excel Import Component
function importExcel() {
    return {
        importType: 'ledgers',
        voucherType: 'Payment',
        selectedFile: null,
        loading: false,
        downloading: false,
        progress: 0,
        progressText: '',
        results: null,

        resetForm() {
            this.selectedFile = null;
            this.loading = false;
            this.progress = 0;
            this.progressText = '';
            this.results = null;
        },

        async downloadTemplate() {
            this.downloading = true;
            try {
                const params = new URLSearchParams();
                if (this.importType === 'vouchers') {
                    params.append('voucher_type', this.voucherType);
                }

                const response = await fetch(`/api/import/template/${this.importType}?${params}`);
                if (!response.ok) throw new Error('Failed to download template');

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;

                // Get filename from Content-Disposition header or use default
                const contentDisposition = response.headers.get('Content-Disposition');
                const filename = contentDisposition
                    ? contentDisposition.split('filename=')[1].replace(/"/g, '')
                    : `${this.importType}_template.xlsx`;

                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                this.showNotification('Template downloaded successfully', 'success');
            } catch (error) {
                console.error('Download error:', error);
                this.showNotification('Failed to download template: ' + error.message, 'error');
            } finally {
                this.downloading = false;
            }
        },

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.selectedFile = file;
                this.results = null;
            }
        },

        async importFile() {
            if (!this.selectedFile) {
                this.showNotification('Please select a file', 'error');
                return;
            }

            this.loading = true;
            this.progress = 10;
            this.progressText = 'Uploading file...';

            try {
                const formData = new FormData();
                formData.append('file', this.selectedFile);

                let endpoint = '';
                const params = new URLSearchParams();

                if (this.importType === 'ledgers') {
                    endpoint = '/api/import/excel/ledgers';
                } else if (this.importType === 'vouchers') {
                    endpoint = '/api/import/excel/vouchers';
                    params.append('voucher_type', this.voucherType);
                } else {
                    throw new Error('Import type not yet implemented');
                }

                this.progress = 30;
                this.progressText = 'Processing data...';

                const response = await fetch(`${endpoint}?${params}`, {
                    method: 'POST',
                    body: formData
                });

                this.progress = 70;
                this.progressText = 'Validating and importing...';

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Import failed');
                }

                this.results = await response.json();
                this.progress = 100;
                this.progressText = 'Import complete!';

                if (this.results.error_count === 0) {
                    this.showNotification(`Successfully imported ${this.results.success_count} records`, 'success');
                } else {
                    this.showNotification(`Imported ${this.results.success_count} records with ${this.results.error_count} errors`, 'warning');
                }

            } catch (error) {
                console.error('Import error:', error);
                this.showNotification('Import failed: ' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },

        showNotification(message, type) {
            // Use Alpine.js store notification if available, otherwise alert
            if (Alpine.store('notifications')) {
                Alpine.store('notifications').add(message, type);
            } else {
                alert(message);
            }
        }
    };
}

// Bank Statement Import Component
function importBankStatement() {
    return {
        ledgerId: '',
        fileFormat: 'excel',
        selectedFile: null,
        loading: false,
        results: null,
        bankLedgers: [],

        async init() {
            await this.loadBankLedgers();
        },

        async loadBankLedgers() {
            try {
                const response = await fetch('/api/ledgers');
                if (!response.ok) throw new Error('Failed to load ledgers');

                const ledgers = await response.json();
                // Filter for bank ledgers (you might want to filter by group)
                this.bankLedgers = ledgers.filter(l =>
                    l.group === 'Bank Accounts' ||
                    l.group === 'Cash-in-Hand'
                );
            } catch (error) {
                console.error('Error loading ledgers:', error);
                this.showNotification('Failed to load bank ledgers', 'error');
            }
        },

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.selectedFile = file;
                this.results = null;
            }
        },

        resetForm() {
            this.selectedFile = null;
            this.loading = false;
            this.results = null;
        },

        async importStatement() {
            if (!this.selectedFile || !this.ledgerId) {
                this.showNotification('Please select both file and bank ledger', 'error');
                return;
            }

            this.loading = true;

            try {
                const formData = new FormData();
                formData.append('file', this.selectedFile);

                const params = new URLSearchParams({
                    ledger_id: this.ledgerId,
                    file_format: this.fileFormat
                });

                const response = await fetch(`/api/import/bank-statement?${params}`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Import failed');
                }

                this.results = await response.json();

                const matchRate = this.results.imported_count > 0
                    ? ((this.results.matched_count / this.results.imported_count) * 100).toFixed(1)
                    : 0;

                this.showNotification(
                    `Imported ${this.results.imported_count} transactions. ${matchRate}% auto-matched.`,
                    'success'
                );

            } catch (error) {
                console.error('Import error:', error);
                this.showNotification('Import failed: ' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },

        showNotification(message, type) {
            if (Alpine.store('notifications')) {
                Alpine.store('notifications').add(message, type);
            } else {
                alert(message);
            }
        }
    };
}

// XML Import Component
function importXML() {
    return {
        selectedFile: null,
        companyId: 1,
        loading: false,
        results: null,
        companies: [],

        async init() {
            await this.loadCompanies();
        },

        async loadCompanies() {
            try {
                const response = await fetch('/api/companies');
                if (!response.ok) throw new Error('Failed to load companies');

                this.companies = await response.json();
                if (this.companies.length > 0) {
                    this.companyId = this.companies[0].id;
                }
            } catch (error) {
                console.error('Error loading companies:', error);
                this.showNotification('Failed to load companies', 'error');
            }
        },

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.selectedFile = file;
                this.results = null;
            }
        },

        resetForm() {
            this.selectedFile = null;
            this.loading = false;
            this.results = null;
        },

        async importXML() {
            if (!this.selectedFile) {
                this.showNotification('Please select an XML file', 'error');
                return;
            }

            this.loading = true;

            try {
                const formData = new FormData();
                formData.append('file', this.selectedFile);

                const params = new URLSearchParams({
                    company_id: this.companyId
                });

                const response = await fetch(`/api/import/xml?${params}`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Import failed');
                }

                this.results = await response.json();

                if (this.results.error_count === 0) {
                    this.showNotification(
                        `Successfully imported ${this.results.success_count} vouchers`,
                        'success'
                    );
                } else {
                    this.showNotification(
                        `Imported ${this.results.success_count} vouchers with ${this.results.error_count} errors`,
                        'warning'
                    );
                }

            } catch (error) {
                console.error('Import error:', error);
                this.showNotification('Import failed: ' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },

        showNotification(message, type) {
            if (Alpine.store('notifications')) {
                Alpine.store('notifications').add(message, type);
            } else {
                alert(message);
            }
        }
    };
}
