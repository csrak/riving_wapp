// static/fin_data_cl/js/portfolio/portfolio_manager/ui.js
export class PortfolioUI {
    constructor(api, state) {
        this.api = api;
        this.state = state;

        // Cache DOM elements
        this.elements = {
            // Dropdowns and inputs
            exchangeSelect: document.getElementById('exchangeSelect'),
            securitySelect: document.getElementById('securitySelect'),
            sharesInput: document.getElementById('securityShares'),
            priceInput: document.getElementById('securityPrice'),
            addButton: document.getElementById('addSecurity'),

            // Forms
            uploadForm: document.getElementById('uploadForm'),
            tickerFile: document.getElementById('tickerFile'),

            // Portfolio details
            portfolioName: document.getElementById('portfolioName'),
            portfolioDescription: document.getElementById('portfolioDescription'),
            isPublic: document.getElementById('isPublic'),

            // Table elements
            securitiesTable: document.getElementById('selectedSecurities'),
            totalValue: document.getElementById('totalValue'),
            totalWeight: document.getElementById('totalWeight'),

            // Actions
            createButton: document.getElementById('createPortfolio')
        };

        // Subscribe to state changes
        this.state.subscribe(this.updateTable.bind(this));
    }

    // Initialization
    async initialize() {
        this.bindEvents();
        await this.loadExchanges();
    }

    // Event Binding
    bindEvents() {
        const { elements } = this;

        // Selection events
        elements.exchangeSelect.addEventListener('change', this.handleExchangeChange.bind(this));
        elements.securitySelect.addEventListener('change', this.handleSecurityChange.bind(this));

        // Input events
        elements.sharesInput.addEventListener('input', this.handleInputValidation.bind(this));
        elements.priceInput.addEventListener('input', this.handleInputValidation.bind(this));

        // Action events
        elements.addButton.addEventListener('click', this.handleAddSecurity.bind(this));
        elements.uploadForm.addEventListener('submit', this.handleFileUpload.bind(this));
        elements.createButton.addEventListener('click', this.handleCreatePortfolio.bind(this));
    }

    // Exchange and Security Loading
    async loadExchanges() {
        try {
            const data = await this.api.getExchanges();
            this.updateExchangeOptions(data.exchanges || []);
        } catch (error) {
            console.error('Error loading exchanges:', error);
            this.showError('Failed to load exchanges');
        }
    }

    updateExchangeOptions(exchanges) {
        const { exchangeSelect } = this.elements;
        exchangeSelect.innerHTML = '<option value="">Select an exchange...</option>';

        exchanges.forEach(exchange => {
            const option = new Option(exchange.name, exchange.id);
            exchangeSelect.add(option);
        });
    }

    async loadSecurities(exchangeId) {
        try {
            const data = await this.api.getSecuritiesByExchange(exchangeId);
            this.updateSecurityOptions(data.securities || []);
        } catch (error) {
            console.error('Error loading securities:', error);
            this.showError('Failed to load securities');
        }
    }

    updateSecurityOptions(securities) {
        const { securitySelect } = this.elements;
        securitySelect.innerHTML = '<option value="">Select a security...</option>';

        securities.forEach(security => {
            if (!this.state.selectedSecurities.has(security.id)) {
                const option = new Option(`${security.ticker} - ${security.name}`, security.id);
                securitySelect.add(option);
            }
        });
    }

    // Event Handlers
    async handleExchangeChange(e) {
        const exchangeId = e.target.value;
        const { securitySelect, sharesInput, priceInput, addButton } = this.elements;

        this.resetInputs();
        securitySelect.disabled = !exchangeId;

        if (exchangeId) {
            await this.loadSecurities(exchangeId);
        }
    }

    handleSecurityChange(e) {
        const { sharesInput, priceInput, addButton } = this.elements;
        const hasSelection = Boolean(e.target.value);

        sharesInput.disabled = !hasSelection;
        priceInput.disabled = !hasSelection;

        if (!hasSelection) {
            this.resetInputs();
        }
    }

    handleInputValidation() {
        const { sharesInput, priceInput, addButton } = this.elements;
        const sharesValid = sharesInput.value > 0;
        const priceValid = priceInput.value > 0;

        addButton.disabled = !(sharesValid && priceValid);
    }

    handleAddSecurity() {
        const { securitySelect, exchangeSelect, sharesInput, priceInput } = this.elements;

        const [ticker, name] = securitySelect.options[securitySelect.selectedIndex].text.split(' - ');
        const exchange = exchangeSelect.options[exchangeSelect.selectedIndex].text;

        this.state.addSecurity(securitySelect.value, {
            ticker,
            name,
            exchange,
            shares: parseFloat(sharesInput.value),
            price: parseFloat(priceInput.value)
        });

        // Remove selected option and reset inputs
        securitySelect.remove(securitySelect.selectedIndex);
        this.resetInputs();
    }

    async handleFileUpload(e) {
        e.preventDefault();
        const formData = new FormData();
        const file = this.elements.tickerFile.files[0];

        if (!file) {
            this.showError('Please select a file first');
            return;
        }

        formData.append('file', file);

        try {
            const data = await this.api.uploadTickers(formData);
            await this.processUploadedTickers(data);
        } catch (error) {
            console.error('Error uploading file:', error);
            this.showError('Error uploading file');
        }
    }

    async processUploadedTickers(data) {
        if (!data.securities?.length) {
            this.showError('No valid securities found in file');
            return;
        }

        const sharesInput = prompt('Enter number of shares for each security:', '100');
        const priceInput = prompt('Enter price per share:', '10');

        if (sharesInput && priceInput) {
            const shares = parseFloat(sharesInput);
            const price = parseFloat(priceInput);

            if (isNaN(shares) || isNaN(price) || shares <= 0 || price <= 0) {
                this.showError('Invalid shares or price value');
                return;
            }

            data.securities.forEach(security => {
                if (!this.state.selectedSecurities.has(security.id)) {
                    this.state.addSecurity(security.id, {
                        ticker: security.ticker,
                        name: security.name,
                        exchange: security.exchange.name,
                        shares,
                        price
                    });
                }
            });
        }

        if (data.not_found?.length) {
            this.showError(`Securities not found: ${data.not_found.join(', ')}`);
        }
    }

    async handleCreatePortfolio() {
        const { portfolioName, portfolioDescription, isPublic } = this.elements;

        if (!this.validatePortfolio()) return;

        const portfolioData = {
            name: portfolioName.value,
            description: portfolioDescription.value,
            is_public: isPublic.checked,
            securities: this.state.getPortfolioData()
        };

        try {
            const response = await this.api.createPortfolio(portfolioData);
            this.handlePortfolioCreationSuccess(response);
        } catch (error) {
            console.error('Error creating portfolio:', error);
            this.showError(`Error creating portfolio: ${error.message}`);
        }
    }

    // UI Updates
    updateTable(securities) {
        const { securitiesTable, totalValue, totalWeight } = this.elements;
        securitiesTable.innerHTML = '';

        securities.forEach((security, id) => {
            securitiesTable.appendChild(this.createSecurityRow(security, id));
        });

        totalValue.textContent = this.state.getTotalPortfolioValue().toFixed(2);
        totalWeight.textContent = '100.00%';
    }


    createSecurityRow(security, id) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">${security.ticker}</td>
            <td class="px-6 py-4 whitespace-nowrap">${security.name}</td>
            <td class="px-6 py-4 whitespace-nowrap">${security.exchange}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <input type="number" value="${security.shares}" min="0" step="1"
                    class="w-24 rounded border-gray-300"
                    onchange="window.portfolioManager.handleSharesUpdate('${id}', this.value)">
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <input type="number" value="${security.price}" min="0" step="0.01"
                    class="w-24 rounded border-gray-300"
                    onchange="window.portfolioManager.handlePriceUpdate('${id}', this.value)">
            </td>
            <td class="px-6 py-4 whitespace-nowrap">${(security.shares * security.price).toFixed(2)}</td>
            <td class="px-6 py-4 whitespace-nowrap">${security.weight}%</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <button onclick="window.portfolioManager.handleRemoveSecurity('${id}')"
                    class="text-red-600 hover:text-red-900">Remove</button>
            </td>
        `;
        return tr;
    }

    // Utility Methods
    resetInputs() {
        const { sharesInput, priceInput, addButton } = this.elements;
        sharesInput.value = '';
        priceInput.value = '';
        sharesInput.disabled = true;
        priceInput.disabled = true;
        addButton.disabled = true;
    }

    validatePortfolio() {
        if (!this.elements.portfolioName.value) {
            this.showError('Please enter a portfolio name');
            return false;
        }

        if (this.state.selectedSecurities.size === 0) {
            this.showError('Please add at least one security');
            return false;
        }

        return true;
    }

    handlePortfolioCreationSuccess(response) {
        alert('Portfolio created successfully!');
        window.location.href = `/portfolio_analysis/${response.id}/`;
    }

    showError(message) {
        alert(message); // Could be replaced with a better error display mechanism
    }
}