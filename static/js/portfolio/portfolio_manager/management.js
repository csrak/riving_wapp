// static/js/portfolio/portfolio_manager/management.js

// API module for handling all server communications
const api = {
    async getExchanges() {
        try {
            const response = await fetch('/api/v1/financial-ratios/available_exchanges/');
            if (!response.ok) throw new Error('Failed to fetch exchanges');
            return await response.json();
        } catch (error) {
            console.error('Error fetching exchanges:', error);
            return { exchanges: [] };
        }
    },

    async getSecuritiesByExchange(exchangeId) {
        try {
            const response = await fetch(`/api/v1/financial-ratios/securities_by_exchange/?exchange_id=${exchangeId}`);
            if (!response.ok) throw new Error('Failed to fetch securities');
            return await response.json();
        } catch (error) {
            console.error('Error fetching securities:', error);
            return { securities: [] };
        }
    },

    async getUserPortfolios() {
        try {
            const response = await fetch('/portfolios/api/portfolios/');
            if (!response.ok) throw new Error('Failed to fetch portfolios');
            const data = await response.json();
            // Handle paginated response
            return data.results || [];  // Return empty array if no results
        } catch (error) {
            console.error('Error fetching portfolios:', error);
            return [];
        }
    },
    async createPortfolio(data) {
        try {
            const response = await fetch('/portfolios/api/portfolios/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create portfolio');
            }

            return await response.json();
        } catch (error) {
            throw new Error(`Portfolio creation failed: ${error.message}`);
        }
    },

    async addPosition(portfolioId, data) {
        try {
            const response = await fetch(`/portfolios/api/portfolios/${portfolioId}/add_position/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) throw new Error('Failed to add position');
            return await response.json();
        } catch (error) {
            console.error('Error adding position:', error);
            throw error;
        }
    }
};

// UI module for handling DOM interactions
const ui = {
    init() {
        // Initialize DOM elements
        this.exchangeSelect = document.getElementById('exchangeSelect');
        this.stockSearch = document.getElementById('stockSearch');
        this.stockList = document.getElementById('stockList');
        this.portfolioSelect = document.getElementById('portfolioSelect');
        this.positionsTable = document.getElementById('positionsTable').querySelector('tbody');
        this.newPortfolioBtn = document.getElementById('newPortfolioBtn');
        this.portfolioModal = document.getElementById('portfolioModal');
        this.savePortfolioBtn = document.getElementById('savePortfolio');
        this.totalValueElement = document.getElementById('totalValue');

        this.bindEvents();
        this.loadInitialData();
    },

    bindEvents() {
        this.exchangeSelect.addEventListener('change', () => this.loadSecurities());
        this.stockSearch.addEventListener('input', () => this.filterStocks());
        this.portfolioSelect.addEventListener('change', () => this.loadPortfolioDetails());
        this.newPortfolioBtn.addEventListener('click', () => $(this.portfolioModal).modal('show'));
        this.savePortfolioBtn.addEventListener('click', () => this.handlePortfolioSubmit());
    },

    async loadInitialData() {
        try {
            const exchangeData = await api.getExchanges();
            this.populateExchangeSelect(exchangeData.exchanges);

            const portfolios = await api.getUserPortfolios();
            this.populatePortfolioSelect(portfolios);
        } catch (error) {
            console.error('Error loading initial data:', error);
            showError('Failed to load initial data');
        }
    },

    populateExchangeSelect(exchanges) {
        this.exchangeSelect.innerHTML = `
            <option value="">Select Exchange</option>
            ${exchanges.map(exchange =>
                `<option value="${exchange.id}">${exchange.name}</option>`
            ).join('')}
        `;
    },

    populatePortfolioSelect(portfolios) {
        if (!Array.isArray(portfolios)) {
            console.error('Expected array of portfolios, got:', portfolios);
            portfolios = [];
        }

        this.portfolioSelect.innerHTML = `
            <option value="">Select Portfolio</option>
            ${portfolios.map(portfolio =>
                `<option value="${portfolio.id}">${portfolio.name}</option>`
            ).join('')}
        `;
    },

    async loadSecurities() {
        const exchangeId = this.exchangeSelect.value;
        if (!exchangeId) return;

        try {
            const data = await api.getSecuritiesByExchange(exchangeId);
            this.renderSecuritiesList(data.securities);
        } catch (error) {
            showError('Failed to load securities');
        }
    },

    renderSecuritiesList(securities) {
        this.stockList.innerHTML = securities.map(security => `
            <div class="list-group-item" data-id="${security.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${security.ticker}</strong>
                        <small class="d-block text-muted">${security.name}</small>
                    </div>
                    <button class="btn btn-sm btn-primary add-stock-btn">Add</button>
                </div>
            </div>
        `).join('');

        // Add click handlers for add buttons
        this.stockList.querySelectorAll('.add-stock-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.showAddPositionModal(e));
        });
    },

    filterStocks() {
        const searchTerm = this.stockSearch.value.toLowerCase();
        this.stockList.querySelectorAll('.list-group-item').forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    },

    showAddPositionModal(event) {
        const stockItem = event.target.closest('.list-group-item');
        const securityId = stockItem.dataset.id;
        const portfolioId = this.portfolioSelect.value;

        if (!portfolioId) {
            showError('Please select a portfolio first');
            return;
        }

        $('#addPositionModal').modal('show');
        $('#addPositionModal').data('securityId', securityId);
    },

    async handlePortfolioSubmit() {
        const name = document.getElementById('portfolioName').value;
        const description = document.getElementById('portfolioDescription').value;

        if (!name) {
            showError('Portfolio name is required');
            return;
        }

        try {
            await api.createPortfolio({ name, description });
            await this.loadInitialData();
            $(this.portfolioModal).modal('hide');
            showSuccess('Portfolio created successfully');
        } catch (error) {
            showError('Failed to create portfolio');
        }
    },

    async loadPortfolioDetails() {
        const portfolioId = this.portfolioSelect.value;
        if (!portfolioId) {
            this.positionsTable.innerHTML = '';
            this.totalValueElement.textContent = '$0.00';
            return;
        }

        try {
            const portfolio = await api.getUserPortfolios().find(p => p.id === portfolioId);
            this.renderPortfolioPositions(portfolio.positions);
        } catch (error) {
            showError('Failed to load portfolio details');
        }
    },

    renderPortfolioPositions(positions) {
        this.positionsTable.innerHTML = positions.map(position => `
            <tr>
                <td>${position.security.ticker}</td>
                <td>${position.security.name}</td>
                <td>${position.shares}</td>
                <td>$${position.average_price}</td>
                <td>$${position.current_value}</td>
                <td>
                    <button class="btn btn-sm btn-danger delete-position" data-id="${position.id}">
                        Remove
                    </button>
                </td>
            </tr>
        `).join('');

        const totalValue = positions.reduce((sum, pos) => sum + pos.current_value, 0);
        this.totalValueElement.textContent = `$${totalValue.toFixed(2)}`;
    }
};

// Helper functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function showError(message) {
    // Implement your error notification system here
    alert(message);
}

function showSuccess(message) {
    // Implement your success notification system here
    alert(message);
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    ui.init();
});