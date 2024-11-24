# views.py
from django.shortcuts import render
from .plot_prices import StockVisualizer
from fin_data_cl.models import PriceData
from datetime import datetime
from django.contrib import messages

def stock_chart_view(request):
    try:
        # Get unique tickers from database
        tickers = PriceData.objects.values_list('ticker', flat=True).distinct()

        if not tickers.exists():
            messages.error(request, "No stock data available in the database.")
            return render(request, 'stock_chart.html', {'tickers': []})

        # Default to first ticker if none selected
        selected_ticker = request.GET.get('ticker', tickers.first())

        plot_div = None
        errors = []

        if selected_ticker:
            # Create visualizer and load data
            viz = StockVisualizer(selected_ticker)

            # Load data and check for success
            if viz.load_data():
                # Create basic candlestick chart
                fig = viz.create_candlestick_figure(show_volume=True)

                if fig is not None:
                    # Add moving averages if we have a valid figure
                    viz.add_ma_overlay()

                    # Example signals (you'll replace with your ML signals)
                    try:
                        example_signals = {
                            datetime(2024, 1, 1): {'description': 'Buy Signal'},
                            datetime(2024, 1, 15): {'description': 'Sell Signal'}
                        }
                        viz.add_signal_overlay(example_signals, 'Trading Signals')
                    except Exception as e:
                        errors.append(f"Could not add signals: {str(e)}")

                    # Convert to HTML
                    plot_div = fig.to_html(full_html=False)

            # Collect any errors from the visualizer
            errors.extend(viz.get_errors())

            # Display errors as messages
            for error in errors:
                if "Error" in error:
                    messages.error(request, error)
                else:
                    messages.warning(request, error)

        return render(request, 'stock_chart.html', {
            'plot_div': plot_div,
            'tickers': tickers,
            'selected_ticker': selected_ticker,
        })

    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return render(request, 'stock_chart.html', {
            'tickers': [],
            'error': str(e)
        })