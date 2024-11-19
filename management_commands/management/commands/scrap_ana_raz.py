# my_app/management/commands/run_my_script.py
from django.core.management.base import BaseCommand
#from finriv.utils.scrapping_classes import test as test_ticker
from finriv.settings import BASE_DIR
from finriv.utils.scrapping_classes import Ticker,TestCmfScraping
from fin_data_cl.models import FinancialReport
import unittest
from pathlib import Path
G_datafold = BASE_DIR / 'media' / 'Data' / 'Chile'
G_root_dir = BASE_DIR

import os, time
import pandas as pd
from pathlib import Path
import fitz  # PyMuPDF
import re
import json
from llama_index.llms.ollama import Ollama

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
from llama_index.core import Settings, VectorStoreIndex, Document, SimpleDirectoryReader
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
import shutil
import tempfile
from llama_index.embeddings.openai import OpenAIEmbedding
from pydantic import BaseModel, Field
from openai import OpenAI as OpenAIog
from llama_index.program.openai import OpenAIPydanticProgram
import logging
def get_api_key(file_path):
    with open(file_path, 'r') as file:
        api_key = file.read().strip()  # Strip removes any extra spaces or newlines
    return api_key
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# class BaseModel:
#     def to_json(self):
#         return json.dumps(self, default=lambda o: o.__dict__, indent=4)

class FinancialMetrics(BaseModel):
    revenue: str
    net_income: str
    operating_margin: str
    gross_profit_margin: str
    debt_to_equity: str
    earnings_per_share: str
    free_cash_flow: str
class HistoricalChange(BaseModel):
    category: str
    description: str
    impact: str

class Risk(BaseModel):
    category: str
    description: str
    potential_impact: str

class FutureOutlook(BaseModel):
    category: str
    description: str
    likelihood: str


class FinancialAnalysis(BaseModel):
    business_overview: str
    risks: list[Risk]
    metrics: Optional[FinancialMetrics]
    historical_changes: list[HistoricalChange]
    future_outlook: list[FutureOutlook]

class FinancialDocumentAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        # Initialize LlamaIndex settings
        self.api_key=api_key
        self.llm = OpenAI(model='gpt-4o-mini', api_key=api_key)
        embed_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=api_key)
        # Update settings
        Settings.llm = self.llm
        Settings.embed_model = embed_model

        self.node_parser = SimpleNodeParser.from_defaults()
        self._init_query_templates()


        # Define query templates

    def _init_query_templates(self):
        """Initialize query templates for different analysis components"""
        self.queries = {
            "business_overview": """
                Extract a complete business overview from the financial document.
                Focus on: main business activities, revenue streams, and market position.
                Be specific and include key details about the company's operations, including countries and regions. Format it in a readable way.Write in english. If anything is missing say it is missing in the document..
            """,

            "risks": """
                List the main risks mentioned in the financial document.
                For each risk, specify:
                1. Risk Category (must be one of: Operational, Financial, Market, Regulatory)
                2. Detailed description of the risk
                3. Potential impact on the business
                Format each risk on a new line starting with the category. Go in detail about said risks, specially numerical aspects, dates and names.  Write in english.If anything is missing say it is missing in the document.
            """,

            "metrics": """
                Extract the following financial metrics from the document:
                - Revenue (in millions/billions)
                - Net Income (in millions/billions)
                - Operating Margin (as percentage)
                - Gross Profit Margin (as percentage)
                - Debt to Equity Ratio
                - Earnings per Share
                - Free Cash Flow
                Provide only the numbers and currency units, with each metric on a new line. Write in english.
            """,

            "changes": """
                Identify significant changes mentioned in the document compared to previous periods.
                For each change:
                1. Specify the category of change
                2. Describe what changed
                3. Explain the impact
                List each change on a new line. Be very detailed about these changes. Write in english. If anything is missing say it is missing in the document.
            """,

            "outlook": """
                Extract future outlook information from the document.
                For each point:
                1. Specify the category
                2. Describe the expected change or development
                3. Indicate likelihood as: High, Medium, or Low
                List each point on a new line. Be very detailed about these outlooks.Write in english.If anything is missing say it is missing in the document.
            """
        }

    @staticmethod
    def make_text_query( text):
        return f"""Given the following response:

\"\"\"
{text}
\"\"\"


Structure the output corectly, do not omit any informatiion in your response. Make sure all the information is conveyed, if information belongs to more than one classification put it on both. Make sure it is clear and concise. 
"""
    @staticmethod

    def create_index_for_document(file_path: str) -> Optional[VectorStoreIndex]:
        try:
            reader = SimpleDirectoryReader(input_files=[file_path])
            documents = reader.load_data()
            return VectorStoreIndex.from_documents(documents)
        except Exception as e:
            logging.error(f"Error creating index for {file_path}: {e}")
            return None
    def analyze_document(self, document: str):
        # Create document and index
        #document = Document(text=document_text)
        index = self.create_index_for_document(document)
        # Create query engine
        query_engine = index.as_query_engine()

        # Execute queries and parse responses
        responses = {}
        text_query = " "
        for query_type, query_text in self.queries.items():
            response = query_engine.query(query_text)
            responses[query_type] = response.response
            text_query = text_query + response.response + " - "

        client = OpenAIog(api_key=self.api_key)
        completion = client.beta.chat.completions.parse(model="gpt-4o-mini", messages=[
            {"role": "system",
             "content": "You are an information retrieval and classification tool. You also know how to classify and understand financial information."},
            {"role": "user", "content": self.make_text_query(text_query)}], response_format=FinancialAnalysis)
        #if completion.refusal:
        #    print(completion.refusal)
        #    exit()
        answer = completion.choices[0].message.parsed
        print(responses["business_overview"])
        print(completion.choices[0].message.parsed.business_overview, '\n')
        print("------------------------------------------------------------------")
        answer.business_overview = responses["business_overview"]
        risks_as_dict = [dict(r) for r in completion.choices[0].message.parsed.risks]
        for r in risks_as_dict:
            print(r, '\n')
        try:
            metrics = dict(completion.choices[0].message.parsed.metrics)
            print(metrics, '\n') s3 xz
        except TypeError:
            print("Metrics Missing")
        hist_as_dict = [dict(r) for r in completion.choices[0].message.parsed.historical_changes]
        for r in hist_as_dict:
            print(r, '\n')
        future_outlook_as_dict = [dict(r) for r in completion.choices[0].message.parsed.future_outlook]
        for r in future_outlook_as_dict:
            print(r, '\n')
        # print(dir(response))
        return completion.choices[0].message.parsed

    def get_summary(self, analysis: FinancialAnalysis) -> str:
        """Generate a human-readable summary from the analysis"""
        summary = f"""
Financial Analysis Summary

Business Overview:
{analysis.business_overview}

Key Risks:
{self._format_risks(analysis.risks)}

Financial Metrics:
{self._format_metrics(analysis.metrics)}

Historical Changes:
{self._format_changes(analysis.historical_changes)}

Future Outlook:
{self._format_outlook(analysis.future_outlook)}
"""
        return summary

    def _format_risks(self, risks: List[Risk]) -> str:
        return "\n".join([
            f"- {risk.category}: {risk.description} (Impact: {risk.potential_impact})"
            for risk in risks
        ])

    def _format_metrics(self, metrics: FinancialMetrics) -> str:
        formatted = []
        if metrics.revenue is not None:
            formatted.append(f"- Revenue: {metrics.revenue:,.2f}")
        if metrics.net_income is not None:
            formatted.append(f"- Net Income: {metrics.net_income:,.2f}")
        if metrics.operating_margin is not None:
            formatted.append(f"- Operating Margin: {metrics.operating_margin:.2f}%")
        if metrics.debt_to_equity is not None:
            formatted.append(f"- Debt to Equity: {metrics.debt_to_equity:.2f}")
        return "\n".join(formatted)

    def _format_changes(self, changes: List[HistoricalChange]) -> str:
        return "\n".join([
            f"- {change.category}: {change.description} (Impact: {change.impact})"
            for change in changes
        ])

    def _format_outlook(self, outlook: List[FutureOutlook]) -> str:
        return "\n".join([
            f"- {item.category} ({item.likelihood}): {item.description}"
            for item in outlook
        ])

class FileSearcher:
    def __init__(self, datafold_path, use_llamaindex=True):
        self.datafold_path = Path(datafold_path)
        self.all_tickers = Ticker.get_all_tickers_as_dataframe()
        self.use_llamaindex = use_llamaindex
        self.results_df = pd.DataFrame(columns=['Ticker', 'Year', 'Month', 'Response'])

    def load_tickers(self):
        # Get all tickers as dataframe
        self.all_tickers = Ticker.get_all_tickers_as_dataframe()

    def search_files_for_tickers(self, start_year = 2023):
        if self.all_tickers is None:
            raise ValueError("Tickers dataframe is not loaded. Call load_tickers() first.")

        # Iterate through each ticker
        for _, row in self.all_tickers.iterrows():
            ticker = row['Ticker']

            # Iterate through each folder in datafold_path
            for folder in self.datafold_path.iterdir():
                if folder.is_dir() and '-' in folder.name:  # Assuming folders are named as 'MM-YYYY'
                    # Extract month and year from folder name
                    month, year = folder.name.split('-')
                    if int(year) >= start_year:
                        # Construct expected filename
                        if not FinancialReport.objects.filter(ticker=ticker,year=year,month=month).exists():
                            file_name = f"Analisis_{ticker}_{folder.name}.pdf"
                            file_path = folder / file_name

                            # Check if the file exists
                            if file_path.exists():
                                print(f"File found: {file_path}")
                                response = self.parse_pdf(file_path)
                                if response:
                                    self.save_response(ticker, year, month, response)
                        else:
                            print(f"The {ticker} for year {year} and month {month} already exists in database, skipping.")
                        #else:
                        #    print(f"File not found: {file_name} in {folder}")

    def parse_pdf(self, file_path):
        retries = 3
        for attempt in range(retries):
                with fitz.open(file_path) as pdf_file:
                    text_content = ""
                    # Extract text from each page
                    for page_num in range(pdf_file.page_count):
                        page = pdf_file.load_page(page_num)
                        text_content += page.get_text("text") + "\n"

                    # Pre-process text for LLM
                    preprocessed_text = self.preprocess_text(text_content)
                    # Choose parsing method
                    if self.use_llamaindex:
                        analyzer = FinancialDocumentAnalyzer(api_key=get_api_key(G_root_dir / 'api_key'))

                        # Analyze document
                        analysis = analyzer.analyze_document(file_path)

                        if analysis:
                            return analysis
    def preprocess_text(self, text):
        # Remove extra whitespace and line breaks
        text = re.sub(r'\s+', ' ', text).strip()

        # Split into smaller chunks for LLM (e.g., 1000-character chunks)
        chunk_size = 3000
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

        # Convert to JSON structure
        structured_data = {"chunks": chunks}
        return json.dumps(structured_data, indent=2)

    def save_response(self, ticker, year, month, analysis):
        # Save the response to the CSV file for debugging
        try:
            metrics = dict(analysis.metrics)
        except TypeError:
            metrics = ["Missing"]
        financial_report, created = FinancialReport.objects.get_or_create(
            ticker=ticker,
            year=year,
            month=month,
            defaults={
                'business_overview': analysis.business_overview,
                'risks': [dict(r) for r in analysis.risks],
                'metrics':metrics ,
                'historical_changes': [dict(r) for r in analysis.historical_changes],
                'future_outlook': [dict(r) for r in analysis.future_outlook],
            }
        )
        financial_report.save()
        #self.results_df.to_csv(G_datafold / 'debug_responses.csv', index=False)
        return
    def _format_response_as_string(self, financial_analysis):
        def format_list(items: List[BaseModel], title: str) -> str:
            return f"\n{title}:\n" + "\n".join(f"- {item.to_json()}" for item in items)

        result = f"Business Overview:\n{financial_analysis.business_overview}\n"

        result += format_list(financial_analysis.risks, "Risks")
        result += f"\n\nMetrics:\n{financial_analysis.metrics.to_json()}\n"
        result += format_list(financial_analysis.historical_changes, "Historical Changes")
        result += format_list(financial_analysis.future_outlook, "Future Outlook")

        return result
    def query_llamaindex(self, preprocessed_text):
        # Use OpenAI's GPT model to query the document
        try:
            llm = OpenAI(model="gpt-4o-mini", api_key=get_api_key(G_root_dir))

            # Formulate the query
            messages = [
                ChatMessage(role="system", content="You are an expert financial document analyst. You give very detailed and long answers for each element and focus on finding unusual information."),
                ChatMessage(role="user", content=(
                    "Please parse the following document and determine the following: \n"
                    "1. Main Risks listed by the company. \n"
                    "2. Main business of the company. \n"
                    "3. Main key information. \n"
                    "4. Main key changes from last year. \n"
                    "5. Main key changes expected in the future. \n"
                    f"Document content: {preprocessed_text}"
                ))
            ]

            response = llm.chat(messages)
            return response
        except Exception as e:
            print(f"Failed to query LlamaIndex (OpenAI GPT-4): {e}")
            return None

    def query_ollama(self, preprocessed_text):
        # Use Ollama Llama3 to query the document
        try:
            llm = Ollama(model="llama3:latest", request_timeout=360.0)

            # Formulate the query
            messages = [
                ChatMessage(role="system", content="You are an expert financial document analyst."),
                ChatMessage(role="user", content=(
                    "Please parse the following document and determine the following: \n"
                    "1. Main Risks listed by the company. \n"
                    "2. Main business of the company. \n"
                    "3. Main key information. \n"
                    "4. Main key changes from last year. \n"
                    "5. Main key changes expected in the future. \n"
                    f"Document content: {preprocessed_text}"
                ))
            ]

            response = llm.chat(messages)
            return response
        except Exception as e:
            print(f"Failed to query Ollama (Llama3): {e}")
            return None
class Command(BaseCommand):
    help = 'Run the utility script'
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without actually performing the analysis'
        )
        parser.add_argument(
            '--do_all',
            action='store_true',
            help='Print what would be done without actually performing the analysis'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='analysis_results',
            help='Directory to store analysis results'
        )
        parser.add_argument(
            '--start-year',
            type=int,
            help='The year to start processing quarters from (e.g., 2022)'
        )
    def handle(self, *args, **kwargs):
        self.stdout.write('Running utility script...')
        #test_ticker()
        #suite = unittest.TestLoader().loadTestsFromTestCase(TestCmfScraping)

        # Run the test suite
        #unittest.TextTestRunner(verbosity=2).run(suite)
        searcher = FileSearcher(G_datafold, use_llamaindex=True)
        start_year = kwargs['start_year']
        print(start_year)
        if start_year:
            searcher.search_files_for_tickers(start_year = start_year)
        else:
            print("Specify start year with --start-year")
            return
        #searcher.search_files_for_tickers()
        # Optionally save the results to a CSV file
        output_file = G_datafold/"results.csv"
        searcher.results_df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")
        self.stdout.write(self.style.SUCCESS('Script ran successfully!'))

