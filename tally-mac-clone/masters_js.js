// Masters Management JavaScript - Add to appData() function in index.html

// Masters state
mastersSubMode: null, // 'ledgers', 'groups', 'cost-centers', 'currencies', 'stock-items'
ledgers: [],
groups: [],
costCenters: [],
currencies: [],
stockItems: [],

// Form states
editingLedger: false,
editingGroup: false,
editingCostCenter: false,
editingCurrency: false,

ledgerForm: {
    id: null,
    name: '',
    group_name: '',
    opening_balance: 0
},

groupForm: {
    id: null,
    name: '',
    parent_id: null,
    is_revenue: false,
    is_expense: false,
    is_asset: false,
    is_liability: false
},

costCenterForm: {
    id: null,
    name: '',
    parent_id: null,
    category: 'Department'
},

currencyForm: {
    id: null,
    code: '',
    symbol: '',
    name: '',
    decimal_places: 2,
    is_base: false
},

// Search
ledgerSearch: '',
groupSearch: '',

// Computed
get filteredLedgers() {
    if (!this.ledgerSearch) return this.ledgers;
    const search = this.ledgerSearch.toLowerCase();
    return this.ledgers.filter(l =>
        l.name.toLowerCase().includes(search) ||
        l.group.toLowerCase().includes(search)
    );
},

get rootGroups() {
    return this.groups.filter(g => !g.parent_id);
},

// Methods
getChildGroups(parentId) {
    return this.groups.filter(g => g.parent_id === parentId);
},

formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
    }).format(amount);
},

// Ledger CRUD
async fetchLedgers() {
    try {
        const response = await fetch('/api/ledgers');
        this.ledgers = await response.json();
    } catch (error) {
        console.error('Error fetching ledgers:', error);
    }
},

async fetchGroups() {
    try {
        const response = await fetch('/api/groups');
        this.groups = await response.json();
    } catch (error) {
        console.error('Error fetching groups:', error);
    }
},

createNewLedger() {
    this.ledgerForm = {
        id: null,
        name: '',
        group_name: '',
        opening_balance: 0
    };
    this.editingLedger = true;
},

editLedger(ledger) {
    this.ledgerForm = {
        id: ledger.id,
        name: ledger.name,
        group_name: ledger.group,
        opening_balance: ledger.opening_balance
    };
    this.editingLedger = true;
},

async saveLedger() {
    try {
        const url = this.ledgerForm.id
            ? `/api/ledgers/${this.ledgerForm.id}`
            : '/api/ledgers';
        const method = this.ledgerForm.id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: this.ledgerForm.name,
                group_name: this.ledgerForm.group_name,
                opening_balance: parseFloat(this.ledgerForm.opening_balance)
            })
        });

        if (response.ok) {
            await this.fetchLedgers();
            this.cancelLedgerForm();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error saving ledger');
        }
    } catch (error) {
        console.error('Error saving ledger:', error);
        alert('Error saving ledger');
    }
},

async deleteLedger(ledger) {
    if (!confirm(`Delete ledger '${ledger.name}'?`)) return;

    try {
        const response = await fetch(`/api/ledgers/${ledger.id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await this.fetchLedgers();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error deleting ledger');
        }
    } catch (error) {
        console.error('Error deleting ledger:', error);
        alert('Error deleting ledger');
    }
},

cancelLedgerForm() {
    this.editingLedger = false;
    this.ledgerForm = {
        id: null,
        name: '',
        group_name: '',
        opening_balance: 0
    };
},

// Group CRUD
createNewGroup() {
    this.groupForm = {
        id: null,
        name: '',
        parent_id: null,
        is_revenue: false,
        is_expense: false,
        is_asset: false,
        is_liability: false
    };
    this.editingGroup = true;
},

editGroup(group) {
    this.groupForm = { ...group };
    this.editingGroup = true;
},

async saveGroup() {
    try {
        const url = this.groupForm.id
            ? `/api/groups/${this.groupForm.id}`
            : '/api/groups';
        const method = this.groupForm.id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.groupForm)
        });

        if (response.ok) {
            await this.fetchGroups();
            this.cancelGroupForm();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error saving group');
        }
    } catch (error) {
        console.error('Error saving group:', error);
        alert('Error saving group');
    }
},

async deleteGroup(group) {
    if (!confirm(`Delete group '${group.name}'?`)) return;

    try {
        const response = await fetch(`/api/groups/${group.id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await this.fetchGroups();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error deleting group');
        }
    } catch (error) {
        console.error('Error deleting group:', error);
        alert('Error deleting group');
    }
},

cancelGroupForm() {
    this.editingGroup = false;
    this.groupForm = {
        id: null,
        name: '',
        parent_id: null,
        is_revenue: false,
        is_expense: false,
        is_asset: false,
        is_liability: false
    };
},

// Cost Center CRUD
async fetchCostCenters() {
    try {
        const response = await fetch('/api/cost-centers');
        const data = await response.json();
        this.costCenters = data.cost_centers || [];
    } catch (error) {
        console.error('Error fetching cost centers:', error);
    }
},

createNewCostCenter() {
    this.costCenterForm = {
        id: null,
        name: '',
        parent_id: null,
        category: 'Department'
    };
    this.editingCostCenter = true;
},

async saveCostCenter() {
    try {
        const url = this.costCenterForm.id
            ? `/api/cost-centers/${this.costCenterForm.id}`
            : '/api/cost-centers';
        const method = this.costCenterForm.id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.costCenterForm)
        });

        if (response.ok) {
            await this.fetchCostCenters();
            this.cancelCostCenterForm();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error saving cost center');
        }
    } catch (error) {
        console.error('Error saving cost center:', error);
        alert('Error saving cost center');
    }
},

cancelCostCenterForm() {
    this.editingCostCenter = false;
},

// Currency CRUD
async fetchCurrencies() {
    try {
        const response = await fetch('/api/currencies');
        this.currencies = await response.json();
    } catch (error) {
        console.error('Error fetching currencies:', error);
    }
},

createNewCurrency() {
    this.currencyForm = {
        id: null,
        code: '',
        symbol: '',
        name: '',
        decimal_places: 2,
        is_base: false
    };
    this.editingCurrency = true;
},

async saveCurrency() {
    try {
        const url = this.currencyForm.id
            ? `/api/currencies/${this.currencyForm.id}`
            : '/api/currencies';
        const method = this.currencyForm.id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.currencyForm)
        });

        if (response.ok) {
            await this.fetchCurrencies();
            this.cancelCurrencyForm();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error saving currency');
        }
    } catch (error) {
        console.error('Error saving currency:', error);
        alert('Error saving currency');
    }
},

cancelCurrencyForm() {
    this.editingCurrency = false;
},

// Keyboard shortcuts - add to existing init or create new init
initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Alt+K: Masters
        if (e.altKey && e.key === 'k') {
            e.preventDefault();
            this.workspaceMode = 'masters';
            this.mastersSubMode = null;
        }

        // Alt+C: Create in masters views
        if (e.altKey && e.key === 'c' && this.mastersSubMode) {
            e.preventDefault();
            if (this.mastersSubMode === 'ledgers') this.createNewLedger();
            else if (this.mastersSubMode === 'groups') this.createNewGroup();
            else if (this.mastersSubMode === 'cost-centers') this.createNewCostCenter();
            else if (this.mastersSubMode === 'currencies') this.createNewCurrency();
        }

        // Esc: Cancel/Go back
        if (e.key === 'Escape') {
            if (this.editingLedger) this.cancelLedgerForm();
            else if (this.editingGroup) this.cancelGroupForm();
            else if (this.editingCostCenter) this.cancelCostCenterForm();
            else if (this.editingCurrency) this.cancelCurrencyForm();
            else if (this.mastersSubMode) this.mastersSubMode = null;
        }
    });
},

// Load data on masters mode change
async loadMastersData() {
    if (this.workspaceMode === 'masters') {
        await this.fetchLedgers();
        await this.fetchGroups();
        await this.fetchCostCenters();
        await this.fetchCurrencies();
    }
}
