import streamlit as st
import yfinance as yf
import math
from scipy.stats import norm
import pandas as pd

# Binomial model for American options (with early exercise)
def binomial_tree(S, K, T, r, sigma, n, option_type="call"):
    dt = T / n  # Time step
    u = math.exp(sigma * math.sqrt(dt))  # Up factor
    d = 1 / u  # Down factor
    p = (math.exp(r * dt) - d) / (u - d)  # Probability of up movement

    # Step 1: Calculate possible stock prices at expiration
    stock_prices = [S * (u ** j) * (d ** (n - j)) for j in range(n + 1)]
    
    # Step 2: Calculate option values at expiration
    if option_type == "call":
        option_values = [max(price - K, 0) for price in stock_prices]
    else:
        option_values = [max(K - price, 0) for price in stock_prices]

    # Step 3: Work backward through the tree and check for early exercise
    for i in range(n - 1, -1, -1):
        for j in range(i + 1):
            stock_price = S * (u ** j) * (d ** (i - j))
            option_values[j] = max(
                math.exp(-r * dt) * (p * option_values[j + 1] + (1 - p) * option_values[j]),
                (stock_price - K if option_type == "call" else K - stock_price)  # Early exercise condition
            )

    return option_values[0]

# Greeks Calculation using Finite Differences
def calculate_greeks(S, K, T, r, sigma, n, option_type="call"):
    epsilon = 0.01  # Small value for calculating finite differences

    # Delta calculation (no change needed)
    S_up = S * 1.01
    S_down = S * 0.99
    V_up = binomial_tree(S_up, K, T, r, sigma, n, option_type)
    V_down = binomial_tree(S_down, K, T, r, sigma, n, option_type)
    delta = (V_up - V_down) / (S_up - S_down)

    # Gamma calculation (no change needed)
    delta_up = (binomial_tree(S_up * 1.01, K, T, r, sigma, n, option_type) - V_up) / (S_up * 1.01 - S_up)
    delta_down = (V_down - binomial_tree(S_down * 0.99, K, T, r, sigma, n, option_type)) / (S_down - S_down * 0.99)
    gamma = (delta_up - delta_down) / (S_up - S_down)

    # Vega calculation (adjust to daily)
    V_vol_up = binomial_tree(S, K, T, r, sigma + epsilon, n, option_type)
    V_vol_down = binomial_tree(S, K, T, r, sigma - epsilon, n, option_type)
    vega = (V_vol_up - V_vol_down) / (2 * epsilon) / 100

    # Theta calculation (adjust to daily)
    dt = 1/365  # One day
    V_current = binomial_tree(S, K, T, r, sigma, n, option_type)
    V_T_down = binomial_tree(S, K, T - dt, r, sigma, n, option_type)
    theta = (V_T_down - V_current) / dt
    theta = theta / 365  # Convert yearly theta to daily theta

    # Rho calculation (adjust to daily)
    V_r_up = binomial_tree(S, K, T, r + epsilon, sigma, n, option_type)
    V_r_down = binomial_tree(S, K, T, r - epsilon, sigma, n, option_type)
    rho = (V_r_up - V_r_down) / (2 * epsilon) / 100

    return delta, gamma, vega, theta, rho

# Streamlit UI
st.title("Options Pricing Calculator")

# Ticker input from the user
ticker = st.text_input("Enter Stock Ticker (e.g., AAPL)")

# Fetching stock data using yfinance
if ticker:
    stock = yf.Ticker(ticker)
    stock_info = stock.history(period="1d")
    
    # Get the current stock price
    if not stock_info.empty:
        current_price = stock_info['Close'].iloc[-1]
        st.write(f"Current Stock Price for {ticker}: {current_price:.2f}")
    else:
        st.write(f"Unable to fetch data for {ticker}. Please check the ticker symbol.")
        current_price = None

# Let the user input other values
K = st.number_input("Strike Price (K)", min_value=0.0, value=235.0, step=1.0)
days_to_expiration = st.number_input("Days to Expiration", min_value=1, value=22)
T = days_to_expiration / 365.0  # Convert days to years
r = st.number_input("Risk-free Interest Rate (r)", min_value=0.0, value=0.0372, step=0.0001, format="%.4f")
sigma = st.number_input("Volatility (sigma)", min_value=0.0, value=0.2714, step=0.0001, format="%.4f")

# Calculate number of steps based on days to expiration
n = max(days_to_expiration, 100)  # Ensure at least 100 steps for short-term options

option_type = st.selectbox("Option Type", ["Call", "Put"])

# Calculation button
if st.button("Calculate") and current_price is not None:
    price = binomial_tree(current_price, K, T, r, sigma, n, option_type.lower())
    st.write(f"Option Price: ${price:.2f}")

    # Calculate and display the Greeks
    delta, gamma, vega, theta, rho = calculate_greeks(current_price, K, T, r, sigma, n, option_type.lower())

    # Creating a dataframe for the Greeks
    greeks_df = pd.DataFrame({
        'Greek': ['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'],
        'Value': [delta, gamma, vega, theta, rho]
    })

    # Display the Greeks in a table format
    st.subheader("Option Greeks")
    st.table(greeks_df)