import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# 🔑 Wpisz tu swój klucz API z CoinMarketCap
CMC_API_KEY = "4f9d6276-feee-4925-aaa6-cc6d68701e12"

def get_spot_volume():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/historical"
    parameters = {
        "symbol": "BTC",
        "convert": "USD",
        "time_period": "daily",
        "time_start": (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d"),
        "time_end": pd.Timestamp.now().strftime("%Y-%m-%d")
    }
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()

    ohlcv = data["data"]["quotes"]
    df = pd.DataFrame([{
        "date": q["time_open"][:10],
        "volume": q["quote"]["USD"]["volume"]
    } for q in ohlcv])
    df["date"] = pd.to_datetime(df["date"])
    return df

# 🌐 Interfejs
st.set_page_config(page_title="Bitcoin ETF Dashboard", layout="wide")
st.title("📊 Bitcoin ETF Dashboard z danymi na żywo")

st.header("📈 Realny wolumen BTC – ostatnie 30 dni (dane z CoinMarketCap)")
try:
    df_volume = get_spot_volume()
    fig, ax = plt.subplots()
    ax.plot(df_volume["date"], df_volume["volume"], marker='o')
    ax.set_title("Wolumen spot BTC (USD)")
    ax.set_xlabel("Data")
    ax.set_ylabel("Wolumen")
    plt.xticks(rotation=45)
    st.pyplot(fig)
except Exception as e:
    st.error(f"Nie udało się pobrać danych: {e}")

# Reszta dashboardu (jak wcześniej)
st.header("1. 🎯 Premia/Dyskonto ETF")
st.markdown("""
- [Coinglass – ETF Premium Tracker](https://www.coinglass.com/proshares-btc-premium)
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
