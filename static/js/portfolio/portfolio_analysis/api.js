// static/fin_data_cl/js/portfolio/portfolio_analysis/api.js
const API_BASE = '/portfolios/api/v1/portfolios/';

export const PortfolioAnalysisAPI = {
    async getAnalysis(portfolioId, startDate, endDate) {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        const response = await fetch(`${API_BASE}${portfolioId}/analysis/?${params}`);
        if (!response.ok) throw new Error('Failed to fetch portfolio analysis');
        return response.json();
    },

    async updatePortfolio(portfolioId, data) {
        const response = await fetch(`${API_BASE}${portfolioId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to update portfolio');
        return response.json();
    },

    async rebalancePortfolio(portfolioId, securities) {
        const response = await fetch(`${API_BASE}${portfolioId}/rebalance/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ securities })
        });
        if (!response.ok) throw new Error('Failed to rebalance portfolio');
        return response.json();
    }
};