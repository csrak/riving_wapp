from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from django.db.models import QuerySet
import numpy as np
from fin_data_cl.models import PriceData


class StockVisualizer:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.figure = None
        self.price_data = None
        self.errors = []

    def load_data(self, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> bool:
        """
        Load price data from Django model into pandas DataFrame.
        Returns True if data was loaded successfully, False otherwise.
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=180)

            queryset = PriceData.objects.filter(
                ticker=self.ticker,
                date__range=(start_date, end_date)
            ).order_by('date')

            if not queryset.exists():
                self.errors.append(f"No data found for ticker {self.ticker} in the specified date range")
                return False

            # Convert queryset to DataFrame
            self.price_data = pd.DataFrame.from_records(
                queryset.values('date', 'open_price', 'high_price',
                                'low_price', 'close_price', 'volume')
            )

            # Clean the data
            # Replace None/NULL values with NaN for proper handling
            self.price_data = self.price_data.replace([None], np.nan)

            # Check for missing or invalid values
            required_columns = ['open_price', 'high_price', 'low_price', 'close_price']
            missing_data = self.price_data[required_columns].isnull().any()

            if missing_data.any():
                missing_cols = missing_data[missing_data].index.tolist()
                self.errors.append(f"Missing values found in columns: {', '.join(missing_cols)}")

                # Forward fill missing values
                self.price_data = self.price_data.fillna(method='ffill')
                # Backward fill any remaining NaN values at the beginning
                self.price_data = self.price_data.fillna(method='bfill')

            # Validate price relationships
            invalid_highs = self.price_data[self.price_data['high_price'] < self.price_data['low_price']]
            if not invalid_highs.empty:
                self.errors.append(f"Found {len(invalid_highs)} records where high price is less than low price")
                # Fix by swapping high and low prices
                self.price_data.loc[invalid_highs.index, ['high_price', 'low_price']] = \
                    self.price_data.loc[invalid_highs.index, ['low_price', 'high_price']].values

            return True

        except Exception as e:
            self.errors.append(f"Error loading data: {str(e)}")
            return False

    def create_candlestick_figure(self,
                                  show_volume: bool = True,
                                  height: int = 800,
                                  title: Optional[str] = None) -> Optional[go.Figure]:
        """
        Create interactive candlestick chart with optional volume subplot.
        Returns None if data is not available or invalid.
        """
        if self.price_data is None or self.price_data.empty:
            self.errors.append("No data available. Call load_data() first.")
            return None

        try:
            # Create figure with secondary y-axis for volume
            fig = make_subplots(
                rows=2 if show_volume else 1,
                cols=1,
                row_heights=[0.7, 0.3] if show_volume else [1],
                vertical_spacing=0.05,
                shared_xaxes=True
            )

            # Add candlestick trace
            fig.add_trace(
                go.Candlestick(
                    x=self.price_data['date'],
                    open=self.price_data['open_price'],
                    high=self.price_data['high_price'],
                    low=self.price_data['low_price'],
                    close=self.price_data['close_price'],
                    name='OHLC'
                ),
                row=1, col=1
            )

            if show_volume and 'volume' in self.price_data.columns:
                # Ensure volume values are valid
                volume_data = self.price_data['volume'].fillna(0)

                # Calculate colors based on price movement
                colors = ['red' if close < open else 'green'
                          for close, open in zip(self.price_data['close_price'],
                                                 self.price_data['open_price'])]

                fig.add_trace(
                    go.Bar(
                        x=self.price_data['date'],
                        y=volume_data,
                        name='Volume',
                        marker_color=colors,
                        opacity=0.5
                    ),
                    row=2, col=1
                )

            # Update layout
            fig.update_layout(
                title=title or f'{self.ticker} Stock Price',
                height=height,
                xaxis_rangeslider_visible=False,
                template='plotly_dark',
                showlegend=True
            )

            self.figure = fig
            return fig

        except Exception as e:
            self.errors.append(f"Error creating chart: {str(e)}")
            return None

    def add_ma_overlay(self, periods: List[int] = [20, 50, 200]) -> bool:
        """
        Add Moving Average overlays.
        Returns True if successful, False otherwise.
        """
        if self.figure is None:
            self.errors.append("Create candlestick figure first")
            return False

        try:
            for period in periods:
                # Skip if period is longer than available data
                if period > len(self.price_data):
                    self.errors.append(f"Not enough data for {period}-day MA")
                    continue

                ma = self.price_data['close_price'].rolling(window=period).mean()

                self.figure.add_trace(
                    go.Scatter(
                        x=self.price_data['date'],
                        y=ma,
                        name=f'{period}MA',
                        line=dict(width=1)
                    ),
                    row=1, col=1
                )
            return True

        except Exception as e:
            self.errors.append(f"Error adding moving averages: {str(e)}")
            return False

    def get_errors(self) -> List[str]:
        """Return list of accumulated errors."""
        return self.errors