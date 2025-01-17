// static/fin_data_cl/js/portfolio/portfolio_manager/api.js
const API_BASE = '/portfolios/api/v1/';  // Updated to match the correct path

export const PortfolioAPI = {
    // These still point to the main fin_data API
    async getExchanges() {
        const response = await fetch('/api/v1/price-data/available_exchanges/');
        if (!response.ok) throw new Error('Failed to fetch exchanges');
        return response.json();
    },

    async getSecuritiesByExchange(exchangeId) {
        const response = await fetch(`/api/v1/price-data/securities_by_exchange/?exchange_id=${exchangeId}`);
        if (!response.ok) throw new Error('Failed to fetch securities');
        return response.json();
    },

    // These point to the portfolios API
    async uploadTickers(formData) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const response = await fetch(`${API_BASE}portfolios/upload_tickers/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        if (!response.ok) throw new Error('Failed to upload tickers');
        return response.json();
    },

    async createPortfolio(portfolioData) {
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const response = await fetch(`${API_BASE}portfolios/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'Accept': 'application/json'
                },
                body: JSON.stringify(portfolioData)
            });

            if (!response.ok) {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || errorData.detail || 'Failed to create portfolio');
                } else {
                    const errorText = await response.text();
                    throw new Error('Server error: Please try again later');
                }
            }

            return response.json();
        } catch (error) {
            console.error('Portfolio creation error:', error);
            throw error;
        }
    }
};