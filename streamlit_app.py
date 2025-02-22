import streamlit as st
import yfinance as yf
import requests
import matplotlib.pyplot as plt
import datetime
import numpy as np

# Alpha Vantage API Key
API_KEY = "NM94KM6O8CUADMP9"  # Replace with your actual API key

# Function to fetch EPS data from Alpha Vantage API
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
                ocf = float(item["operatingCashflow"])  # Extract Operating Cash Flow
                ocf_data.append((date, ocf))

                if earliest_ocf_date is None or date < earliest_ocf_date:
                    earliest_ocf_date = date
            except (ValueError, KeyError, TypeError):
                continue  # Skip invalid entries
        
        return ocf_data, earliest_ocf_date
    except Exception as e:
        st.error(f"Error fetching Operating Cash Flow data: {e}")
        return None, None

# Function to fetch Shares Outstanding from the Company Overview API
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

# Function to fetch historical stock prices, aligned with financial data
def get_stock_data(ticker, start_date):
    stock = yf.Ticker(ticker)
    
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = "2000-01-01"  # Default if no financial data is available

    history = stock.history(start=start_date, period="max")
    history.index = history.index.tz_localize(None)  # Convert timezone-aware index to naive
    return history

# Streamlit UI
st.title("📈 Stock Price & Fundamental-Based Valuation Dashboard (Log Scale)")

ticker = st.text_input("Enter a Stock Ticker (e.g., AAPL, TSLA, IREN)", "AAPL").upper()
multiple_eps = st.number_input("Enter EPS Multiple (e.g., 15, 20, 25)", min_value=1, value=15, step=1)
multiple_ocfps = st.number_input("Enter OCFPS Multiple (e.g., 10, 15, 20)", min_value=1, value=10, step=1)

if st.button("Generate Chart"):
    # Fetch EPS data
    eps_data, earliest_eps_date = get_eps_data(ticker)

    if not eps_data:
        st.warning("Could not retrieve EPS data. Proceeding with stock prices only.")
        earliest_eps_date = None  # No restriction on stock data

    # Fetch Operating Cash Flow data
    ocf_data, earliest_ocf_date = get_ocf_data(ticker)

    if not ocf_data:
        st.warning("Could not retrieve Operating Cash Flow data.")
        earliest_ocf_date = None  # No restriction on stock data

    # Fetch Shares Outstanding
    shares_outstanding = get_shares_outstanding(ticker)

    if not shares_outstanding:
        st.warning("Could not retrieve Shares Outstanding data.")

    # Calculate OCFPS (Operating Cash Flow Per Share)
    ocfps_data = [(date, ocf / shares_outstanding) for date, ocf in ocf_data if shares_outstanding]

    # Determine earliest available financial data
    earliest_date = min(filter(None, [earliest_eps_date, earliest_ocf_date]))

    # Fetch stock price data (limited to the earliest financial data date)
    stock_data = get_stock_data(ticker, earliest_date)

    if stock_data is None or stock_data.empty:
        st.error("Stock data not found. Please enter a valid ticker.")
    else:
        # ---- EPS-Based Valuation Chart ----
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(stock_data.index, stock_data["Close"], label="Stock Price", color="blue")
        ax1.set_yscale("log")

        if eps_data:
            eps_dates, eps_values = zip(*[(datetime.datetime.strptime(d, "%Y-%m-%d"), v * multiple_eps) for d, v in eps_data])
            ax1.plot(eps_dates, eps_values, label=f"EPS x {multiple_eps} (Fair Value)", color="red", linestyle="dashed")

        ax1.set_title(f"{ticker} Stock Price vs EPS Fair Value (Log Scale)")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Price ($) - Log Scale")
        ax1.legend()
        ax1.grid(True, which="both", linestyle="--", linewidth=0.5)

        st.pyplot(fig)

        # ---- OCFPS-Based Valuation Chart ----
        fig, ax2 = plt.subplots(figsize=(10, 6))
        ax2.plot(stock_data.index, stock_data["Close"], label="Stock Price", color="blue")
        ax2.set_yscale("log")

        if ocfps_data:
            ocfps_dates, ocfps_values = zip(*[(datetime.datetime.strptime(d, "%Y-%m-%d"), v * multiple_ocfps) for d, v in ocfps_data])
            ax2.plot(ocfps_dates, ocfps_values, label=f"OCFPS x {multiple_ocfps} (Fair Value)", color="green", linestyle="dashed")

        ax2.set_title(f"{ticker} Stock Price vs OCFPS Fair Value (Log Scale)")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Price ($) - Log Scale")
        ax2.legend()
        ax2.grid(True, which="both", linestyle="--", linewidth=0.5)

        st.pyplot(fig)
