import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import datetime

# Function to fetch historical stock prices
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    history = stock.history(period="5y")  # Get 5 years of data
    return history

# Function to scrape EPS data from Nasdaq
def get_eps_data(ticker):
    url = f"https://www.nasdaq.com/market-activity/stocks/{ticker}/earnings"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "lxml")

    # Extract historical and estimated EPS values
    eps_data = []
    rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            try:
                date = cols[0].text.strip()
                eps = float(cols[1].text.strip())  # Convert EPS to float
                eps_data.append((date, eps * 15))  # Multiply EPS by 15
            except:
                continue

    return eps_data

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
            eps_dates, eps_values = zip(*[(datetime.datetime.strptime(d, "%m/%d/%Y"), v) for d, v in eps_data])
            ax.plot(eps_dates, eps_values, label="EPS x 15 (Fair Value)", color="red", linestyle="dashed")

        ax.set_title(f"{ticker} Stock Price vs EPS Fair Value")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price ($)")
        ax.legend()
        ax.grid()

        st.pyplot(fig)
