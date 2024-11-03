
from finriv.settings import BASE_DIR
import logging
from requests.exceptions import RequestException
import datetime
# Set up logging for detailed debugging
logging.basicConfig(level=logging.DEBUG)
G_datafold = BASE_DIR / 'media' / 'Data' / 'Chile'
G_root_dir = BASE_DIR
from django.core.management.base import BaseCommand
from finriv.utils.scrapping_classes import Ticker,CmfScraping

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #unittest.main()
        start_year = 2013
        end_year = None
        if end_year is None:
            end_year = datetime.datetime.now().year
        try:
            all_tickers = Ticker.get_all_tickers_as_dataframe()
            logging.debug(f"Successfully retrieved tickers: {all_tickers.head()}")
        except Exception as e:
            logging.error(f"Error retrieving tickers: {e}")
        for year in range(start_year, end_year + 1):
            try:
                for i in ['03','06','09','12']:
                    cmf_scraping = CmfScraping(tickers=all_tickers, month=i, year=str(year))
            except ValueError as e:
                logging.error(f"Invalid month provided: {e}")
            except RequestException as e:
                logging.error(f"Failed to scrape links: {e}")

