import unittest
import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
import logging
import sys
import requests
from pprint import pformat

# Create a logger for diagnostics
logger = logging.getLogger('yahoo_finance_diagnostics')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

class YahooFinanceDiagnostics(unittest.TestCase):
    """Tests to diagnose issues with Yahoo Finance data retrieval"""

    def print_dataframe_diagnostics(self, df, prefix=""):
        """Print detailed diagnostic information about a DataFrame"""
        if df is None:
            logger.warning(f"{prefix}DataFrame is None")
            return

        if not isinstance(df, pd.DataFrame):
            logger.warning(f"{prefix}Not a DataFrame, but a {type(df).__name__}")
            logger.warning(f"{prefix}Value: {df}")
            return

        if df.empty:
            logger.warning(f"{prefix}DataFrame is empty")
            return

        logger.info(f"{prefix}DataFrame info:")
        logger.info(f"{prefix}  Shape: {df.shape}")
        logger.info(f"{prefix}  Columns: {list(df.columns)}")
        logger.info(f"{prefix}  Index type: {type(df.index).__name__}")

        # Check index in more detail
        if isinstance(df.index, pd.DatetimeIndex):
            logger.info(f"{prefix}  Index is DatetimeIndex")
            if len(df.index) > 0:
                logger.info(f"{prefix}  Date range: {df.index.min()} to {df.index.max()}")
                logger.info(f"{prefix}  Number of days: {(df.index.max() - df.index.min()).days + 1}")

        # Show all index values if not too many
        if len(df.index) <= 10:
            logger.info(f"{prefix}  All index values: {list(df.index)}")
        else:
            logger.info(f"{prefix}  First few index values: {list(df.index[:5])}")
            logger.info(f"{prefix}  Last few index values: {list(df.index[-5:])}")

        # Check for missing values
        missing_vals = df.isnull().sum()
        if missing_vals.sum() > 0:
            logger.warning(f"{prefix}  Columns with missing values:")
            for col, count in missing_vals[missing_vals > 0].items():
                logger.warning(f"{prefix}    {col}: {count} missing values")

        # Show a sample of data
        logger.info(f"{prefix}  Sample data (first row):")
        for col in df.columns:
            if len(df) > 0:
                val = df[col].iloc[0]
                val_type = type(val).__name__
                val_str = str(val)
                if len(val_str) > 50:
                    val_str = val_str[:47] + "..."
                logger.info(f"{prefix}    {col} ({val_type}): {val_str}")

        # Print dtypes
        logger.info(f"{prefix}  Column dtypes:")
        for col, dtype in df.dtypes.items():
            logger.info(f"{prefix}    {col}: {dtype}")

    def test_actual_yahoo_finance_data(self):
        """Test retrieving actual data from Yahoo Finance"""
        # Test parameters
        ticker_symbol = "SQM-A.SN"
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # Last 30 days

        logger.info(f"Testing Yahoo Finance data retrieval")
        logger.info(f"Ticker: {ticker_symbol}")
        logger.info(f"Date range: {start_date} to {end_date}")

        try:
            # Create ticker object
            ticker = yf.Ticker(ticker_symbol, session = session)

            # Check ticker info
            logger.info("Retrieving ticker info...")
            info = ticker.info

            if not info:
                logger.warning("Ticker info is empty")
            else:
                # Print a selection of important keys
                important_keys = ['symbol', 'shortName', 'longName', 'currency', 'exchange']
                info_subset = {k: info.get(k) for k in important_keys if k in info}
                logger.info(f"Ticker info: {info_subset}")

                if 'symbol' in info and info['symbol'] != ticker_symbol:
                    logger.warning(f"Symbol mismatch: requested {ticker_symbol}, got {info['symbol']}")

            # Get historical data
            logger.info(f"Retrieving historical data from {start_date} to {end_date}...")
            hist = ticker.history(start=start_date, end=end_date + timedelta(days=1))

            # Print diagnostics
            logger.info("Historical data diagnostics:")
            self.print_dataframe_diagnostics(hist, "  ")

            # Additional checks for historical data
            if hist.empty:
                logger.critical(f"No historical data found for {ticker_symbol} from {start_date} to {end_date}")

                # Try retrieving with a longer time range to see if any data is available
                logger.info("Trying with a longer time range (90 days)...")
                wider_start = end_date - timedelta(days=90)
                wider_hist = ticker.history(start=wider_start, end=end_date + timedelta(days=1))

                if wider_hist.empty:
                    logger.critical("No data found even with extended time range")
                else:
                    logger.info(f"Found {len(wider_hist)} days of data with extended range")
                    logger.info(f"Data available from {wider_hist.index.min()} to {wider_hist.index.max()}")

                    # Check if there might be an issue with the specific date range
                    if wider_hist.index.max() < start_date:
                        logger.warning(
                            f"Latest available data ({wider_hist.index.max()}) is before requested start date ({start_date})")
            else:
                # Check if the returned date range matches what was requested
                actual_start = hist.index.min().date()
                actual_end = hist.index.max().date()

                if actual_start > start_date:
                    logger.warning(f"Returned start date ({actual_start}) is later than requested ({start_date})")

                if actual_end < end_date:
                    logger.warning(f"Returned end date ({actual_end}) is earlier than requested ({end_date})")

                # Check for expected columns
                expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                missing_columns = [col for col in expected_columns if col not in hist.columns]

                if missing_columns:
                    logger.warning(f"Missing expected columns: {missing_columns}")
                    logger.warning(f"Available columns: {list(hist.columns)}")

                # Look for non-numeric values in price columns
                price_columns = [col for col in ['Open', 'High', 'Low', 'Close'] if col in hist.columns]

                for col in price_columns:
                    non_numeric = hist[col].apply(lambda x: not (isinstance(x, (int, float)) or pd.isna(x))).any()
                    if non_numeric:
                        logger.warning(f"Non-numeric values found in {col} column")
                        # Show examples of non-numeric values
                        non_numeric_rows = hist[
                            hist[col].apply(lambda x: not (isinstance(x, (int, float)) or pd.isna(x)))]
                        logger.warning(f"Examples of non-numeric values in {col}:")
                        for idx, val in zip(non_numeric_rows.index, non_numeric_rows[col]):
                            logger.warning(f"  {idx}: {val} (type: {type(val).__name__})")

        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            logger.error("Traceback:")
            import traceback
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    unittest.main()