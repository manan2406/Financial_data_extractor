import streamlit as st
import google.generativeai as genai
import pdfplumber
import io
import json
import re
from typing import Dict, Any
from functools import lru_cache
import logging
import pandas as pd
import altair as alt
import csv

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gemini API setup
API_KEY = "AIzaSyCTIICVF7EHWnNIcw30cxUDQZt9hDl13dQ"  # Replace with your actual API key
genai.configure(api_key=API_KEY)

class FinancialQueryExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    @lru_cache(maxsize=10)
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes with preprocessing."""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
                cleaned_text = "\n".join(pages_text).replace("SAVITHRI\n", "").replace("\n\n", "\n").strip()
                return cleaned_text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def query_gemini(self, text_content: str, user_prompt: str) -> str:
        """Query Gemini API with user-provided prompt."""
        try:
            model = genai.GenerativeModel(model_name="gemini-1.5-pro")
            full_prompt = f"""
            Using the provided financial document text, answer the user's query with exact values and their scale (e.g., Cr, Lakh, Thousand) directly from the text. Do not infer or estimate values. If the value is not explicitly stated, return "Not available in the document." Provide a concise answer (1-2 sentences max).

            User Query: {user_prompt}
            Document Text: {text_content}
            """
            response = model.generate_content(full_prompt)
            if response and hasattr(response, "candidates") and response.candidates:
                return "".join(part.text for part in response.candidates[0].content.parts).strip()
            return "Not available in the document."
        except Exception as e:
            logger.error(f"Error querying Gemini: {e}")
            return "Error processing query."

    def extract_structured_data(self, text_content: str, result_type: str = "consolidated") -> Dict[str, Any]:
        """Extract structured financial data."""
        prompt = f"""
        Extract financial metrics from the text for {result_type} results for the quarter ended 31 Dec'24. 
        Ensure exact numerical values with their scale (Cr, Lakh, Thousand). Include:
        - Revenue (Value of Sales & Services after GST, in Cr)
        - Operating Profit (Total Segment Profit before Interest Tax and Depreciation, in Cr)
        - Net Profit (Profit After Tax and Share of Profit/Loss of Associates and Joint Ventures, in Cr)
        - Sales (Gross Value of Sales and Services before Inter Segment Transfers, in Cr)
        - EPS (Earnings per Share, Basic, in ₹)
        - Segment-wise Revenue and EBIT for: Oil to Chemicals (O2C), Oil and Gas, Retail, Digital Services, Others
        - Ratios: Debt Equity Ratio, Net Profit Margin (%), Return on Equity (%)
        - Year-over-Year Growth for Net Profit (%)
        - Company Name and a 2-line summary

        Return in JSON:
        {{
          "Metrics": {{"Revenue": "value Cr", "Operating Profit": "value Cr", "Net Profit": "value Cr", "Sales": "value Cr", "EPS": "value", "YoY Net Profit Growth": "value %"}},
          "Segments": {{"Oil to Chemicals": {{"Revenue": "value Cr", "EBIT": "value Cr"}}, ...}},
          "Ratios": {{"Debt Equity Ratio": "value", "Net Profit Margin": "value %", "Return on Equity": "value %"}},
          "Company Name": "Company Name",
          "Summary": ["Line 1", "Line 2"]
        }}

        If a value is missing, use "N/A". Text: {text_content}
        """
        try:
            model = genai.GenerativeModel(model_name="gemini-1.5-pro")
            response = model.generate_content(prompt)
            if response and hasattr(response, "candidates") and response.candidates:
                raw_text = "".join(part.text for part in response.candidates[0].content.parts)
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            return {}
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {}

    def save_to_csv(self, data: Dict[str, Any]) -> str:
        """Generate CSV content as a string."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Financial Metrics"])
        writer.writerow(["Metric", "Value"])
        for key, value in data.get("Metrics", {}).items():
            writer.writerow([key, value])

        writer.writerow([])
        writer.writerow(["Segment Information"])
        writer.writerow(["Segment", "Revenue", "EBIT"])
        for segment, values in data.get("Segments", {}).items():
            writer.writerow([segment, values.get("Revenue", "N/A"), values.get("EBIT", "N/A")])

        writer.writerow([])
        writer.writerow(["Financial Ratios"])
        writer.writerow(["Ratio", "Value"])
        for key, value in data.get("Ratios", {}).items():
            writer.writerow([key, value])

        writer.writerow([])
        writer.writerow(["Company Name", data.get("Company Name", "N/A")])
        summary = data.get("Summary", ["N/A", "N/A"])
        writer.writerow(["Summary", summary[0]])
        writer.writerow(["", summary[1]])

        return output.getvalue()

# Streamlit Dashboard
def main():
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("Financial Report Dashboard")
    with col2:
        st.write("")  # Spacer for alignment
        if "detailed_data" in st.session_state:
            csv_data = st.session_state["extractor"].save_to_csv(st.session_state["detailed_data"])
            st.download_button(
                label="Download Report",
                data=csv_data,
                file_name="xyz_financial_report.csv",
                mime="text/csv"
            )

    # File uploader
    uploaded_file = st.file_uploader("Choose a Financial PDF", type="pdf")
    
    if uploaded_file:
        # Initialize session state for extractor and data
        if "extractor" not in st.session_state:
            st.session_state["extractor"] = FinancialQueryExtractor()
        extractor = st.session_state["extractor"]

        pdf_bytes = uploaded_file.read()
        text_content = extractor.extract_text_from_pdf(pdf_bytes)

        if not text_content.strip():
            st.error("No text extracted from PDF.")
            return

        # Result type selection
        result_type = st.selectbox("Select Result Type", ["Consolidated", "Standalone"], index=0)

        # Extract structured data
        with st.spinner("Extracting financial data..."):
            detailed_data = extractor.extract_structured_data(text_content, result_type.lower())
            st.session_state["detailed_data"] = detailed_data

        if not detailed_data:
            st.error("Failed to extract data.")
            return

        # Metrics Grid
        st.subheader("Key Financial Metrics")
        metrics = detailed_data.get("Metrics", {})
        ratios = detailed_data.get("Ratios", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Revenue/Sales", metrics.get("Sales", "N/A"))
            st.metric("Year over Year Growth", metrics.get("YoY Net Profit Growth", "N/A"))
        with col2:
            st.metric("Net Profit", metrics.get("Net Profit", "N/A"))
            st.metric("EPS", metrics.get("EPS", "N/A"))
        with col3:
            st.metric("Operating Profit", metrics.get("Operating Profit", "N/A"))
            st.metric("Return on Equity", ratios.get("Return on Equity", "N/A"))

        # Summary Section
        st.subheader("Summary")
        st.write(f"**Company Name:** {detailed_data.get('Company Name', 'xyz Ltd.')}")
        st.write(f"**Quarter:** Q3 FY24")
        st.write("**Key Insights:**")
        st.write(f"- The total Revenue for the quarter is {metrics.get('Revenue', 'N/A')}, showing a Revenue Growth of {metrics.get('YoY Net Profit Growth', 'N/A')} from the last quarter.")
        st.write(f"- The company's Earnings Per Share (EPS) is ₹{metrics.get('EPS', 'N/A')}, reflecting stable shareholder earnings.")
        st.write(f"- The YoY Net Profit Growth is {metrics.get('YoY Net Profit Growth', 'N/A')}, suggesting a positive long-term outlook.")
        st.write(f"- The Return on Equity (ROE) is {ratios.get('Return on Equity', 'N/A')}, indicating strong returns for investors.")
        st.write("**Overall Financial Status:** Healthy Performance with Growth in Profitability.")

        # Visualizations
        st.subheader("Visual Insights")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Stacked Bar Chart: Revenue vs. Operating Profit vs. Net Profit**")
            # Mock data for visualization (replace with actual segment data if available)
            data = pd.DataFrame({
                "Region": ["North", "East", "West"],
                "Revenue": [100, 120, 80],
                "Operating Profit": [30, 40, 25],
                "Net Profit": [20, 25, 15]
            })
            data_melted = data.melt(id_vars="Region", var_name="Metric", value_name="Value")
            chart = alt.Chart(data_melted).mark_bar().encode(
                x="Region",
                y="Value",
                color="Metric",
                tooltip=["Region", "Metric", "Value"]
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)

        with col2:
            st.write("**Multi-line Trend Chart: Revenue, Profit Over Time**")
            # Mock data for trend (replace with actual time-series data if available)
            trend_data = pd.DataFrame({
                "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                "Revenue": [20, 22, 25, 28, 30, 32, 35, 38, 40, 42, 45, 48],
                "Profit": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
            })
            trend_melted = trend_data.melt(id_vars="Month", var_name="Metric", value_name="Value")
            trend_chart = alt.Chart(trend_melted).mark_line().encode(
                x="Month",
                y="Value",
                color="Metric",
                tooltip=["Month", "Metric", "Value"]
            ).properties(height=300)
            st.altair_chart(trend_chart, use_container_width=True)

        # Prompt Window
        st.subheader("Ask a Question")
        user_prompt = st.text_input(
            "Enter your query (e.g., 'Sales for the third quarter')",
            value="",
            placeholder="Type your question here..."
        )

        if user_prompt:
            with st.spinner("Processing your query..."):
                answer = extractor.query_gemini(text_content, user_prompt)
            st.write("**Answer:**")
            st.write(answer)

if __name__ == "__main__":
    main()