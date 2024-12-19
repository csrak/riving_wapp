from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Window, F
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import timedelta
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
import logging
from fin_data_cl.models import Security, PriceData
from fin_data_cl.serializers import PriceDataSerializer
from fin_data_cl.viewsets import BaseFinancialViewSet
from datetime import datetime
logger = logging.getLogger(__name__)


class EnhancedPriceDataViewSet(BaseFinancialViewSet):
    """
    Enhanced ViewSet for price data with advanced technical analysis capabilities.
    Provides endpoints for various chart types and technical indicators.
    """
    model = PriceData
    serializer_class = PriceDataSerializer
    supports_time_range = True
    supports_latest = True
    queryset = PriceData.objects.all()

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for the given DataFrame.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with additional technical indicator columns
        """
        try:
            # Simple Moving Averages
            df['sma_20'] = df['close_price'].rolling(window=20).mean()
            df['sma_50'] = df['close_price'].rolling(window=50).mean()
            df['sma_200'] = df['close_price'].rolling(window=200).mean()

            # Exponential Moving Averages
            df['ema_12'] = df['close_price'].ewm(span=12).mean()
            df['ema_26'] = df['close_price'].ewm(span=26).mean()

            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']

            # RSI
            delta = df['close_price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            df['bb_middle'] = df['close_price'].rolling(window=20).mean()
            std = df['close_price'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (std * 2)
            df['bb_lower'] = df['bb_middle'] - (std * 2)

            return df

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            raise

    @action(detail=False, methods=['GET'])
    def advanced_chart_data(self, request):
        """
        Get comprehensive price data with technical indicators.

        Query Parameters:
            ticker (str): Security ticker
            timeframe (str): Time range (1D, 1W, 1M, 3M, 6M, 1Y, 5Y)
            indicators (list): List of technical indicators to include
        """
        try:
            ticker = request.query_params.get('ticker')
            timeframe = request.query_params.get('timeframe', '1Y')
            indicators = request.query_params.getlist('indicators', [])

            if not ticker:
                return Response({'error': 'ticker parameter is required'}, status=400)

            # Get base queryset
            security = Security.objects.get(ticker=ticker)
            queryset = self.get_queryset().filter(security=security)

            # Calculate date range
            end_date = queryset.order_by('-date').values('date').first()['date']
            start_date = self._get_start_date(end_date, timeframe)

            # Filter and order data
            queryset = queryset.filter(
                date__range=[start_date, end_date]
            ).order_by('date')

            # Convert to DataFrame for calculations
            df = pd.DataFrame(queryset.values(
                'date', 'open_price', 'high_price',
                'low_price', 'close_price', 'volume'
            ))

            # Calculate technical indicators if requested
            if indicators:
                df = self._calculate_technical_indicators(df)

            # Format response data
            response_data = {
                'ticker': ticker,
                'timeframe': timeframe,
                'data': df.to_dict(orient='records'),
                'indicators': indicators
            }

            return Response(response_data)

        except Security.DoesNotExist:
            return Response({'error': f'Security {ticker} not found'}, status=404)
        except Exception as e:
            logger.error(f"Error in advanced_chart_data: {str(e)}")
            return Response({'error': str(e)}, status=500)

    @staticmethod
    def _get_start_date(end_date: datetime.date, timeframe: str) -> datetime.date:
        """Calculate start date based on timeframe."""
        timeframe_mapping = {
            '1D': timedelta(days=1),
            '1W': timedelta(days=7),
            '1M': timedelta(days=30),
            '3M': timedelta(days=90),
            '6M': timedelta(days=180),
            '1Y': timedelta(days=365),
            '5Y': timedelta(days=1825),
        }
        return end_date - timeframe_mapping.get(timeframe, timedelta(days=365))

    @action(detail=False)
    def available_indicators(self, request):
        """Get list of available technical indicators with descriptions."""
        indicators = {
            'sma': {
                'name': 'Simple Moving Average',
                'periods': [20, 50, 200],
                'description': 'Arithmetic mean of prices over specified period'
            },
            'ema': {
                'name': 'Exponential Moving Average',
                'periods': [12, 26],
                'description': 'Weighted moving average emphasizing recent prices'
            },
            'macd': {
                'name': 'MACD',
                'parameters': {'fast': 12, 'slow': 26, 'signal': 9},
                'description': 'Trend-following momentum indicator'
            },
            'rsi': {
                'name': 'Relative Strength Index',
                'period': 14,
                'description': 'Momentum oscillator measuring speed and change of price movements'
            },
            'bollinger': {
                'name': 'Bollinger Bands',
                'parameters': {'period': 20, 'std_dev': 2},
                'description': 'Volatility bands above and below moving average'
            }
        }
        return Response(indicators)

    @action(detail=False)
    def pattern_recognition(self, request):
        """
        Detect common candlestick patterns in the price data.
        Implements basic pattern recognition for common formations.
        """
        ticker = request.query_params.get('ticker')
        lookback = int(request.query_params.get('lookback', 100))

        try:
            security = Security.objects.get(ticker=ticker)
            data = self.get_queryset().filter(
                security=security
            ).order_by('-date')[:lookback]

            patterns = self._detect_patterns(data)
            return Response(patterns)

        except Exception as e:
            logger.error(f"Error in pattern_recognition: {str(e)}")
            return Response({'error': str(e)}, status=500)