// static/fin_data_cl/js/portfolio/portfolio_manager/index.js
import { PortfolioAPI } from './api.js';
import { PortfolioState } from './state.js';
import { PortfolioUI } from './ui.js';

class PortfolioManager {
    constructor() {
        this.api = PortfolioAPI;
        this.state = new PortfolioState();
        this.ui = new PortfolioUI(this.api, this.state);
    }

    async initialize() {
        await this.ui.initialize();
        // Define the global handlers before accessing them
        this.defineGlobalHandlers();
    }

    defineGlobalHandlers() {
        window.portfolioManager = {
            handleSharesUpdate: (id, value) => this.state.updateShares(id, value),
            handlePriceUpdate: (id, value) => this.state.updatePrice(id, value),
            handleRemoveSecurity: (id) => this.state.removeSecurity(id)
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    const manager = new PortfolioManager();
    await manager.initialize();
});