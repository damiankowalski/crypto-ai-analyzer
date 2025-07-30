import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# 🔑 Wpisz tu swój klucz API z CoinMarketCap
CMC_API_KEY = "4f9d6276-feee-4925-aaa6-cc6d68701e12"

def get_spot_volume():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical"
    parameters = {
        "symbol": "BTC",
        "convert": "USD",
        "interval": "daily",
        "count": 30,
    }
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    response = requests.get(url, headers=headers, params=parameters)

    if response.status_code != 200:
        raise Exception(f"Błąd API: {response.status_code} – {response.text}")

    data = response.json()
    if "data" not in data:
        raise Exception("Brak pola 'data' w odpowiedzi API")

    df = pd.DataFrame([{
        "date": entry["timestamp"][:10],
        "volume": entry["quote"]["USD"]["volume_24h"]
    } for entry in data["data"]["quotes"]])

    df["date"] = pd.to_datetime(df["date"])
    return df

# 🌐 Interfejs
st.set_page_config(page_title="Bitcoin ETF Dashboard", layout="wide")
st.title("📊 Bitcoin ETF Dashboard z danymi na żywo")

with st.expander("📈 Realny wolumen BTC – ostatnie 30 dni (kliknij, aby rozwinąć)"):
    st.caption("Źródło: CoinMarketCap")
    df_volume = get_spot_volume()
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df_volume["date"], df_volume["volume"], marker='o')
    ax.set_title("Wolumen spot BTC (USD)")
    ax.set_xlabel("Data")
    ax.set_ylabel("Wolumen")
    plt.xticks(rotation=45)
    st.pyplot(fig, clear_figure=True)
except Exception as e:
    st.error(f"Nie udało się pobrać danych: {e}")


# Reszta dashboardu (jak wcześniej)
st.header("1. 🎯 Premia/Dyskonto ETF")
st.markdown("""
- [Coinglass – ETF Premium Tracker](https://www.coinglass.com/etf)
- [GBTC.io – Grayscale BTC Premium](https://www.gbtc.io/)
- [Yahoo Finance – ETF Quotes](https://finance.yahoo.com)
""")

st.header("2. 🏦 Aktywność AP (ETF flows)")
st.markdown("""
- [Coinglass – ETF Flow Tracker](https://www.coinglass.com/etf)
- [Blockworks – ETF Tracker](https://blockworks.co/etf-tracker)
""")

st.header("📌 Wskazówki interpretacyjne")
st.markdown("""
- **Dodatnia premia ETF** ➜ większy popyt przez instytucje.
- **Aktywność AP** ➜ napływ kapitału.
- **Wzrost wolumenu spot** ➜ realny popyt.
""")

import yfinance as yf

def get_gbtc_premium():
    btc = yf.download("BTC-USD", period="1mo", interval="1d")
    gbtc = yf.download("GBTC", period="1mo", interval="1d")

    df = pd.DataFrame({
        "BTC": btc["Close"],
        "GBTC": gbtc["Close"]
    }).dropna()
    df["Premium"] = (df["GBTC"] / df["BTC"] - 1) * 100
    return df

st.header("📉 Premia GBTC względem ceny BTC")

try:
    df_premium = get_gbtc_premium()
    fig2, ax2 = plt.subplots(figsize=(6, 3))
    ax2.plot(df_premium.index, df_premium["Premium"], color="orange")
    ax2.axhline(0, linestyle='--', color='gray')
    ax2.set_title("Premia/Dyskonto GBTC (%)")
    ax2.set_ylabel("Premia [%]")
    ax2.set_xlabel("Data")
    plt.xticks(rotation=45)
    st.pyplot(fig2, clear_figure=True)
except Exception as e:
    st.error(f"Nie udało się pobrać premii GBTC: {e}")

