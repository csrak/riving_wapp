# Riving WebApp

**Riving WebApp** is the Django web implementation of **Riving Tools**, offering streamlined access and visualization of financial data.

## Production Version

You can view the production version here:  
[**Riving WebApp - Production**](https://rivingwapp-production.up.railway.app/)

---

## Features

- **Stock Screener**  
- **Financial Quarterly Data Plots**  
- **GenAI (LLM) Summaries**  
  - Summarizes extended quarterly reports: Risks, Outlook, Changes, etc.  
- **Last Day Movers and Price Charts**  
  *(Note: Price charts are not always updated to conserve resources during testing)*  

---

## About

The main idea behind Riving WebApp is to provide **easy-to-use access** and **visualizations** of the data aggregated by Riving Tools. 

Riving tools scraps data from official sources in the Chilean market, but that are often wrongly interpreted or missing data in some of the biggest financial data aggregators duch as Bloomberg.

Most tools are being integrated into the web app, enabling:  
- **Self-updating databases**  
- **Standalone functionality**  

---

## Databases Utilized

### 1. Financial Data
- Scraped and processed from **Chilean CMF XBRL files**.  
- Follows **IFRS accounting standards**.

### 2. Quarterly Detailed Reports
- Text-based reports sourced from the **CMF**.

### 3. Dividend Data
- Scraped from **CMF** sources.

### 4. Price Data
- Ready for API usage.  
- Currently tested using the **Yahoo Finance API** (free tier).

---

## Future Scope

- **Integration of all Riving Tools features** into the web app.  
- **Standalone operation** with automatic database updates.  

---

## Development

For contributions, suggestions, or bug reports, feel free to open an issue or submit a pull request.  
Stay tuned for updates as the project evolves!  
