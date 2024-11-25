
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
    def add_arguments(self, parser):
        parser.add_argument(
            '--start-year',
            type=int,
            help='The year to start processing quarters from (e.g., 2022)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only do 5 companies, only for 2024'
        )
        parser.add_argument(
            '--dividends',
            action='store_true',
            help='Scrap dividends'
        )
        parser.add_argument(
            '--analysis',
            action='store_true',
            help='Scrap reasoned analysis'
        )

    def handle(self, *args, **kwargs):
        #unittest.main()
        dry_run = kwargs['dry_run']
        dividends = kwargs['dividends']
        analysis = kwargs['analysis']
        if dry_run:
            end_year=2024
            start_year=2024
            all_tickers = Ticker.get_all_tickers_as_dataframe().head(5)
        else:
            end_year = None
            start_year = kwargs['start_year']
            all_tickers = Ticker.get_all_tickers_as_dataframe()

        if end_year is None:
            end_year = datetime.datetime.now().year
        try:
            logging.debug(f"Successfully retrieved tickers: {all_tickers.head()}")
        except Exception as e:
            logging.error(f"Error retrieving tickers: {e}")
        for year in range(start_year, end_year + 1):
            try:
                for i in ['03','06','09','12']:
                    cmf_scraping = CmfScraping(tickers=all_tickers, month=i, year=str(year))
                    if analysis:
                        cmf_scraping.scrap_all_analysis()
            except ValueError as e:
                logging.error(f"Invalid month provided: {e}")
            except RequestException as e:
                logging.error(f"Failed to scrape links: {e}")
        if dividends:
            cmf_scraping.scrap_dividends(start_year,end_year)

