import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import datetime
from alpha_vantage.fundamentaldata import FundamentalData

# Alpha Vantage API Key
API_KEY = "NM94KM6O8CUADMP9"  # Replace this with your API key

# Function to fetch historical stock prices
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    history = stock.history(period="5y")  # Get 5 years of data
    return history

# Function to fetch EPS data from Alpha Vantage
def get_eps_data(ticker):
    fd = FundamentalData(API_KEY, output_format="json")

    try:
        data, _ = fd.get_earnings(ticker)  # Fetch earnings data
        eps_data = []

        for q in data['quarterlyEarnings']:
            try:
                date = q['fiscalDateEnding']
                eps = float(q['reportedEPS']) * 15  # Multiply EPS by 15
                eps_data.append((date, eps))
            except ValueError:
                continue  # Skip invalid data

        return eps_data
    except Exception as e:
        st.error(f"Error fetching EPS data: {e}")
        return None

# Streamlit UI
st.title("📈 Stock Price & EPS-Based Valuation Dashboard")

ticker = st.text_input("Enter a Stock Ticker (e.g., AAPL, TSLA, IREN)", "AAPL").upper()

if st.button("Generate Chart"):
    # Fetch stock price data
    stock_data = get_stock_data(ticker)

    if stock_data is None or stock_data.empty:
        st.error("Stock data not found. Please enter a valid ticker.")
    else:
        # Fetch EPS data
        eps_data = get_eps_data(ticker)

        if not eps_data:
            st.warning("Could not retrieve EPS data. Proceeding with stock prices only.")

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
