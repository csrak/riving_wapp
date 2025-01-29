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
    async getPortfolioDetails(portfolioId) {
        return fetch(`/portfolios/api/portfolios/${portfolioId}/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'include'
        });
    },
        async addPosition(portfolioId, data) {
        try {
            const response = await fetch(`/portfolios/api/portfolios/${portfolioId}/add_position/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'include',
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to add position');
            }

            return await response.json();
        } catch (error) {
            console.error('Error adding position:', error);
            throw error;
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
                    'X-CSRFToken': getCsrfToken()  // Only need CSRF token
                },
                credentials: 'include',  // This ensures cookies (including session) are sent
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create portfolio');
            }

            return await response.json();
        } catch (error) {
            console.error('Portfolio creation error:', error);
            throw error;
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
        this.addPositionModal = document.getElementById('addPositionModal');
        this.savePositionBtn = document.getElementById('savePosition');
        this.bindEvents();
        this.loadInitialData();
    },

    bindEvents() {
        this.exchangeSelect.addEventListener('change', () => this.loadSecurities());
        this.stockSearch.addEventListener('input', () => this.filterStocks());
        this.portfolioSelect.addEventListener('change', () => this.loadPortfolioDetails());
        this.newPortfolioBtn.addEventListener('click', () => $(this.portfolioModal).modal('show'));
        this.savePortfolioBtn.addEventListener('click', () => this.handlePortfolioSubmit());
        this.savePositionBtn.addEventListener('click', () => this.handleAddPosition());
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
            this.showEmptyState();
            return;
        }

        try {
            const response = await api.getPortfolioDetails(portfolioId);
            if (!response.ok) {
                throw new Error('Failed to load portfolio');
            }
            const portfolio = await response.json();
            this.renderPortfolioDetails(portfolio);
        } catch (error) {
            console.error('Error loading portfolio:', error);
            this.showErrorState('Could not load portfolio details');
        }
    },
    showEmptyState() {
    this.positionsTable.innerHTML = `
        <tr>
            <td colspan="6" class="text-center py-4">
                <p class="text-muted mb-0">No positions in this portfolio yet.</p>
                <p class="text-muted">Use the left panel to add stocks to your portfolio.</p>
            </td>
        </tr>
    `;
    this.totalValueElement.textContent = '$0.00';
    },

    showErrorState(message) {
        this.positionsTable.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <p class="text-danger mb-0">${message}</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="ui.loadPortfolioDetails()">
                        Try Again
                    </button>
                </td>
            </tr>
        `;
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
    },

    renderPortfolioDetails(portfolio) {
        if (!portfolio.positions || portfolio.positions.length === 0) {
            this.showEmptyState();
            return;
        }

        this.positionsTable.innerHTML = portfolio.positions.map(position => `
            <tr>
                <td>${position.security.ticker}</td>
                <td>${position.security.name}</td>
                <td>${position.shares}</td>
                <td>$${position.average_price}</td>
                <td>$${position.current_value}</td>
                <td>
                    <button class="btn btn-sm btn-danger delete-position"
                            data-id="${position.id}">
                        Remove
                    </button>
                </td>
            </tr>
        `).join('');

        this.totalValueElement.textContent = `$${portfolio.total_value.toFixed(2)}`;
    },
        async handleAddPosition() {
        const portfolioId = this.portfolioSelect.value;
        const securityId = this.addPositionModal.dataset.securityId;
        const shares = document.getElementById('shares').value;
        const averagePrice = document.getElementById('averagePrice').value;

        if (!shares || !averagePrice) {
            showError('Please fill in all fields');
            return;
        }

        try {
            await api.addPosition(portfolioId, {
                security_id: securityId,
                shares: parseFloat(shares),
                average_price: parseFloat(averagePrice)
            });

            // Refresh portfolio details
            await this.loadPortfolioDetails();

            // Clear form and close modal
            document.getElementById('shares').value = '';
            document.getElementById('averagePrice').value = '';
            $(this.addPositionModal).modal('hide');

            showSuccess('Position added successfully');
        } catch (error) {
            showError('Failed to add position');
        }
    },

    showAddPositionModal(event) {
        const stockItem = event.target.closest('.list-group-item');
        const securityId = stockItem.dataset.id;
        const portfolioId = this.portfolioSelect.value;

        if (!portfolioId) {
            showError('Please select a portfolio first');
            return;
        }

        // Store the security ID in the modal's dataset
        this.addPositionModal.dataset.securityId = securityId;
        $(this.addPositionModal).modal('show');
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
//function getAuthToken() {
//    // Implement token retrieval logic if using token auth
//    return localStorage.getItem('authToken');
//}
function showError(message) {
    // You can replace this with a proper notification system
    alert(message);
}

function showSuccess(message) {
    // You can replace this with a proper notification system
    alert(message);
}