class StockAnalysis {
    constructor() {
        this.DEBUG = true;
        console.log('StockAnalysis Constructor Started');

        this.state = {
            activeStocks: new Map(), // Map of securityId -> {color, visible, ticker}
            timeRange: '1y',
            indicators: new Set(),
            chartType: 'line',
            colors: ['#2E93fA', '#66DA26', '#546E7A', '#E91E63', '#FF9800'],
            nextColorIndex: 0
        };

        this.initializeElements();
        this.initializeEventListeners();
    }

    initializeElements() {
        this.elements = {
            exchangeSelect: document.getElementById('exchange-select'),
            stockSelect: document.getElementById('stock-select'),
            addButton: document.getElementById('add-stock'),
            chartContainer: document.getElementById('chart-container'),
            volumeContainer: document.getElementById('volume-container'),
            activeStocks: document.getElementById('active-stocks'),
            loadingIndicator: document.getElementById('loading-indicator')
        };

        console.log('Elements initialized:', this.elements);
    }

    async updateStockSelect(exchangeCode) {
        console.log('Updating stock select for exchange:', exchangeCode);
        const stockSelect = this.elements.stockSelect;

        // Disable select while loading
        stockSelect.disabled = true;
        this.elements.addButton.disabled = true;

        try {
            const url = `/api/stock-securities/${exchangeCode ? `?exchange=${exchangeCode}` : ''}`;
            console.log('Fetching securities from:', url);

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const securities = await response.json();
            console.log('Received securities:', securities);

            // Clear existing options
            stockSelect.innerHTML = '<option value="">Select Stock</option>';

            // Add new options
            securities.forEach(security => {
                const option = document.createElement('option');
                option.value = security.id;
                option.textContent = `${security.ticker} - ${security.name}`;
                stockSelect.appendChild(option);
            });

            // Enable select if we have options
            stockSelect.disabled = false;
        } catch (error) {
            console.error('Error fetching securities:', error);
            stockSelect.innerHTML = '<option value="">Error loading securities</option>';
        }
    }

    initializeEventListeners() {
        // Exchange selection
        this.elements.exchangeSelect.addEventListener('change', (e) => {
            console.log('Exchange changed:', e.target.value);
            this.updateStockSelect(e.target.value);
        });

        // Stock selection
        this.elements.stockSelect.addEventListener('change', (e) => {
            this.elements.addButton.disabled = !e.target.value;
        });

        // Add stock button
        this.elements.addButton.addEventListener('click', () => this.addStock());

        // Time range selection
        document.querySelectorAll('[data-range]').forEach(button => {
            button.addEventListener('click', (e) => {
                this.state.timeRange = e.target.dataset.range;
                document.querySelectorAll('[data-range]').forEach(b =>
                    b.classList.toggle('active', b.dataset.range === this.state.timeRange));
                this.updateChart();
            });
        });

        // Chart type selection
        document.querySelectorAll('[data-chart-type]').forEach(button => {
            button.addEventListener('click', (e) => {
                this.state.chartType = e.target.dataset.chartType;
                document.querySelectorAll('[data-chart-type]').forEach(b =>
                    b.classList.toggle('active', b.dataset.chartType === this.state.chartType));
                this.updateChart();
            });
        });

        console.log('Event listeners initialized');
    }
    async addStock() {
        const stockSelect = this.elements.stockSelect;
        const securityId = stockSelect.value;
        const stockText = stockSelect.options[stockSelect.selectedIndex].text;

        if (!securityId || this.state.activeStocks.has(securityId)) {
            console.log('Stock already added or invalid selection');
            return;
        }

        console.log('Adding stock:', stockText);

        // Add to active stocks with next color
        const color = this.state.colors[this.state.nextColorIndex % this.state.colors.length];
        this.state.nextColorIndex++;

        this.state.activeStocks.set(securityId, {
            color,
            visible: true,
            ticker: stockText.split(' - ')[0] // Get ticker from the option text
        });

        this.updateActiveStocksUI();
        await this.updateChart();
    }

    updateActiveStocksUI() {
        const container = this.elements.activeStocks;
        container.innerHTML = '';

        this.state.activeStocks.forEach((details, securityId) => {
            const chip = document.createElement('div');
            chip.className = 'badge rounded-pill d-flex align-items-center gap-2 p-2 me-2';
            chip.style.backgroundColor = details.color;
            chip.style.color = 'white';
            chip.innerHTML = `
                ${details.ticker}
                <button class="btn-close btn-close-white btn-sm ms-2"
                        onclick="stockAnalysis.removeStock('${securityId}')"></button>
            `;
            container.appendChild(chip);
        });
    }

    async removeStock(securityId) {
        this.state.activeStocks.delete(securityId);
        this.updateActiveStocksUI();
        await this.updateChart();
    }

    showLoading(show) {
        if (this.elements.loadingIndicator) {
            this.elements.loadingIndicator.style.display = show ? 'block' : 'none';
        }
    }

    async updateChart() {
        if (this.state.activeStocks.size === 0) {
            if (this.elements.chartContainer) {
                this.elements.chartContainer.innerHTML = `
                    <div class="text-center text-muted p-5">
                        Select an exchange and stock to begin
                    </div>`;
            }
            return;
        }

        this.showLoading(true);
        const traces = [];
        const volumeTraces = [];

        try {
            for (const [securityId, details] of this.state.activeStocks) {
                const data = await this.fetchStockData(securityId);
                if (!data) continue;

                if (this.state.chartType === 'line') {
                    traces.push({
                        name: details.ticker,
                        x: data.dates,
                        y: data.prices,
                        type: 'scatter',
                        mode: 'lines',
                        line: { color: details.color }
                    });
                } else {
                    traces.push({
                        name: details.ticker,
                        x: data.dates,
                        open: data.open_prices,
                        high: data.high_prices,
                        low: data.low_prices,
                        close: data.prices,
                        type: 'candlestick',
                        increasing: {line: {color: '#00ff00'}},
                        decreasing: {line: {color: '#ff0000'}}
                    });
                }

                volumeTraces.push({
                    name: `${details.ticker} Volume`,
                    x: data.dates,
                    y: data.volumes,
                    type: 'bar',
                    marker: { color: details.color, opacity: 0.5 }
                });
            }

            const layout = {
                showlegend: true,
                xaxis: { rangeslider: { visible: false } },
                yaxis: { title: 'Price' },
                height: 600,
                margin: { t: 20, b: 40, l: 40, r: 40 }
            };

            const volumeLayout = {
                showlegend: true,
                xaxis: { rangeslider: { visible: false } },
                yaxis: { title: 'Volume' },
                height: 200,
                margin: { t: 0, b: 20, l: 40, r: 40 }
            };

            await Plotly.newPlot(this.elements.chartContainer, traces, layout);
            await Plotly.newPlot(this.elements.volumeContainer, volumeTraces, volumeLayout);

        } catch (error) {
            console.error('Error updating chart:', error);
        } finally {
            this.showLoading(false);
        }
    }

    async fetchStockData(securityId) {
        try {
            const response = await fetch(`/api/stock-analysis/${securityId}/price_data/?timerange=${this.state.timeRange}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching stock data:', error);
            return null;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded - Initializing StockAnalysis');
    window.stockAnalysis = new StockAnalysis();
});