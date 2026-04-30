/**
 * Voucher Entry Component for Tally Clone
 * Handles voucher forms (F5-F9) with keyboard navigation
 */

function voucherComponent() {
    return {
        // Voucher state
        voucher: {
            type: '',
            number: 'AUTO-001',
            date: new Date().toISOString().split('T')[0],
            partyAccount: '',
            entries: [
                { ledger: '', amount: 0, debit: 0, credit: 0, rate: 0, qty: 1 }
            ],
            narration: ''
        },

        // Ledger autocomplete
        ledgers: [],
        filteredLedgers: [],

        // Validation
        totalDebit: 0,
        totalCredit: 0,
        isBalanced: false,

        // Initialize voucher component
        async init() {
            await this.loadLedgers();
            this.setupKeyboardShortcuts();
        },

        // Set voucher mode and reset form
        setVoucherMode(type) {
            this.workspaceMode = type;
            this.voucher.type = type;
            this.clearVoucher();
            this.generateVoucherNumber(type);
        },

        // Generate auto voucher number
        generateVoucherNumber(type) {
            const prefix = {
                'payment': 'PAY',
                'receipt': 'RCV',
                'journal': 'JV',
                'sales': 'SV',
                'purchase': 'PV'
            };

            const num = Math.floor(Math.random() * 1000) + 1;
            this.voucher.number = `${prefix[type] || 'AUTO'}-${num.toString().padStart(4, '0')}`;
        },

        // Load ledgers from API
        async loadLedgers() {
            try {
                const response = await fetch('/api/ledgers');
                if (response.ok) {
                    this.ledgers = await response.json();
                    this.filteredLedgers = this.ledgers;
                }
            } catch (error) {
                console.error('Failed to load ledgers:', error);
                // Use mock data for demo
                this.ledgers = [
                    { id: 1, name: 'Cash in Hand', group: 'Cash' },
                    { id: 2, name: 'HDFC Bank', group: 'Bank Accounts' },
                    { id: 3, name: 'Sundry Debtors', group: 'Sundry Debtors' },
                    { id: 4, name: 'Sundry Creditors', group: 'Sundry Creditors' },
                    { id: 5, name: 'Sales Account', group: 'Sales Accounts' },
                    { id: 6, name: 'Purchase Account', group: 'Purchase Accounts' },
                    { id: 7, name: 'Salary Expense', group: 'Indirect Expenses' },
                    { id: 8, name: 'Rent Expense', group: 'Indirect Expenses' },
                    { id: 9, name: 'CGST', group: 'Duties & Taxes' },
                    { id: 10, name: 'SGST', group: 'Duties & Taxes' }
                ];
                this.filteredLedgers = this.ledgers;
            }
        },

        // Filter ledgers for autocomplete
        filterLedgers(event) {
            const query = event.target.value.toLowerCase();
            if (query.length === 0) {
                this.filteredLedgers = this.ledgers;
            } else {
                this.filteredLedgers = this.ledgers.filter(l =>
                    l.name.toLowerCase().includes(query) ||
                    l.group.toLowerCase().includes(query)
                );
            }
        },

        // Add new entry line
        addEntry() {
            const newEntry = {
                ledger: '',
                amount: 0,
                debit: 0,
                credit: 0,
                rate: 0,
                qty: 1
            };
            this.voucher.entries.push(newEntry);
        },

        // Remove entry line
        removeEntry(index) {
            if (this.voucher.entries.length > 1) {
                this.voucher.entries.splice(index, 1);
                this.calculateBalance();
            }
        },

        // Calculate Dr/Cr balance
        calculateBalance() {
            this.totalDebit = 0;
            this.totalCredit = 0;

            const voucherType = this.voucher.type;

            if (voucherType === 'journal') {
                // Journal: sum debit and credit columns
                this.voucher.entries.forEach(entry => {
                    this.totalDebit += parseFloat(entry.debit || 0);
                    this.totalCredit += parseFloat(entry.credit || 0);
                });
            } else if (voucherType === 'payment') {
                // Payment: Dr party account, Cr ledgers
                const totalCr = this.voucher.entries.reduce((sum, e) =>
                    sum + parseFloat(e.amount || 0), 0);
                this.totalDebit = totalCr;
                this.totalCredit = totalCr;
            } else if (voucherType === 'receipt') {
                // Receipt: Cr party account, Dr ledgers
                const totalDr = this.voucher.entries.reduce((sum, e) =>
                    sum + parseFloat(e.amount || 0), 0);
                this.totalDebit = totalDr;
                this.totalCredit = totalDr;
            } else if (voucherType === 'sales') {
                // Sales: Dr party, Cr sales ledgers
                const totalCr = this.voucher.entries.reduce((sum, e) =>
                    sum + parseFloat(e.amount || 0), 0);
                this.totalDebit = totalCr;
                this.totalCredit = totalCr;
            } else if (voucherType === 'purchase') {
                // Purchase: Cr party, Dr purchase ledgers
                const totalDr = this.voucher.entries.reduce((sum, e) =>
                    sum + parseFloat(e.amount || 0), 0);
                this.totalDebit = totalDr;
                this.totalCredit = totalDr;
            }

            // Check if balanced (within 0.01 tolerance)
            this.isBalanced = Math.abs(this.totalDebit - this.totalCredit) < 0.01 &&
                             this.totalDebit > 0;
        },

        // Format currency
        formatCurrency(amount) {
            return new Intl.NumberFormat('en-IN', {
                style: 'currency',
                currency: 'INR',
                minimumFractionDigits: 2
            }).format(amount || 0);
        },

        // Save voucher
        async saveVoucher() {
            if (!this.isBalanced) {
                alert('Voucher is not balanced. Please check Dr/Cr totals.');
                return;
            }

            // Prepare voucher data
            const voucherData = {
                voucher_type: this.voucher.type.charAt(0).toUpperCase() + this.voucher.type.slice(1),
                voucher_number: this.voucher.number,
                date: this.voucher.date,
                company_id: 1,
                narration: this.voucher.narration,
                entries: []
            };

            // Convert entries to API format
            const voucherType = this.voucher.type;

            if (voucherType === 'journal') {
                // Journal entries
                this.voucher.entries.forEach(entry => {
                    const ledger = this.ledgers.find(l => l.name === entry.ledger);
                    if (ledger && entry.debit > 0) {
                        voucherData.entries.push({
                            ledger_id: ledger.id,
                            amount: parseFloat(entry.debit),
                            is_debit: true
                        });
                    }
                    if (ledger && entry.credit > 0) {
                        voucherData.entries.push({
                            ledger_id: ledger.id,
                            amount: parseFloat(entry.credit),
                            is_debit: false
                        });
                    }
                });
            } else {
                // Payment, Receipt, Sales, Purchase
                const partyLedger = this.ledgers.find(l => l.name === this.voucher.partyAccount);
                if (!partyLedger) {
                    alert('Please select a valid party account');
                    return;
                }

                // Add party entry
                if (voucherType === 'payment' || voucherType === 'purchase') {
                    voucherData.entries.push({
                        ledger_id: partyLedger.id,
                        amount: this.totalDebit,
                        is_debit: voucherType === 'purchase'
                    });
                } else {
                    voucherData.entries.push({
                        ledger_id: partyLedger.id,
                        amount: this.totalCredit,
                        is_debit: voucherType === 'sales'
                    });
                }

                // Add line item entries
                this.voucher.entries.forEach(entry => {
                    const ledger = this.ledgers.find(l => l.name === entry.ledger);
                    if (ledger && entry.amount > 0) {
                        voucherData.entries.push({
                            ledger_id: ledger.id,
                            amount: parseFloat(entry.amount),
                            is_debit: voucherType === 'receipt' || voucherType === 'purchase'
                        });
                    }
                });
            }

            try {
                const response = await fetch('/api/vouchers', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(voucherData)
                });

                if (response.ok) {
                    const result = await response.json();
                    alert(`Voucher ${result.voucher_number} saved successfully!`);
                    this.clearVoucher();
                    this.workspaceMode = 'dashboard';
                } else {
                    const error = await response.json();
                    alert(`Error: ${error.detail}`);
                }
            } catch (error) {
                console.error('Failed to save voucher:', error);
                alert('Failed to save voucher. Please try again.');
            }
        },

        // Clear voucher form
        clearVoucher() {
            this.voucher.partyAccount = '';
            this.voucher.entries = [
                { ledger: '', amount: 0, debit: 0, credit: 0, rate: 0, qty: 1 }
            ];
            this.voucher.narration = '';
            this.totalDebit = 0;
            this.totalCredit = 0;
            this.isBalanced = false;
        },

        // Setup keyboard shortcuts
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ctrl+A: Accept/Save
                if (e.ctrlKey && e.key === 'a') {
                    e.preventDefault();
                    if (this.isBalanced && ['payment', 'receipt', 'journal', 'sales', 'purchase'].includes(this.workspaceMode)) {
                        this.saveVoucher();
                    }
                }

                // Esc: Cancel
                if (e.key === 'Escape') {
                    if (['payment', 'receipt', 'journal', 'sales', 'purchase'].includes(this.workspaceMode)) {
                        this.clearVoucher();
                        this.workspaceMode = 'dashboard';
                    }
                }

                // F2: Focus date field
                if (e.key === 'F2') {
                    e.preventDefault();
                    const dateInput = document.querySelector('input[type="date"]');
                    if (dateInput) dateInput.focus();
                }

                // F5-F9: Switch voucher types
                if (e.key === 'F5') {
                    e.preventDefault();
                    this.setVoucherMode('payment');
                }
                if (e.key === 'F6') {
                    e.preventDefault();
                    this.setVoucherMode('receipt');
                }
                if (e.key === 'F7') {
                    e.preventDefault();
                    this.setVoucherMode('journal');
                }
                if (e.key === 'F8') {
                    e.preventDefault();
                    this.setVoucherMode('sales');
                }
                if (e.key === 'F9') {
                    e.preventDefault();
                    this.setVoucherMode('purchase');
                }
            });
        }
    };
}

// Export for use in Alpine.js
if (typeof window !== 'undefined') {
    window.voucherComponent = voucherComponent;
}
