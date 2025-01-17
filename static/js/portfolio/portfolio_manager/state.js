// static/fin_data_cl/js/portfolio/portfolio_manager/state.js
export class PortfolioState {
    constructor() {
        this.selectedSecurities = new Map();
        this.subscribers = [];
    }

    subscribe(callback) {
        this.subscribers.push(callback);
    }

    notify() {
        this.subscribers.forEach(callback => callback(this.selectedSecurities));
    }

    addSecurity(id, security) {
        this.selectedSecurities.set(id, {
            ...security,
            weight: this._calculateWeight(security.shares * security.price)
        });
        this._recalculateWeights();
        this.notify();
    }

    updateShares(id, shares) {
        const security = this.selectedSecurities.get(id);
        if (security) {
            security.shares = parseFloat(shares);
            this._recalculateWeights();
            this.notify();
        }
    }

    updatePrice(id, price) {
        const security = this.selectedSecurities.get(id);
        if (security) {
            security.price = parseFloat(price);
            this._recalculateWeights();
            this.notify();
        }
    }

    removeSecurity(id) {
        this.selectedSecurities.delete(id);
        this._recalculateWeights();
        this.notify();
    }

    getTotalPortfolioValue() {
        let total = 0;
        this.selectedSecurities.forEach(security => {
            total += security.shares * security.price;
        });
        return total;
    }

    _calculateWeight(value) {
        const total = this.getTotalPortfolioValue();
        return total ? ((value / total) * 100).toFixed(2) : '0.00';
    }

    _recalculateWeights() {
        const total = this.getTotalPortfolioValue();
        this.selectedSecurities.forEach(security => {
            security.weight = ((security.shares * security.price / total) * 100).toFixed(2);
        });
    }

    getPortfolioData() {
        const securities = [];
        this.selectedSecurities.forEach((security, id) => {
            securities.push({
                security_id: id,
                shares: security.shares,
                price: security.price,
                weight: parseFloat(security.weight)
            });
        });
        return securities;
    }
}