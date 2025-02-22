import streamlit as st
import yfinance as yf
import requests
import matplotlib.pyplot as plt
import datetime
import numpy as np

# Alpha Vantage API Key
API_KEY = "NM94KM6O8CUADMP9"  # Replace with your actual API key

# Function to fetch EPS data
def get_eps_data(ticker):
    url = f"https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "annualEarnings" not in data:
            return None, None

        eps_data = []
        earliest_eps_date = None

        for item in data["annualEarnings"]:
            try:
                date = item["fiscalDateEnding"]
                eps = float(item["reportedEPS"])
                eps_data.append((date, eps))

                if earliest_eps_date is None or date < earliest_eps_date:
                    earliest_eps_date = date
            except ValueError:
                continue  # Skip invalid entries
        
        return eps_data, earliest_eps_date
    except Exception as e:
        st.error(f"Error fetching EPS data: {e}")
        return None, None

# Function to fetch Operating Cash Flow (OCF) data
def get_ocf_data(ticker):
    url = f"https://www.alphavantage.co/query?function=CASH_FLOW&symbol={ticker}&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "annualReports" not in data:
            return None, None

        ocf_data = []
        earliest_ocf_date = None

        for item in data["annualReports"]:
            try:
                date = item["fiscalDateEnding"]
                ocf = float(item["operatingCashflow"])  
                ocf_data.append((date, ocf))

                if earliest_ocf_date is None or date < earliest_ocf_date:
                    earliest_ocf_date = date
            except (ValueError, KeyError, TypeError):
                continue  # Skip invalid entries
        
        return ocf_data, earliest_ocf_date
    except Exception as e:
        st.error(f"Error fetching Operating Cash Flow data: {e}")
        return None, None

# Function to fetch Shares Outstanding
def get_shares_outstanding(ticker):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "SharesOutstanding" not in data:
            return None

        return float(data["SharesOutstanding"])
    except Exception as e:
        st.error(f"Error fetching Shares Outstanding: {e}")
        return None

# Function to fetch historical stock prices
def get_stock_data(ticker, start_date):
    stock = yf.Ticker(ticker)
    
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = "2000-01-01"

    history = stock.history(start=start_date, period="max")
    history.index = history.index.tz_localize(None)  
    return history

# Streamlit UI
st.title("📈 Stock Price & Valuation Dashboard")

ticker = st.text_input("Enter a Stock Ticker (e.g., AAPL, TSLA, IREN)", "AAPL").upper()
valuation_method = st.selectbox("Select Valuation Method:", ["Earnings", "Operating Cash Flow"])
multiple = st.number_input("Enter Multiple (e.g., 10, 15, 20)", min_value=1, value=15, step=1)

if st.button("Generate Chart"):
    # Determine which data to use
    if valuation_method == "Earnings":
        financial_data, earliest_date = get_eps_data(ticker)
        label = "EPS"
    else:
        ocf_data, earliest_ocf_date = get_ocf_data(ticker)
        shares_outstanding = get_shares_outstanding(ticker)

        if not shares_outstanding:
            st.warning("Could not retrieve Shares Outstanding data.")
            financial_data, earliest_date = None, None
        elif ocf_data:
            financial_data = [(date, ocf / shares_outstanding) for date, ocf in ocf_data]
            earliest_date = earliest_ocf_date
            label = "Operating Cash Flow Per Share"
        else:
            financial_data, earliest_date = None, None

    # Handle missing data
    if not financial_data:
        st.warning(f"Could not retrieve {valuation_method} data. Proceeding with stock prices only.")
        earliest_date = None

    # Fetch stock price data
    stock_data = get_stock_data(ticker, earliest_date)

    if stock_data is None or stock_data.empty:
        st.error("Stock data not found. Please enter a valid ticker.")
    else:
        # ---- Valuation Chart ----
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(stock_data.index, stock_data["Close"], label="Stock Price", color="blue")
        ax.set_yscale("log")

        if financial_data:
            dates, values = zip(*[(datetime.datetime.strptime(d, "%Y-%m-%d"), v * multiple) for d, v in financial_data])
            ax.plot(dates, values, label=f"{label} x {multiple} (Fair Value)", color="red", linestyle="dashed")

        ax.set_title(f"{ticker} Stock Price vs {label} Fair Value (Log Scale)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price ($) - Log Scale")
        ax.legend()
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        st.pyplot(fig)
