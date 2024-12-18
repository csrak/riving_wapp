
from zipfile import ZipFile, BadZipfile
from pdfminer.high_level import extract_text
import requests
import pandas as pd
from pathlib import Path
import time
import PyPDF2
import unidecode
import os
import lxml.html as lh
import sys
from django.conf import settings
import re
import unittest
import logging
from unittest.mock import patch
from requests.exceptions import RequestException
from zipfile import BadZipFile
import datetime
# Set up logging for detailed debugging
BASE_DIR = settings.BASE_DIR

logging.basicConfig(level=logging.DEBUG)
G_datafold = BASE_DIR / 'media' / 'Data' / 'Chile'
G_root_dir = BASE_DIR
##Scraiping of PDF or (online not working, not matter since source does not work well anymore)
class Ticker:
    datafold = G_datafold
    root_dir = G_root_dir

    def __init__(self, ticker, rut, name):
        """
        Initialize a Ticker object with a ticker symbol, RUT, and name.
        """
        self.ticker = ticker
        self.rut = rut
        self.name = name

    @classmethod
    def from_scraped_data(cls, scraped_data):
        """
        Initialize Ticker objects from scraped data (a list of dictionaries).
        """
        return [cls(data['Ticker'], data['RUT'], data['Name']) for data in scraped_data]

    @classmethod
    def scrape_tickers(cls, offline=False):
        """
        Scrapes tickers from the Bolsa de Santiago PDF or loads from local storage if offline.
        """
        file_name = Path('list_of_tickers.pdf')
        tickers = []

        if not offline:
            url = (
                'http://cibe.bolsadesantiago.com/EmisoresyValores/Nminas%20Emisores/1.%20N%C3%B3mina%20Emisores%20de%20Acciones.pdf'
            )
            print(f"Scraping tickers from: {url}")
            try:
                response = requests.get(url)
                response.raise_for_status()
                with open(cls.datafold / file_name, 'wb') as f:
                    f.write(response.content)
                time.sleep(5)  # Wait for the download to finish
            except requests.exceptions.RequestException as e:
                print(f"Failed to download tickers: {e}")
                return []

        # Open and read the PDF file
        try:
            with open(cls.datafold / file_name, 'rb') as filepdf:
                filling = PyPDF2.PdfFileReader(filepdf)
                table = []
                for i in range(filling.numPages):
                    page = filling.getPage(i)
                    temp = page.extractText()
                    table.append(temp.split('\n'))
            # After parsing the PDF
            print(f"Parsed pages: {len(table)}")
            print(f"Sample parsed data: {table[:2]}")  # Checking the first two pages or entries

        except FileNotFoundError:
            print(f"Ticker file not found at: {cls.datafold / file_name}")
            return []

        # Parsing the table to get tickers, RUT, and names
        tickers, rut, names = ['Ticker'], ['RUT'], ['Name']
        count = 1
        companies_full = []

        for pages in table:
            pages = [value for value in pages if value != '']
            companies = []
            temp_elem = []  # Initialize temp_elem here to ensure it's defined
            while True:
                found_companies = [i for i in pages if i.startswith(str(count))]
                if len(found_companies) == 0:
                    break
                for ix, comp in enumerate(found_companies):
                    length = len(str(count))
                    if comp[length].isnumeric():
                        continue
                    else:
                        companies.append(comp)
                        count += 1
                for ix, comp in enumerate(companies):
                    if ix != len(companies) - 1:
                        indexs = pages.index(comp)
                        indexf = pages.index(companies[ix + 1])
                        temp_elem = []
                        for ins in range(indexs, indexf):
                            temp_elem.append(pages[ins])
                        temp_elem = ' '.join(temp_elem).lstrip('0123456789.- ')
                        temp_elem = temp_elem.split(" ")
                    companies_full.append(temp_elem)

        for comp in companies_full:
            rut.append(comp[-1].replace('.', ''))
            tickers.append(comp[0])
            count = 0
            while "-" in comp[count]:
                count += 1
            names.append(' '.join(comp[count:-2]))
            if "-BA" in comp[1]:
                rut.append(comp[-1].replace('.', ''))
                tickers.append(comp[0].replace("-A", "-B"))
                names.append(' '.join(comp[count:-2]))

        # Unidecode formatting for consistent data
        final_list = [tickers, rut, names]
        temp_final_list = []
        for j in range(len(tickers)):
            dim = []
            for i in range(len(final_list)):
                dim.append(unidecode.unidecode(final_list[i][j]))
            temp_final_list.append(dim)
        final_list = temp_final_list
        column_names = final_list.pop(0)

        # Save to CSV
        df = pd.DataFrame(final_list, columns=column_names)
        try:
            df.to_csv(cls.datafold / 'registered_stocks.csv', index=None, header=True)
        except Exception as e:
            print(f"Error saving tickers to file: {e}")
            return []

        # Return a list of Ticker objects
        scraped_data = df.to_dict(orient='records')
        return cls.from_scraped_data(scraped_data)

    @classmethod
    def load_tickers_from_file(cls):
        """
        Load ticker data from a CSV file and return a list of Ticker objects.
        """
        file_name = 'registered_stocks.csv'
        filepath = cls.datafold / file_name
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                scraped_data = df.to_dict(orient='records')
                return cls.from_scraped_data(scraped_data)
            except pd.errors.EmptyDataError:
                print(f"CSV file at {filepath} is empty.")
                return []
        else:
            print(f"{file_name} not found at {filepath}. Please run Ticker.scrape_tickers() first.")
            return []

    def __repr__(self):
        return f"Ticker(ticker={self.ticker}, rut={self.rut}, name={self.name})"

    @classmethod
    def get_ticker_by_symbol(cls, symbol):
        """
        Retrieves a Ticker object by its ticker symbol.
        """
        tickers = cls.load_tickers_from_file()
        for ticker in tickers:
            if ticker.ticker == symbol:
                return ticker
        print(f"Ticker with symbol {symbol} not found.")
        return None

    @classmethod
    def get_all_tickers(cls):
        """
        Retrieves all Ticker objects from the file.
        """
        return cls.load_tickers_from_file()
    @classmethod
    def get_all_tickers_as_dataframe(cls):
        """
        Retrieves all Ticker objects from the file and returns them as a DataFrame.
        """
        tickers = cls.get_all_tickers()
        data = [{'Ticker': t.ticker, 'RUT': t.rut, 'Name': t.name} for t in tickers]
        return pd.DataFrame(data)
class FileDownloader:
    """
    Handles downloading and extracting files from URLs.
    Includes methods to download, save, and extract files of different types.
    """
    def __init__(self, root_dir, datafold, agent):
        """
        Initializes the FileDownloader class with root directory, data folder, and request headers for downloading files.
        """
        self.root_dir = root_dir
        self.datafold = datafold
        self.agent = agent
        self.session = requests.Session()

    def download_files(self, urls, filenames, update=False):
        """
        Downloads files from the provided URLs, saves them locally, and extracts if necessary.
        Checks if a file already exists before downloading based on the update flag.
        """
        for url, filename in zip(urls, filenames):
            if filename == '0':
                continue

            file_path = self.root_dir / self.datafold / Path(filename)

            # Skip download if the file already exists and update is not set
            if not update and file_path.exists():
                print(f"Already downloaded {file_path} and Update not set")
                continue

            # Download the file
            myfile = self._download_file(url)
            if not myfile:
                print(f"Failed to download {url} after multiple attempts")
                continue

            # Save the downloaded file
            self._save_file(file_path, myfile)

            # Handle file types: extract zip, parse pdf, or save others
            if filename.endswith('.zip'):
                self._extract_zip(file_path)
            #elif filename.endswith('.pdf'):
            #    self._parse_pdf(file_path)
            else:
                print(f"File saved at {file_path}")

    def _download_file(self, url, max_retries=9):
        """
        Handles downloading a file with retry logic to ensure robustness against temporary network issues.
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=self.agent)
                response.raise_for_status()
                return response
            except KeyboardInterrupt:
                print("Interrupted")
                sys.exit(0)
            except requests.RequestException as e:
                print(f"Error: {e}\n  Trying again ({attempt + 1}/{max_retries})")
                time.sleep(1)
        return None

    def _save_file(self, file_path, response):
        """
        Saves the content of the response to the specified file path.
        """
        with open(file_path, 'wb') as file:
            file.write(response.content)

    def _extract_zip(self, zip_path, max_retries=12):
        """
        Attempts to extract a zip file with retry logic to handle issues like incomplete downloads.
        """
        extract_path = zip_path.with_suffix('')
        if not extract_path.exists():
            os.makedirs(extract_path, exist_ok=True)

        print(f"Extracting {extract_path}...\n")
        for attempt in range(max_retries):
            try:
                with ZipFile(zip_path, 'r') as zip_obj:
                    zip_obj.extractall(extract_path)
                print(f"Successfully extracted {zip_path} to {extract_path}")
                return
            except BadZipfile:
                print(f"Still extracting ({(attempt + 1) * 5} seconds) {extract_path}\n")
                time.sleep(5)

        print(f"Error extracting {extract_path}. Please extract manually before proceeding")

    def _parse_pdf(self, pdf_path):
        """
        Parses a PDF file to extract text content using pdfminer.six.
        """
        try:
            text = extract_text(pdf_path)
            if text:
                print(f"Successfully parsed PDF: {pdf_path}\nExtracted text sample:\n{text[:200]}...")
            else:
                print(f"No text found in PDF: {pdf_path}")
        except Exception as e:
            print(f"Error parsing PDF {pdf_path}: {e}")

class CmfScraping:
    """
    Responsible for scraping links and file URLs from the CMF Chile website and uses FileDownloader to download these files.
    """
    datafold = G_datafold
    root_dir = G_root_dir
    agent = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"
    }

    def __init__(self, tickers):
        """
        Initializes the CmfScraping class
        """

        self.companies_list = tickers#.get_all_tickers_as_dataframe()
        self.downloader = FileDownloader(self.root_dir, self.datafold, self.agent)
        return

    def scrap_all_analysis(self, month, year):
        """
        Scrapes company links, and downloads the relevant files using FileDownloader.
        """
        if month not in ['03', '06', '09', '12']:
            raise ValueError("Month must be one of the reporting months: 03, 06, 09, 12")
        company_links = self.scrap_company_links(month, year)
        flinks = []
        fnames = ['0'] * len(company_links)

        # Loop through each company link to scrape file links and set filenames for downloading
        for i, link in enumerate(company_links):
            if link == 'Not Found':
                print(f"Link not found for company index {i}, skipping...")
                flinks.append('Invalid Link')
                continue

            print(f'Scraping {link}, please wait...')
            try:
                file_link = self.scrap_file_links(link)
                flinks.append(file_link)
                if file_link != 'Not Found':
                    fnames[i] = f"{month}-{year}/Analisis_{self.companies_list.loc[i, 'Ticker']}_{month}-{year}.pdf"
            except requests.RequestException as e:
                print(f"Error scraping file link for {link}: {e}")
                flinks.append('Invalid Link')

        # Create directory for storing downloaded data if it doesn't exist
        folder_data = self.datafold / Path(f"{month}-{year}")
        print(folder_data)
        os.makedirs(folder_data, exist_ok=True)

        # Creates an instance of FileDownloader to handle the downloading of files

        # Uses the FileDownloader instance to download the files whose links were scraped
        self.downloader.download_files(flinks, fnames, update=False)

    def scrap_company_links(self, month, year):
        """
        Scrapes the company links from the CMF Chile website for a specific month and year.
        Iterates over all links and matches them with each company's RUT to find the correct link.
        """
        url = f'https://www.cmfchile.cl/institucional/mercados/novedades_envio_sa_ifrs.php?mm_ifrs={month}&aa_ifrs={year}'
        out = ['Not Found'] * self.companies_list.shape[0]
        print(url)
        try:
            page = requests.get(url, headers=self.agent)
            page.raise_for_status()
            #print('page', page.content)
            page = lh.fromstring(page.content)
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e} -> Trying next one")
            return out

        # Iterate over all links to match them with each company's RUT
        links = page.xpath('//a')
        #print(links)
        for link in links:
            for i in range(self.companies_list.shape[0]):
                rut = self.companies_list.loc[i, 'RUT']
                rut = rut.split('-')[0]
                if 'href' in link.attrib and rut in link.attrib['href']:
                    out[i] = link.attrib['href']
                    out[i] = f'https://www.cmfchile.cl/institucional/mercados/{out[i]}'
        return out

    def scrap_file_links(self, url):
        """
        Scrapes the file link from a given company page URL if it contains the required financial analysis document.
        """
        try:
            page = requests.get(url, headers=self.agent)
            page.raise_for_status()
            page = lh.fromstring(page.content)
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e} -> Skipping link {url}")
            return 'Not Found'

        # Iterate over all links found on the company page to identify the link to the financial analysis document
        links = page.xpath('//a')
        for link in links:
            if 'href' in link.attrib and 'Razonado' in link.text_content():
                out = link.attrib['href']
                out = f'https://www.cmfchile.cl/institucional{out[2:]}'
                out = re.sub(' ', '%20', out)
                return out

        return 'Not Found'

    def scrap_dividends(
            self,
            year_i,
            year_f=0,
            types=[1, 2, 3],
            to_file=True
    ):
        """
        Scrape comprehensive dividend information for Chilean companies.

        Args:
        - year_i: Initial year for dividend retrieval
        - year_f: Final year (default: current year)
        - types: Types of dividends to select
        - to_file: Whether to save results to a file

        Returns:
        - DataFrame with detailed dividend information
        """
        # Determine final year
        if year_f == 0:
            year_f = datetime.now().year
        elif (year_f - year_i) < 0:
            raise ValueError("Initial year must be before or equal to final year")

        # Load registered stocks
        file_name = 'registered_stocks.csv'
        df1 = pd.read_csv(self.datafold / file_name)

        # Prepare lists of tickers and RUTs
        tickers = self.companies_list['Ticker'].tolist()
        ruts = self.companies_list['RUT'].tolist()

        # Prepare to collect dividend data
        final_dataframe = []

        # Iterate through companies
        for counter, rut in enumerate(ruts):
            # Skip companies with ERROR in RUT
            if "ERROR" in rut:
                continue

            ticker = tickers[counter]

            # Determine series based on ticker naming convention
            if '-A' in ticker:
                series = 'A'
            elif '-B' in ticker:
                series = 'B'
            elif '-C' in ticker:
                series = 'C'
            else:
                series = 'U'  # Universal/default series

            # Construct URL for dividend scraping
            url = (
                "https://www.cmfchile.cl/institucional/estadisticas/acc_dividendos1grid.php?"
                f"lang=es&sociedad%5B%5D={rut[:-2]}&tipodiv=0&mes=0&anno={year_i}&"
                f"mes2=0&anno2={year_f}&xls=y&semana=&vsn=2"
            )
            print(url)
            logging.info(f"Parsing url for {ticker}: {url}")

            try:
                # Fetch dividend data
                page = requests.get(url, headers=self.agent)

                # Read Excel data
                df = pd.read_excel(page.content, header=6, engine="openpyxl")

                # Filter by series and dividend types
                df = df[
                    (df['Serieafecta'].isin([series, 'U'])) &
                    (df['Tipodedividendo(1)'].isin(types))
                    ]

                # Ensure date is properly parsed
                df['Date'] = pd.to_datetime(df['Fecha'], infer_datetime_format=True)

                # Calculate dividends with exchange rate
                df['Dividend'] = df.iloc[:, 12] * df['Tasadecambio']

                # Add additional columns for tracking
                df['Ticker'] = ticker
                df['Series'] = series

                # Select and rename relevant columns
                dividend_df = df[['Date', 'Dividend', 'Ticker', 'Series', 'Tipodedividendo(1)']]
                dividend_df.columns = ['Date', 'Dividend', 'Ticker', 'Series', 'DividendType']

                final_dataframe.append(dividend_df)

            except BadZipFile:
                logging.warning(f"Bad zip file for {ticker}")
                continue
            except Exception as e:
                logging.error(f"Error processing {ticker}: {e}")
                continue

        # Combine results
        try:
            result = pd.concat(final_dataframe)

            # Sort by date for better readability
            result = result.sort_values('Date')

            # Reset index for clean output
            result = result.reset_index(drop=True)
        except ValueError:
            print("No data found in range, please check.")
            return None

        # Save to file if requested
        if to_file:
            # Ensure Dividends directory exists
            dividends_path = self.datafold / 'Dividends'
            dividends_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            file_name = f'Dividends_{year_i}_{year_f}.csv'
            full_path = dividends_path / file_name

            result.to_csv(full_path, index=False)

        return result


class TestCmfScraping(unittest.TestCase):
    #@patch('requests.get')  # Mocking the requests.get call
    def test_retrieve_first_three_documents(self):
        """
        Unit test to verify that the first three documents for the first ticker can be retrieved.
        Includes detailed logging for better debugging.
        """
        # Mock response setup
        #mock_get.return_value.status_code = 200
        #mock_get.return_value.content = "<html>Mock content for testing</html>"

        # Retrieve all tickers as a DataFrame from the Ticker class
        try:
            all_tickers = Ticker.get_all_tickers_as_dataframe()
            logging.debug(f"Successfully retrieved tickers: {all_tickers.head()}")
        except Exception as e:
            logging.error(f"Error retrieving tickers: {e}")
            self.fail("Ticker retrieval failed.")

        # Pass only the first row (first company) to CmfScraping
        try:
            for i in ['03','06','09','12']:
                cmf_scraping = CmfScraping(tickers=all_tickers.head(1), month=i, year='2023')
        except ValueError as e:
            logging.error(f"Invalid month provided: {e}")
            self.fail("Invalid month provided.")
        except RequestException as e:
            logging.error(f"Failed to scrape links: {e}")
            self.fail("Failed to scrape company links due to network error.")

        # Retrieve only the first three links for documents
        flinks = cmf_scraping.company_links[:3]
        logging.debug(f"Retrieved first three links: {flinks}")

if __name__ == "__main__":
    #unittest.main()
    start_year = 2013
    end_year = None
    if end_year is None:
        end_year = datetime.now().year
    try:
        all_tickers = Ticker.get_all_tickers_as_dataframe()
        logging.debug(f"Successfully retrieved tickers: {all_tickers.head()}")
    except Exception as e:
        logging.error(f"Error retrieving tickers: {e}")
    cmf_scraping = CmfScraping(tickers=all_tickers.head(1))
    for year in range(start_year, end_year + 1):
        try:
            for i in ['03','06','09','12']:
                cmf_scraping.scrap_all_analysis(month=i, year='2023')
        except ValueError as e:
            logging.error(f"Invalid month provided: {e}")
        except RequestException as e:
            logging.error(f"Failed to scrape links: {e}")

