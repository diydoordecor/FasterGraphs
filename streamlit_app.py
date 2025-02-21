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

# Function to fetch historical stock prices, aligned with EPS data
def get_stock_data(ticker, start_date):
    stock = yf.Ticker(ticker)
    
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = "2000-01-01"  # Default if no financial data is available

    history = stock.history(start=start_date, period="max")
    history.index = history.index.tz_localize(None)  # Convert timezone-aware index to naive
    return history

# Function to calculate average P/E ratios over different timeframes
def calculate_pe_averages(eps_data, stock_data):
    if not eps_data or stock_data.empty:
        return None

    eps_data.sort(reverse=True, key=lambda x: x[0])  # Sort by date descending
    today = datetime.datetime.today()

    pe_ratios = []

    for date, eps in eps_data:
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=None)  # Ensure EPS date is timezone-naive
        
        # Find closest stock price for that EPS date
        closest_date = min(stock_data.index, key=lambda d: abs(d.to_pydatetime().replace(tzinfo=None) - date_obj))
        stock_price = stock_data.loc[closest_date]["Close"]

        if eps > 0:  # Avoid division by zero
            pe_ratios.append((date, stock_price / eps))

    pe_full = [v for _, v in pe_ratios]
    pe_10yr = [v for d, v in pe_ratios if (today - datetime.datetime.strptime(d, "%Y-%m-%d")).days <= 3650]
    pe_5yr = [v for d, v in pe_ratios if (today - datetime.datetime.strptime(d, "%Y-%m-%d")).days <= 1825]
    pe_3yr = [v for d, v in pe_ratios if (today - datetime.datetime.strptime(d, "%Y-%m-%d")).days <= 1095]

    return {
        "Full timeframe": np.mean(pe_full) if pe_full else None,
        "Last 10 years": np.mean(pe_10yr) if pe_10yr else None,
        "Last 5 years": np.mean(pe_5yr) if pe_5yr else None,
        "Last 3 years": np.mean(pe_3yr) if pe_3yr else None
    }

# Streamlit UI
st.title("📈 Stock Price & EPS-Based Valuation Dashboard (Log Scale)")

ticker = st.text_input("Enter a Stock Ticker (e.g., AAPL, TSLA, IREN)", "AAPL").upper()
multiple = st.number_input("Enter EPS Multiple (e.g., 15, 20, 25)", min_value=1, value=15, step=1)

if st.button("Generate Chart"):
    # Fetch EPS data
    eps_data, earliest_eps_date = get_eps_data(ticker)

    if not eps_data:
        st.warning("Could not retrieve EPS data. Proceeding with stock prices only.")
        earliest_eps_date = None  # No restriction on stock data

    # Fetch stock price data (limited to the earliest EPS date)
    stock_data = get_stock_data(ticker, earliest_eps_date)

    if stock_data is None or stock_data.empty:
        st.error("Stock data not found. Please enter a valid ticker.")
    else:
        # ---- EPS-Based Valuation Chart ----
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(stock_data.index, stock_data["Close"], label="Stock Price", color="blue")
        ax1.set_yscale("log")

        if eps_data:
            eps_dates, eps_values = zip(*[(datetime.datetime.strptime(d, "%Y-%m-%d"), v * multiple) for d, v in eps_data])
            ax1.plot(eps_dates, eps_values, label=f"EPS x {multiple} (Fair Value)", color="red", linestyle="dashed")

        ax1.set_title(f"{ticker} Stock Price vs EPS Fair Value (Log Scale)")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Price ($) - Log Scale")
        ax1.legend()
        ax1.grid(True, which="both", linestyle="--", linewidth=0.5)

        st.pyplot(fig)

        # ---- Display Average P/E Ratios ----
        pe_averages = calculate_pe_averages(eps_data, stock_data)
        if pe_averages:
            st.subheader("📊 Average Annual P/E Ratios")
            st.write(f"**Full timeframe:** {pe_averages['Full timeframe']:.2f}")
            st.write(f"**Last 10 years:** {pe_averages['Last 10 years']:.2f}")
            st.write(f"**Last 5 years:** {pe_averages['Last 5 years']:.2f}")
            st.write(f"**Last 3 years:** {pe_averages['Last 3 years']:.2f}")
