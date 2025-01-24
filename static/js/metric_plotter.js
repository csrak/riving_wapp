/**
 * metric_plotter.js
 *  Metrics Plotter
 *
 * This provides plotting of financial metrics data.
 * It handles user interactions, data fetching, and visualization using Plotly.js.
 *
 */

class MetricPlotter {
    /**
     * Configuration settings for the MetricPlotter
     * Modify these values to change the behavior of the plotter
     */
    static CONFIG = {
        // Maximum number of metrics that can be plotted simultaneously
        MAX_METRICS: 4,

        // Delay in milliseconds before updating the plot after user interaction
        DEBOUNCE_DELAY: 300,

        // Duration of animations in milliseconds
        ANIMATION_DURATION: 300,

        // Default plot height in pixels
        PLOT_HEIGHT: 600,

        // Color palette for metrics
        COLORS: [
            '#1f77b4',  // Blue
            '#ff7f0e',  // Orange
            '#2ca02c',  // Green
            '#d62728',  // Red
            '#9467bd',  // Purple
            '#8c564b'   // Brown
        ],

        // Plot margins
        MARGINS: { l: 60, r: 30, t: 50, b: 50 },

    responsive: true,
    displayModeBar: true,
    displaylogo: false
    };

    /**
     * Initialize the MetricPlotter instance
     */
    constructor() {
        // Initialize instance variables
        this.currentMetrics = 0;
        this.plot = null;
        this.debounceTimer = null;
        this.cachedMetrics = null;

        // Initialize component
        this.initializeEventListeners();
        this.loadExchanges();
        this.updateMetricCounter();
        this.setEmptyState();
    }

    /**
     * DOM Element Getters
     * Cached getters for frequently accessed DOM elements
     */
    get exchangeSelect() { return document.getElementById('exchange-select'); }
    get securitySelect() { return document.getElementById('security-select'); }
    get metricsContainer() { return document.getElementById('metrics-container'); }
    get addMetricBtn() { return document.getElementById('add-metric-btn'); }
    get plotArea() { return document.getElementById('plot-area'); }
    get loadingOverlay() { return document.querySelector('.loading-overlay'); }

    /**
     * Initialize all event listeners for user interactions
     * @private
     */
    initializeEventListeners() {
        // Exchange selection handler
        this.exchangeSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                this.handleExchangeChange(e.target.value);
            }
        });

        // Security selection handler
        this.securitySelect.addEventListener('change', (e) => {
            if (e.target.value) {
                this.handleSecurityChange(e.target.value);
            }
        });

        // Add metric button handler
        this.addMetricBtn.addEventListener('click', () => this.addMetricRow());

        // Metric container event delegation
        this.metricsContainer.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('.remove-metric');
            if (removeBtn) {
                this.handleMetricRemove(removeBtn);
            }
        });

        this.metricsContainer.addEventListener('change', (e) => {
            if (e.target.classList.contains('metric-select')) {
                this.debouncedUpdate();
            }
        });

        // Time range button handlers
        document.querySelector('.btn-group').addEventListener('click', (e) => {
            if (e.target.classList.contains('time-range-btn')) {
                this.handleTimeRangeChange(e.target);
            }
        });
    }

    /**
     * UI State Management Methods
     */

    /**
     * Show loading overlay with spinner
     * @private
     */
    showLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.visibility = 'visible';
            this.loadingOverlay.classList.add('visible');
        }
    }

    /**
     * Hide loading overlay with animation
     * @private
     */
    hideLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.remove('visible');
            setTimeout(() => {
                this.loadingOverlay.style.visibility = 'hidden';
            }, MetricPlotter.CONFIG.ANIMATION_DURATION);
        }
    }

    /**
     * Update the metric counter display
     * @private
     */
    updateMetricCounter() {
        const currentMetricsElements = document.querySelectorAll('[id^="current-metrics"]');
        const maxMetricsElements = document.querySelectorAll('[id^="max-metrics"]');

        currentMetricsElements.forEach(element => {
            element.textContent = this.currentMetrics;
        });

        maxMetricsElements.forEach(element => {
            element.textContent = MetricPlotter.CONFIG.MAX_METRICS;
        });
    }

    /**
     * Set empty state display
     * @private
     */
    setEmptyState() {
        this.plotArea.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-graph-up"></i>
                <p class="mb-0">Select an exchange, security, and metrics to begin plotting</p>
            </div>
        `;
    }

    /**
     * Data Loading Methods
     */

    /**
     * Load available exchanges from the API
     * @returns {Promise<void>}
     */
    async loadExchanges() {
        try {
            this.showLoading();
            const response = await fetch(`${FINANCIAL_DATA_API}available_exchanges/`);
            const data = await response.json();

            this.exchangeSelect.innerHTML = [
                '<option value="">Select Exchange</option>',
                ...data.exchanges.map(exchange =>
                    `<option value="${exchange.id}">${exchange.name}</option>`
                )
            ].join('');
        } catch (error) {
            this.handleError('Failed to load exchanges', error);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Load securities for a given exchange
     * @param {string} exchangeId - The ID of the exchange
     * @returns {Promise<void>}
     */
    async loadSecurities(exchangeId) {
        try {
            this.showLoading();
            const response = await fetch(
                `${FINANCIAL_DATA_API}securities_by_exchange/?exchange_id=${exchangeId}`
            );
            const data = await response.json();

            this.securitySelect.innerHTML = [
                '<option value="">Select Security</option>',
                ...data.securities.map(security =>
                    `<option value="${security.id}">${security.ticker} - ${security.name}</option>`
                )
            ].join('');

            this.securitySelect.disabled = false;
        } catch (error) {
            this.handleError('Failed to load securities', error);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Load available metrics from the API
     * @returns {Promise<Array>}
     */
    async loadMetrics() {
        if (this.cachedMetrics) return this.cachedMetrics;

        try {
            const response = await fetch(`${FINANCIAL_DATA_API}metrics/`);
            const data = await response.json();
            this.cachedMetrics = data;
            return data;
        } catch (error) {
            this.handleError('Failed to load metrics', error);
            return [];
        }
    }

    /**
     * Event Handlers
     */

    /**
     * Handle exchange selection change
     * @param {string} exchangeId - The selected exchange ID
     * @private
     */
    async handleExchangeChange(exchangeId) {
        this.securitySelect.value = '';
        this.metricsContainer.innerHTML = '';
        this.currentMetrics = 0;
        this.updateMetricCounter();
        this.addMetricBtn.disabled = true;
        this.setEmptyState();
        await this.loadSecurities(exchangeId);
    }

    /**
     * Handle security selection change
     * @param {string} securityId - The selected security ID
     * @private
     */
    handleSecurityChange(securityId) {
        this.addMetricBtn.disabled = false;
        if (this.currentMetrics === 0) {
            this.addMetricRow();
        }
    }

    /**
     * Handle metric removal
     * @param {HTMLElement} removeBtn - The remove button element
     * @private
     */
    handleMetricRemove(removeBtn) {
        const metricRow = removeBtn.closest('.metric-row');
        metricRow.classList.add('removing');

        setTimeout(() => {
            metricRow.remove();
            this.currentMetrics--;
            this.updateMetricCounter();
            this.addMetricBtn.disabled = false;
            this.debouncedUpdate();
        }, MetricPlotter.CONFIG.ANIMATION_DURATION);
    }

    /**
     * Handle time range button click
     * @param {HTMLElement} button - The clicked time range button
     * @private
     */
    handleTimeRangeChange(button) {
        document.querySelectorAll('.time-range-btn')
            .forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        this.debouncedUpdate();
    }

    /**
     * Add a new metric selection row
     * @returns {Promise<void>}
     * @private
     */
    async addMetricRow() {
        if (this.currentMetrics >= MetricPlotter.CONFIG.MAX_METRICS) return;

        const metrics = await this.loadMetrics();
        const row = document.createElement('div');
        row.className = 'metric-row';
        row.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <select class="form-select metric-select" style="min-width: 0">
                    <option value="">Select Metric</option>
                    ${metrics.map(metric =>
                        `<option value="${metric.field}">${metric.display_name}</option>`
                    ).join('')}
                </select>
                <button class="btn btn-outline-danger remove-metric" style="min-width: 0">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;

        this.metricsContainer.appendChild(row);
        this.currentMetrics++;
        this.updateMetricCounter();
        this.addMetricBtn.disabled = this.currentMetrics >= MetricPlotter.CONFIG.MAX_METRICS;
    }

    /**
     * Plot Management Methods
     */

    /**
     * Update the plot with current selections
     * @returns {Promise<void>}
     * @private
     */
    async updatePlot() {
        const securityId = this.securitySelect.value;
        if (!securityId) return;

        const selectedMetrics = Array.from(document.querySelectorAll('.metric-select'))
            .map(select => select.value)
            .filter(Boolean);

        if (!selectedMetrics.length) return;

        try {
            this.showLoading();
            const data = await this.fetchPlotData(securityId, selectedMetrics);
            await this.renderPlot(data, selectedMetrics);
        } catch (error) {
            this.handleError('Failed to update plot', error);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Fetch plot data from the API
     * @param {string} securityId - The selected security ID
     * @param {Array<string>} selectedMetrics - Array of selected metric fields
     * @returns {Promise<Object>}
     * @private
     */
    async fetchPlotData(securityId, selectedMetrics) {
        const timeRange = document.querySelector('.time-range-btn.active').dataset.range;
        let url = `${FINANCIAL_DATA_API}`;

        if (timeRange !== 'max') {
            const endDate = new Date();
            const startDate = new Date();
            startDate.setFullYear(endDate.getFullYear() - parseInt(timeRange));
            url = `${FINANCIAL_DATA_API}date_range/?security_id=${securityId}&start_date=${startDate.toISOString()}&end_date=${endDate.toISOString()}`;
        } else {
            url += `?security=${securityId}&metrics=${selectedMetrics.join(',')}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Render the plot using Plotly.js
     * @param {Object} data - The plot data
     * @param {Array<string>} selectedMetrics - Array of selected metric fields
     * @returns {Promise<void>}
     * @private
     */
    async renderPlot(data, selectedMetrics) {
        const traces = selectedMetrics.map((metric, index) => ({
            x: data.dates,
            y: data[metric],
            name: document.querySelector(`option[value="${metric}"]`).textContent,
            type: 'scatter',
            mode: 'lines+markers',
            line: {
                color: MetricPlotter.CONFIG.COLORS[index % MetricPlotter.CONFIG.COLORS.length],
                width: 2
            },
            marker: {
                size: 6
            }
        }));

        const layout = {
            title: {
                text: `Financial Metrics - ${this.securitySelect.selectedOptions[0].text}`,
                font: { size: 20 }
            },
            xaxis: {
                title: 'Date',
                tickangle: -45,
                gridcolor: 'rgba(0,0,0,0.1)'
            },
            yaxis: {
                title: 'Value',
                gridcolor: 'rgba(0,0,0,0.1)'
            },
            showlegend: true,
            height: MetricPlotter.CONFIG.PLOT_HEIGHT,
            margin: MetricPlotter.CONFIG.MARGINS,
            hovermode: 'x unified',
            plot_bgcolor: 'white',
            paper_bgcolor: 'white',
            autosize: true,
            showlegend: true,
            legend: {
                orientation: 'h',  // horizontal legend below
                y: -0.2,          // position below the plot
                x: 0.5,           // centered
                xanchor: 'center'
            },
            margin: {
                l: 50, r: 30, t: 30, b: 100  // extra bottom margin for legend
            },
            xaxis: {
                automargin: true,
                tickangle: -45
            },
            yaxis: {
                automargin: true
    }
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtons: [['zoom2d', 'pan2d', 'resetScale2d', 'toImage']]
        };

        await Plotly.newPlot(this.plotArea, traces, layout, config);
    }

    /**
     * Utility Methods
     */

    /**
     * Debounce plot updates to prevent excessive API calls
     * @private
     */
    debouncedUpdate() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(
            () => this.updatePlot(),
            MetricPlotter.CONFIG.DEBOUNCE_DELAY
        );
    }

/**
     * Handle errors and display user feedback
     * @param {string} message - Error message to display
     * @param {Error} [error] - Optional error object for logging
     * @private
     */
    handleError(message, error = null) {
        console.error(message, error);

        // Create and show error toast
        const errorToast = document.createElement('div');
        errorToast.className = 'alert alert-danger alert-dismissible fade show position-fixed bottom-0 end-0 m-3';
        errorToast.setAttribute('role', 'alert');
        errorToast.innerHTML = `
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        document.body.appendChild(errorToast);

        // Remove toast after 5 seconds
        setTimeout(() => {
            errorToast.remove();
        }, 5000);
    }

    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date string
     * @private
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    /**
     * Format number for display
     * @param {number} value - Number to format
     * @param {number} [decimals=2] - Number of decimal places
     * @returns {string} Formatted number string
     * @private
     */
    formatNumber(value, decimals = 2) {
        if (typeof value !== 'number' || isNaN(value)) return '-';
        return new Intl.NumberFormat(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(value);
    }

    /**
     * Check if the plot area is visible in viewport
     * @returns {boolean} True if plot area is visible
     * @private
     */
    isPlotVisible() {
        if (!this.plotArea) return false;
        const rect = this.plotArea.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    /**
     * Resize plot to fit container
     * @private
     */
    resizePlot() {
        if (this.plot && this.isPlotVisible()) {
            Plotly.Plots.resize(this.plotArea);
        }
    }
}

/**
 * Window resize handler with debounce
 */
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        if (window.metricPlotter) {
            window.metricPlotter.resizePlot();
        }
    }, 250);
});

/**
 * Initialize the plotter when the DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    // Create and store the plotter instance
    window.metricPlotter = new MetricPlotter();

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Update max metrics UI
    const maxMetrics = MetricPlotter.CONFIG.MAX_METRICS;
    document.querySelectorAll('[data-max-metrics]').forEach(element => {
        element.textContent = maxMetrics;
    });

    // Update tooltip content
    const addMetricBtn = document.getElementById('add-metric-btn');
    if (addMetricBtn) {
        addMetricBtn.setAttribute(
            'title',
            `Maximum ${maxMetrics} metrics can be plotted simultaneously`
        );
    }
});
  function updatePlotLayout() {
    const isMobile = window.innerWidth < 768;
    const plotArea = document.getElementById('plot-area');

    if (window.Plotly && plotArea.data) {
      const update = {
        'legend.orientation': isMobile ? 'h' : 'v',
        'legend.y': isMobile ? -0.5 : 1,
        'legend.x': isMobile ? 0.5 : 1.02,
        'legend.xanchor': isMobile ? 'center' : 'left',
        'legend.yanchor': isMobile ? 'top' : 'auto',
        'margin.b': isMobile ? 100 : 50,
        'margin.r': isMobile ? 20 : 100,
        'xaxis.tickangle': isMobile ? -45 : 0
      };

      Plotly.relayout(plotArea, update);
    }
  }

  // Add resize listener
  window.addEventListener('resize', () => {
    clearTimeout(window.resizeTimer);
    window.resizeTimer = setTimeout(updatePlotLayout, 250);
  });

  // Modify your existing plot creation code to include this initial setup
  const defaultLayout = {
    autosize: true,
    showlegend: true,
    hovermode: 'x unified',
    legend: {
      bgcolor: 'rgba(255,255,255,0.9)',
      bordercolor: 'rgba(0,0,0,0.1)',
      borderwidth: 1
    },
    margin: { t: 30 },
    xaxis: {
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)'
    },
    yaxis: {
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)'
    }
  };