import streamlit as st
import yfinance as yf
import requests
import matplotlib.pyplot as plt
import datetime

# Alpha Vantage API Key
API_KEY = "NM94KM6O8CUADMP9"  # Replace with your actual API key

# Function to fetch EPS data from Alpha Vantage API directly
def get_eps_data(ticker):
    url = f"https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        # Ensure response has earnings data
        if "annualEarnings" not in data:
            return None, None

        eps_data = []
        earliest_eps_date = None
        
        # Extract EPS from "annualEarnings"
        for item in data["annualEarnings"]:
            try:
                date = item["fiscalDateEnding"]
                eps = float(item["reportedEPS"]) * 15  # Multiply EPS by 15 for fair value estimate
                eps_data.append((date, eps))

                # Track earliest EPS date
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
    
    # Convert start_date from string to datetime object
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = "2000-01-01"  # Default if no EPS data is available

    history = stock.history(start=start_date, period="max")  # Fetch stock data from earliest EPS date
    return history

# Streamlit UI
st.title("📈 Stock Price & EPS-Based Valuation Dashboard")

ticker = st.text_input("Enter a Stock Ticker (e.g., AAPL, TSLA, IREN)", "AAPL").upper()

if st.button("Generate Chart"):
    # Fetch EPS data first (to get the earliest EPS date)
    eps_data, earliest_eps_date = get_eps_data(ticker)

    if not eps_data:
        st.warning("Could not retrieve EPS data. Proceeding with stock prices only.")
        earliest_eps_date = None  # No restriction on stock data

    # Fetch stock price data (limited to the earliest EPS date)
    stock_data = get_stock_data(ticker, earliest_eps_date)

    if stock_data is None or stock_data.empty:
        st.error("Stock data not found. Please enter a valid ticker.")
    else:
        # Plot data
        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot stock price
        ax.plot(stock_data.index, stock_data["Close"], label="Stock Price", color="blue")

        # Plot EPS estimates if available
        if eps_data:
            eps_dates, eps_values = zip(*[(datetime.datetime.strptime(d, "%Y-%m-%d"), v) for d, v in eps_data])
            ax.plot(eps_dates, eps_values, label="EPS x 15 (Fair Value)", color="red", linestyle="dashed")

        ax.set_title(f"{ticker} Stock Price vs EPS Fair Value")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price ($)")
        ax.legend()
        ax.grid()

        st.pyplot(fig)
