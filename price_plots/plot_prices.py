from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from django.db.models import QuerySet
import numpy as np
from fin_data_cl.models import PriceData, DividendData, Security


class StockVisualizer:
    def __init__(self, security: Security):
        self.security = security
        self.figure = None
        self.price_data = None
        self.dividend_data = None
        self.errors = []

    def load_data(self, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> bool:
        """
        Load price and dividend data from Django models into pandas DataFrames.
        Returns True if data was loaded successfully, False otherwise.
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=180)

            # Load price data
            price_queryset = PriceData.objects.filter(
                security=self.security,
                date__range=(start_date, end_date)
            ).order_by('date')

            if not price_queryset.exists():
                self.errors.append(f"No price data found for security {self.security.full_symbol} in the specified date range")
                return False

            # Convert queryset to DataFrame
            self.price_data = pd.DataFrame.from_records(
                price_queryset.values('date', 'open_price', 'high_price',
                                      'low_price', 'close_price', 'volume')
            )

            # Clean the price data
            self.price_data = self.price_data.replace([None], np.nan)
            required_columns = ['open_price', 'high_price', 'low_price', 'close_price']
            missing_data = self.price_data[required_columns].isnull().any()

            if missing_data.any():
                missing_cols = missing_data[missing_data].index.tolist()
                self.errors.append(f"Missing values found in columns: {', '.join(missing_cols)}")
                self.price_data = self.price_data.fillna(method='ffill').fillna(method='bfill')

            # Validate price relationships
            invalid_highs = self.price_data[self.price_data['high_price'] < self.price_data['low_price']]
            if not invalid_highs.empty:
                self.errors.append(f"Found {len(invalid_highs)} records where high price is less than low price")
                self.price_data.loc[invalid_highs.index, ['high_price', 'low_price']] = \
                    self.price_data.loc[invalid_highs.index, ['low_price', 'high_price']].values

            # Load dividend data
            dividend_queryset = DividendData.objects.filter(
                security=self.security,
                date__range=(start_date, end_date)
            ).order_by('date')

            if dividend_queryset.exists():
                self.dividend_data = pd.DataFrame.from_records(
                    dividend_queryset.values('date', 'amount', 'dividend_type')
                )
                if self.dividend_data.empty:
                    self.errors.append("Dividend data exists but could not be loaded into the DataFrame.")
                else:
                    print(self.dividend_data)  # Debugging: check the content of the DataFrame

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
        Include dividends as markers with their own y-axis.
        Returns None if data is not available or invalid.
        """
        if self.price_data is None or self.price_data.empty:
            self.errors.append("No data available. Call load_data() first.")
            return None

        try:
            # Ensure dates are sorted for proper plotting
            self.price_data.sort_values('date', inplace=True)

            # Create figure with secondary y-axis for volume and dividends
            fig = make_subplots(
                rows=2 if show_volume else 1,
                cols=1,
                row_heights=[0.7, 0.3] if show_volume else [1],
                vertical_spacing=0.05,
                shared_xaxes=True,
                specs=[[{"secondary_y": True}], [{"secondary_y": False}]] if show_volume else [[{"secondary_y": True}]]
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

            # Add volume bars if enabled
            if show_volume and 'volume' in self.price_data.columns:
                volume_data = self.price_data['volume'].fillna(0)
                colors = ['red' if close < open else 'green'
                          for close, open in zip(self.price_data['close_price'], self.price_data['open_price'])]

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

            # Add dividend markers if available
            if self.dividend_data is not None and not self.dividend_data.empty:
                dividend_colors = {1: 'rgba(0, 0, 255, 0.5)', 2: 'rgba(255, 165, 0, 0.5)', 3: 'rgba(128, 0, 128, 0.5)'}
                for dividend_type, color in dividend_colors.items():
                    filtered_data = self.dividend_data[self.dividend_data['dividend_type'] == dividend_type]
                    if not filtered_data.empty:
                        fig.add_trace(
                            go.Bar(
                                x=filtered_data['date'],
                                y=filtered_data['amount'],
                                name=f'Dividend Type {dividend_type}',
                                marker=dict(color=color),
                                opacity=0.7,
                                yaxis='y2'
                            ),
                            row=1, col=1,
                            secondary_y=True
                        )

            # Update layout for better appearance
            fig.update_layout(
                title=title or f'{self.security.ticker} Stock Price with Dividends',
                height=height,
                xaxis_rangeslider_visible=False,
                template='plotly_white',
                showlegend=True,
                yaxis_title='Price',
                yaxis2_title='Dividend Amount'
            )

            self.figure = fig
            return fig.to_html(full_html=False)  # Convert to HTML

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
