import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from llama_index.core import Document, Settings, SimpleDirectoryReader, VectorStoreIndex
from openai import OpenAI as OpenAIog
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
from fin_data_cl.models import RiskComparison as Model_Risk
from fin_data_cl.models import Exchange, Security
import logging
import time
from pydantic import BaseModel, Field
from collections import defaultdict
from django.utils import timezone
import openai
from dateutil.relativedelta import relativedelta
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

G_datafold = Path(settings.MEDIA_ROOT) / 'Data' / 'Chile'
G_root_dir = Path(settings.BASE_DIR)

def get_api_key(file_path: Path) -> str:
    with open(file_path, 'r') as file:
        api_key = file.read().strip()
    return api_key

class ReportLocator:
    def __init__(self, data_folder: Path):
        self.data_folder = data_folder

    def get_consecutive_quarter_pairs(self) -> List[Tuple[Path, Path]]:
        """
        Get pairs of consecutive quarter folders from oldest to newest.
        Warns and stops if a quarter is missing.

        Returns:
            List[Tuple[Path, Path]]: List of folder pairs up to the first missing quarter
        """
        folders = self.get_period_folders()
        if len(folders) < 2:
            return []

        folder_pairs = []
        for i in range(len(folders) - 1):
            current_folder = folders[i]
            next_folder = folders[i + 1]

            # Parse dates
            current_date = datetime.strptime(current_folder.name, "%m-%Y")
            next_date = datetime.strptime(next_folder.name, "%m-%Y")

            # Calculate expected next quarter
            expected_next = current_date + relativedelta(months=3)
            expected_next_str = expected_next.strftime("%m-%Y")

            # Check if the next folder is the expected one
            if next_date != expected_next:
                print(f"\nAnalysis stopped: No folder found for {expected_next_str}")
                print(f"Last processed quarter: {current_folder.name}")
                return folder_pairs

            folder_pairs.append((current_folder, next_folder))

        return folder_pairs

    def process_quarters(self, callback=None):
        """
        Process all quarters in sequence, handling missing folders.

        Args:
            callback: Optional function to process each pair of folders
                     Should accept (earlier_folder, next_folder) as parameters
        """
        folders = self.get_period_folders()
        if not folders:
            print("No quarterly folders found.")
            return

        current_folder = folders[0]
        print(f"Starting analysis from oldest quarter: {current_folder.name}")

        while True:
            # Calculate expected next quarter
            current_date = datetime.strptime(current_folder.name, "%m-%Y")
            expected_next = current_date + relativedelta(months=3)
            expected_next_str = expected_next.strftime("%m-%Y")

            # Find the next folder
            next_folder = None
            for folder in folders:
                if folder.name == expected_next_str:
                    next_folder = folder
                    break

            if next_folder is None:
                print(f"\nAnalysis stopped: No folder found for {expected_next_str}")
                print(f"Last processed quarter: {current_folder.name}")
                break

            print(f"Processing: {current_folder.name} -> {next_folder.name}")

            # Execute callback if provided
            if callback:
                callback(current_folder, next_folder)

            current_folder = next_folder
    def get_period_folders(self) -> List[Path]:
        """Get all valid period folders sorted by date."""
        pattern = re.compile(r"^(03|06|09|12)-\d{4}$")
        folders = [f for f in self.data_folder.iterdir() if f.is_dir() and pattern.match(f.name)]
        return sorted(folders, key=lambda x: datetime.strptime(x.name, "%m-%Y"))

    def get_company_file(self, period_folder: Path, ticker: str):
        """Get the file path for a specific company in a period."""
        pattern = f"Analisis_{ticker.upper()}_*-*.pdf"
        files = list(period_folder.glob(pattern))
        return files[0] if files else None

    def get_first_ticker(self):
        """Get the first ticker found in the oldest year."""
        oldest_folders = self.get_oldest_year_folders()
        if not oldest_folders:
            return None

        pattern = re.compile(r"Analisis_([A-Z]+)_\d{2}-\d{4}\.pdf")

        for folder in oldest_folders:
            for file in folder.glob("*.pdf"):
                if match := pattern.match(file.name):
                    return match.group(1)
        return None

    def get_oldest_year_folders(self) -> List[Path]:
        """Get folders from the oldest year only."""
        all_folders = self.get_period_folders()
        if not all_folders:
            return []

        oldest_year = datetime.strptime(all_folders[0].name, "%m-%Y").year
        return [f for f in all_folders if datetime.strptime(f.name, "%m-%Y").year == oldest_year]


    def get_tickers_in_period(self, period_folder: Path) -> List[str]:
        """
        Get all tickers found in a specific period folder.

        Args:
            period_folder (Path): Path to the period folder

        Returns:
            List[str]: List of tickers found in the period
        """
        pattern = re.compile(r"Analisis_([A-Z]+)_\d{2}-\d{4}\.pdf")
        tickers = []

        for file in period_folder.glob("*.pdf"):
            if match := pattern.match(file.name):
                tickers.append(match.group(1))

        return sorted(tickers)


    def get_ticker_paths_by_period(self) -> Dict[str, List[Path]]:
        """
        Get all existing paths for each ticker, ordered from oldest to newest.

        Returns:
            Dict[str, List[Path]]: Dictionary where keys are tickers and values are lists of paths
                                 ordered from oldest to newest
        """
        ticker_paths = defaultdict(list)
        period_folders = self.get_period_folders()

        for folder in period_folders:
            for file in folder.glob("*.pdf"):
                pattern = re.compile(r"Analisis_([A-Z]+)_\d{2}-\d{4}\.pdf")
                if match := pattern.match(file.name):
                    ticker = match.group(1)
                    ticker_paths[ticker].append(file)

        # Sort paths for each ticker by date
        for ticker in ticker_paths:
            ticker_paths[ticker].sort(key=lambda x: datetime.strptime(
                x.parent.name, "%m-%Y"
            ))

        return dict(ticker_paths)

import json
import time
from typing import Dict, Optional

class Risks(BaseModel):
    name: str
    description: str

class RiskComparison(BaseModel):
    new_risks: list[Risks]
    removed_risks: list[Risks]
    modified_risks: list[Risks]

class ReportAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = OpenAI(model="gpt-4o-mini", api_key=api_key)
        Settings.llm = self.llm

    def create_index_for_document(self, file_path: str) -> Optional[VectorStoreIndex]:
        try:
            reader = SimpleDirectoryReader(input_files=[file_path])
            documents = reader.load_data()
            return VectorStoreIndex.from_documents(documents)
        except Exception as e:
            logging.error(f"Error creating index for {file_path}: {e}")
            return None

    def compare_reports(self, file1: str, file2: str):
        """Compare two reports and identify risk changes."""
        index1 = self.create_index_for_document(file1)
        index2 = self.create_index_for_document(file2)

        if not index1 or not index2:
            logging.error("Failed to create indices for comparison")
            return None

        query_engine1 = index1.as_query_engine()
        query_engine2 = index2.as_query_engine()

        risk_prompt = """
        Extract and list all risks mentioned in the document comprehensively.
        Include risk factors, business risks, market risks, operational risks, financial risks, regulatory risks, and reputational risks.
        Provide detailed descriptions for each risk, include names, numbers and percentages, including context and potential impact.
        Text might be in spanish, but you write in english. 
        """

        risks1 = query_engine1.query(risk_prompt).response
        risks2 = query_engine2.query(risk_prompt).response
        #print(risks1)
        #print(risks2)
        comparison_prompt = f"""
        Compare these two sets of risks and categorize the changes:

        First period risks:
        {risks1}

        Second period risks:
        {risks2}

        Provide analysis in english using the following structured output:
        - New Risks: List of risks that appear only in the second period. Describe them in detail.
        - Removed Risks: List of risks that only appeared in the first period.  Describe them in detail.
        - Modified Risks:List of risks that only appeared in the first period.  Describe the changes in detail.
        Ensure that all changes are captured comprehensively, and provide sufficient context for each change.We do not care about languages only the meaning. Be specific about numbers, and specific details: Example: 
        Instead of general phrases such as "In the second period, there’s a more detailed description of credit risk" say what the new description is.
        """

        max_retries = 5
        retry_delay = 20  # seconds

        # Use OpenAI functions from LlamaIndex to perform the comparison query
        client = OpenAIog(api_key= self.api_key)
        completion = client.beta.chat.completions.parse(model="gpt-4o-mini", messages = [
        {"role":"system", "content":"You are an expert in financial analysis, providing detailed risk assessments."},
        {"role":"user", "content":comparison_prompt}  ], response_format=RiskComparison)
        #print(completion.choices[0].message.parsed)
        #print(dir(response))
        return completion.choices[0].message.parsed



class Command(BaseCommand):
    help = 'Run a sample analysis for the first ticker in the oldest year'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exchange',
            type=str,
            required=True,
            help='Exchange code to update (e.g., NYSE)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done. Not updated.'
        )
        parser.add_argument(
            '--do_all',
            action='store_true',
            help='Do all. Only tested current run option.'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='analysis_results',
            help='Optional: Specify output directory. '
        )
        parser.add_argument(
            '--start-year',
            type=int,
            help='The year to start processing quarters from (e.g., 2022)'
        )

    def write_results(self, output_dir: Path, ticker: str, period1: str, period2: str, results: str):
        """Write analysis results to a file."""
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            filename = f"{ticker}_{period1}_to_{period2}_analysis.txt"
            output_file = output_dir / filename

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("New Risks:\n")
                for l in results.new_risks:
                    f.write(l.name+ ": " + l.description +'\n')
                f.write("Removed Risks:\n")
                for l in results.removed_risks:
                    f.write(l.name+ ": " + l.description +'\n')
                f.write("Modified Risks:\n")
                for l in results.modified_risks:
                    f.write(l.name+ ": " + l.description +'\n')
            return output_file
        except Exception as e:
            logger.error(f"Error writing results: {e}")
            return None

    def handle(self, *args, **options):
        try:
            data_folder = G_datafold
            output_dir = Path(options['output_dir'])

            api_key = get_api_key(G_root_dir / 'api_key')

            analyzer = ReportAnalyzer(api_key)
            locator = ReportLocator(data_folder)
            start_year = options.get('start_year')
            exchange_code = options['exchange'].upper()
            exchange = Exchange.objects.get(code=exchange_code)
            securities = Security.objects.filter(
                exchange=exchange,
                is_active=True
            )
            if options['do_all']:
                quarter_pairs = locator.get_consecutive_quarter_pairs()

                # Filter pairs by the start year if provided
                if start_year:
                    quarter_pairs = [
                        (q1, q2) for q1, q2 in quarter_pairs
                        if datetime.strptime(q1.name, "%m-%Y").year >= start_year
                    ]
                for earlier_quarter, next_quarter in quarter_pairs:
                    print(f"Processing quarters: {earlier_quarter.name} -> {next_quarter.name}")
                    old_tickers = locator.get_tickers_in_period(earlier_quarter)
                    new_tickers = locator.get_tickers_in_period(next_quarter)
                    for tick in old_tickers:
                        filename = f"{tick}_{earlier_quarter.name}_to_{next_quarter.name}_analysis.txt"
                        out_file = output_dir / Path(filename)
                        if out_file.exists():
                            print(f"comparison {tick} : {earlier_quarter.name} -> {next_quarter.name} already exists. Skipping")
                            continue
                        print(f"Processing {tick}")
                        if tick in new_tickers:
                            file1 = locator.get_company_file(earlier_quarter, tick)
                            file2 = locator.get_company_file(next_quarter, tick)
                            if not file1 or not file2:
                                self.stdout.write(self.style.WARNING(
                                    f"Missing files for comparison {tick} : {earlier_quarter.name} -> {next_quarter.name}"
                                ))
                                continue

                            comparison = analyzer.compare_reports(str(file1), str(file2))
                            if not comparison:
                                self.stdout.write(self.style.WARNING("Comparison produced no results"))
                                continue

                            output_file = self.write_results(
                                output_dir,
                                tick,
                                earlier_quarter.name,
                                next_quarter.name,
                                comparison
                            )
                            # We'll use period 2 as reference
                            security_ob = securities.filter(ticker=tick).first()
                            current_time = timezone.now()
                            financial_risk, created = Model_Risk.objects.get_or_create(
                                security=security_ob,
                                date=datetime.strptime(next_quarter.name, '%m-%Y').date(),
                                created_at=current_time,
                                updated_at=current_time,
                                defaults={
                                    'new_risks': [i.name + "\n" + i.description for i in comparison.new_risks],
                                    'old_risks': [i.name + "\n" + i.description for i in comparison.removed_risks],
                                    'modified_risks': [i.name + "\n" + i.description for i in comparison.modified_risks]
                                })
                            financial_risk.save()
                            if output_file:
                                self.stdout.write(self.style.SUCCESS(
                                    f"Successfully analyzed {tick} for periods "
                                    f"{earlier_quarter.name} -> {next_quarter.name}\n"
                                    f"Results written to: {output_file}"
                                ))
                return
            ticker = locator.get_first_ticker()
            if not ticker:
                self.stdout.write(self.style.ERROR("No tickers found in the data folder"))
                return

            oldest_periods = locator.get_oldest_year_folders()
            if len(oldest_periods) < 2:
                self.stdout.write(self.style.ERROR(
                    "Not enough periods found in the oldest year for comparison"
                ))
                return

            self.stdout.write(f"Found ticker: {ticker}")
            self.stdout.write(
                f"Analyzing year: {datetime.strptime(oldest_periods[0].name, '%m-%Y').year}"
            )

            if options['dry_run']:
                self.stdout.write("Dry run - would analyze these periods:")
                for i in range(len(oldest_periods) - 1):
                    self.stdout.write(
                        f"  {oldest_periods[i].name} -> {oldest_periods[i + 1].name}"
                    )
                return

            for i in range(len(oldest_periods) - 1):
                period1, period2 = oldest_periods[i], oldest_periods[i + 1]
                self.stdout.write(f"Comparing {period1.name} -> {period2.name}")

                file1 = locator.get_company_file(period1, ticker)
                file2 = locator.get_company_file(period2, ticker)

                if not file1 or not file2:
                    self.stdout.write(self.style.WARNING(
                        f"Missing files for comparison {period1.name} -> {period2.name}"
                    ))
                    continue

                comparison = analyzer.compare_reports(str(file1), str(file2))
                if not comparison:
                    self.stdout.write(self.style.WARNING("Comparison produced no results"))
                    continue

                output_file = self.write_results(
                    output_dir,
                    ticker,
                    period1.name,
                    period2.name,
                    comparison
                )
                #We'll use period 2 as reference

                current_time = timezone.now()
                financial_risk, created = Model_Risk.objects.get_or_create(
                    ticker=ticker,
                    year=int(datetime.strptime(period2.name, '%m-%Y').year),
                    month=int(datetime.strptime(period2.name, '%m-%Y').month),
                    defaults={
                        'new_risks': [i.name + "\n" + i.description for i in comparison.new_risks],
                        'old_risks': [i.name + "\n" + i.description for i in comparison.removed_risks],
                        'modified_risks': [i.name + "\n" + i.description for i in comparison.modified_risks]
                })
                financial_risk.save()
                if output_file:
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully analyzed {ticker} for periods "
                        f"{period1.name} -> {period2.name}\n"
                        f"Results written to: {output_file}"
                    ))



        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in handle: {e}"))
            logger.error(f"Error in handle: {e}")
            raise