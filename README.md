# Financial Report Dashboard

A Python-based web application built with Streamlit to extract, analyze, and visualize financial data from PDF reports. This tool leverages the Google Gemini API for natural language processing and structured data extraction, enabling users to upload financial PDFs, view key metrics, and ask custom queries about the document.

## Features

- **PDF Upload & Text Extraction**: Upload financial PDFs and extract text using `pdfplumber` with preprocessing to clean the data.
- **Structured Data Extraction**: Automatically extracts key financial metrics, segment-wise data, ratios, and a summary in JSON format for the quarter ended 31 Dec'24.
- **Custom Queries**: Ask specific questions about the financial data (e.g., "What is the sales figure for Q3?") and get concise, exact answers.
- **Interactive Dashboard**: Displays key financial metrics, a summary, and visualizations (stacked bar and multi-line charts) using Altair.
- **CSV Export**: Download extracted financial data as a CSV file.
- **Logging**: Includes error logging for debugging and monitoring.

## Technologies Used

- **Python 3.8+**
- **Streamlit**: For the interactive web interface.
- **Google Gemini API**: For text analysis and structured data extraction.
- **pdfplumber**: For extracting text from PDFs.
- **Pandas & Altair**: For data manipulation and visualization.
- **Other Libraries**: `json`, `re`, `csv`, `functools` (for caching), `logging`.

## Prerequisites

Before running the application, ensure you have:

1. **Python 3.8+** installed.
2. A **Google Gemini API Key**. Replace the placeholder `API_KEY` in the code with your actual key.
3. A financial PDF report to upload (e.g., quarterly earnings report).