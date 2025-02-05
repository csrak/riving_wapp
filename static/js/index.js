
const loadPlotly = () => {
    if (window.Plotly) return Promise.resolve();
    return new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.plot.ly/plotly-2.24.1.min.js';
        script.onload = resolve;
        document.head.appendChild(script);
    });
};

// Main initialization when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // Initialize state variables for chart control
    let currentTicker = null;
    let currentTimeframe = '1Y';

    // Setup loading indicator functions
    function showLoading() {
        document.querySelector('.loading-overlay').style.display = 'flex';
    }

    function hideLoading() {
        document.querySelector('.loading-overlay').style.display = 'none';
    }

    // Handle chart title and statistics updates
    function updateChartTitle(ticker, data) {
        const chartTitle = document.getElementById('chart-title');
        const chartStats = document.getElementById('chart-stats');

        if (!ticker) {
            chartTitle.textContent = 'Market Overview';
            chartStats.textContent = '';
            return;
        }

        chartTitle.textContent = `${ticker} Price History`;

        if (data && data.length > 0) {
            const lastPrice = data[data.length - 1].close_price;
            const firstPrice = data[0].close_price;
            const priceDiff = lastPrice - firstPrice;
            const percentChange = ((priceDiff / firstPrice) * 100).toFixed(2);
            const sign = priceDiff >= 0 ? '+' : '';

            // Map timeframe codes to readable text
            const timeframeText = {
                '1W': 'Past Week',
                '1M': 'Past Month',
                '6M': 'Past 6 Months',
                '1Y': 'Past Year',
                '5Y': 'Past 5 Years',
                'Max': 'All Time'
            }[currentTimeframe] || '';

            chartStats.innerHTML = `
                <span class="me-3">Last: $${lastPrice.toFixed(2)}</span>
                <span class="${priceDiff >= 0 ? 'text-success' : 'text-danger'}">
                    ${sign}${percentChange}% (${timeframeText})
                </span>`;
        }
    }

    // Main function to fetch and render chart data
    function fetchAndRenderChart(ticker, timeframe) {
        if (!ticker) return;

        showLoading();
        const url = `${API_BASE}price-data/candlestick_data/?ticker=${ticker}&timeframe=${timeframe}`;

        fetch(url)
            .then(response => response.json())
            .then(result => {
                if (result.error) {
                    throw new Error(result.error);
                }

                const data = result.data;
                if (!data || !data.length) {
                    throw new Error('No data available');
                }

                // Clean and validate data
                const validData = data.filter(d => (
                    d.open_price != null &&
                    d.high_price != null &&
                    d.low_price != null &&
                    d.close_price != null
                ));

                if (validData.length === 0) {
                    throw new Error('No valid price data available');
                }

                // Prepare data for candlestick chart
                const plotData = [{
                    x: validData.map(d => d.date),
                    open: validData.map(d => Number(d.open_price) || 0),
                    high: validData.map(d => Number(d.high_price) || 0),
                    low: validData.map(d => Number(d.low_price) || 0),
                    close: validData.map(d => Number(d.close_price) || 0),
                    type: 'candlestick',
                    increasing: {line: {color: '#26a69a'}, fillcolor: '#26a69a'},
                    decreasing: {line: {color: '#ef5350'}, fillcolor: '#ef5350'},
                    hoverinfo: 'x+y',
                    hoverlabel: {
                        bgcolor: '#1a237e',
                        font: {color: 'white'}
                    }
                }];

                updateChartTitle(ticker, validData);

                // Configure chart layout
                const layout = {
                    dragmode: 'zoom',
                    showlegend: false,
                    xaxis: {
                        type: 'date',
                        rangeslider: {visible: false},
                        gridcolor: '#f5f5f5',
                        showgrid: true,
                        zeroline: false
                    },
                    yaxis: {
                        autorange: true,
                        title: 'Price ($)',
                        tickformat: '.2f',
                        gridcolor: '#f5f5f5',
                        showgrid: true,
                        zeroline: false
                    },
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white',
                    margin: {t: 10, r: 40, b: 20, l: 60},
                    hovermode: 'x unified'
                };

                // Create the plot with configuration
                Plotly.newPlot('stock-plot', plotData, layout, {
                    responsive: true,
                    scrollZoom: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: [
                        'select2d',
                        'lasso2d',
                        'autoScale2d',
                        'hoverClosestCartesian',
                        'hoverCompareCartesian'
                    ],
                    displaylogo: false
                });
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('stock-plot').innerHTML = `
                    <div class="alert alert-warning m-4">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            <div>
                                <h6 class="alert-heading mb-1">Unable to Load Data</h6>
                                <p class="mb-0">Error: ${error.message}</p>
                            </div>
                        </div>
                    </div>`;
            })
            .finally(hideLoading);
    }

    // Set up click handlers for ticker rows
    document.querySelectorAll('.ticker-row').forEach(row => {
        row.addEventListener('click', function() {
            const ticker = this.dataset.ticker;
            if (ticker) {
                currentTicker = ticker;
                fetchAndRenderChart(ticker, currentTimeframe);

                document.querySelectorAll('.ticker-row').forEach(r =>
                    r.classList.toggle('table-active', r === this));
            }
        });
    });

    // Set up click handlers for timeframe buttons
    document.querySelectorAll('.timeframe-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (!currentTicker) return;

            currentTimeframe = this.dataset.timeframe;
            fetchAndRenderChart(currentTicker, currentTimeframe);

            document.querySelectorAll('.timeframe-btn').forEach(b =>
                b.classList.toggle('active', b === this));
        });
    });

    // Set up handlers for timeframe selector buttons
    document.querySelectorAll('.timeframe-selector').forEach(button => {
        button.addEventListener('click', function() {
            window.location.href = `?timeframe=${this.dataset.timeframe}`;
        });
    });

    // Load Plotly.js before initializing the chart
    await loadPlotly();

    // Load initial chart with default ticker
    const defaultTicker = document.querySelector('.ticker-row')?.dataset.ticker;
    if (defaultTicker) {
        currentTicker = defaultTicker;
        fetchAndRenderChart(defaultTicker, currentTimeframe);
        document.querySelector('.ticker-row').classList.add('table-active');
    }
});
