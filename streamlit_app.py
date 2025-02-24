import streamlit as st
import yfinance as yf
import requests
import matplotlib.pyplot as plt
import datetime
import numpy as np
import plotly.graph_objects as go

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
                continue
        
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
                continue 
        
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

# Function to calculate historical average multiples
def calculate_average_multiple(financial_data, stock_data):
    pe_ratios = []

    for date, value in financial_data:
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        
        closest_date = min(stock_data.index, key=lambda d: abs(d - date_obj))
        stock_price = stock_data.loc[closest_date]["Close"]

        if value > 0:
            pe_ratios.append(stock_price / value)

    if len(pe_ratios) > 1:
        return np.mean(pe_ratios[:-1])  # Exclude the most recent data point
    return None

# Streamlit UI
st.title("📈 Stock Price & Valuation Dashboard")

ticker = st.text_input("Enter a Stock Ticker (e.g., AAPL, TSLA, IREN)", "AAPL").upper()
valuation_method = st.selectbox("Select Valuation Method:", ["Earnings", "Operating Cash Flow"])

if st.button("Fetch Data"):
    # Fetch selected financial data
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

    # Fetch stock price data
    stock_data = get_stock_data(ticker, earliest_date)

    if financial_data and stock_data is not None and not stock_data.empty:
        avg_multiple = calculate_average_multiple(financial_data, stock_data)
        if avg_multiple:
            multiple = st.number_input("Enter Multiple", min_value=1, value=int(avg_multiple), step=1)
        else:
            multiple = st.number_input("Enter Multiple", min_value=1, value=15, step=1)

        # Interactive date range selector
        date_range = st.slider("Select Date Range:", min_value=stock_data.index[0].date(), 
                               max_value=stock_data.index[-1].date(), 
                               value=(stock_data.index[0].date(), stock_data.index[-1].date()))

        # Filter stock data for selected range
        filtered_stock_data = stock_data.loc[str(date_range[0]):str(date_range[1])]

        # Create interactive chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_stock_data.index, y=filtered_stock_data["Close"], 
                                 mode='lines', name="Stock Price", line=dict(color="blue")))

        # Calculate and plot fair value line
        if financial_data:
            dates, values = zip(*[(datetime.datetime.strptime(d, "%Y-%m-%d"), v * multiple) for d, v in financial_data])
            fair_value_dates = [d for d in dates if d >= date_range[0] and d <= date_range[1]]
            fair_values = [values[i] for i in range(len(dates)) if dates[i] >= date_range[0] and dates[i] <= date_range[1]]

            fig.add_trace(go.Scatter(x=fair_value_dates, y=fair_values, 
                                     mode='lines', name=f"{label} x {multiple} (Fair Value)", 
                                     line=dict(color="red", dash="dash")))

        fig.update_layout(title=f"{ticker} Stock Price vs {label} Fair Value",
                          xaxis_title="Date", yaxis_title="Price ($)", yaxis_type="log",
                          hovermode="x unified")

        st.plotly_chart(fig)

        # CAGR calculation section
        st.subheader("📊 CAGR Calculator")
        start_date = st.date_input("Select Start Date:", min_value=stock_data.index[0].date(), 
                                   max_value=stock_data.index[-1].date(), value=stock_data.index[0].date())
        end_date = st.date_input("Select End Date:", min_value=start_date, max_value=stock_data.index[-1].date(),
                                 value=stock_data.index[-1].date())

        start_price = stock_data.loc[str(start_date)]["Close"]
        end_price = stock_data.loc[str(end_date)]["Close"]
        years = (end_date - start_date).days / 365.25
        cagr = ((end_price / start_price) ** (1 / years) - 1) * 100

        st.write(f"CAGR from {start_date} to {end_date}: **{cagr:.2f}%**")
