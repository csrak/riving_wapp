// static/fin_data_cl/js/portfolio/portfolio_analysis/index.js
import { PortfolioAnalysisAPI } from './api.js';
import { PortfolioAnalysisUI } from './ui.js';

class PortfolioAnalysisManager {
    constructor() {
        this.api = PortfolioAnalysisAPI;
        this.ui = new PortfolioAnalysisUI(this.api);
    }

    async initialize() {
        await this.ui.initialize();
        this.defineGlobalHandlers();
    }

    defineGlobalHandlers() {
        window.portfolioAnalysis = {
            handleSecurityEdit: (id) => this.ui.handleSecurityEdit(id)
        };
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const manager = new PortfolioAnalysisManager();
    await manager.initialize();
});