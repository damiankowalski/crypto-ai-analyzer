import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import yfinance as yf

# 🔑 Klucz API z CoinMarketCap
CMC_API_KEY = "4f9d6276-feee-4925-aaa6-cc6d68701e12"

# 🔄 Funkcja: Wolumen BTC
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

# 🔄 Funkcja: Globalne metryki rynku

def get_global_metrics():
    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Błąd API global-metrics: {response.status_code} – {response.text}")

    data = response.json()["data"]

    return {
        "btc_dominance": data["btc_dominance"],
        "total_volume_24h": data["quote"]["USD"]["total_volume_24h"],
        "total_market_cap": data["quote"]["USD"]["total_market_cap"],
        "btc_market_cap": data["btc_market_cap"],
        "btc_market_cap_change_24h": data["quote"]["USD"]["market_cap_change_24h"]
    }

# 🌐 Interfejs
st.set_page_config(page_title="Bitcoin ETF Dashboard", layout="wide")
st.title("📊 Bitcoin ETF Dashboard z danymi na żywo")

# 🌐 Sekcja: Globalne metryki
st.header("🌐 Globalne metryki rynku krypto (z CoinMarketCap)")
try:
    metrics = get_global_metrics()

    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Dominacja BTC", f"{metrics['btc_dominance']:.2f}%")
    col2.metric("💰 Wolumen 24h", f"${metrics['total_volume_24h'] / 1e9:.2f}B")
    col3.metric("🌎 Market Cap", f"${metrics['total_market_cap'] / 1e12:.2f}T")

    st.caption(f"Zmiana kapitalizacji BTC 24h: {metrics['btc_market_cap_change_24h']:.2f} USD")
except Exception as e:
    st.error(f"Nie udało się pobrać globalnych metryk: {e}")

# 🔍 Sekcja: Wolumen spot BTC
with st.expander("📈 Realny wolumen BTC – ostatnie 30 dni (kliknij, aby rozwinąć)"):
    st.caption("Źródło: CoinMarketCap")
    try:
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

# 📉 Premia GBTC
st.header("📉 Premia GBTC względem ceny BTC")

def get_gbtc_premium():
    btc = yf.download("BTC-USD", period="1mo", interval="1d")
    gbtc = yf.download("GBTC", period="1mo", interval="1d")

    if btc.empty or gbtc.empty:
        raise Exception("Brak danych z Yahoo Finance (BTC lub GBTC)")

    df = pd.concat([btc["Close"], gbtc["Close"]], axis=1)
    df.columns = ["BTC", "GBTC"]
    df.dropna(inplace=True)

    df["Premium"] = (df["GBTC"] / df["BTC"] - 1) * 100
    return df

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

# 📌 Informacje dodatkowe
st.header("📘 Wskazówki interpretacyjne")
st.markdown("""
- **Dodatnia premia ETF** ➜ większy popyt przez instytucje.
- **Aktywność AP** ➜ napływ kapitału.
- **Wzrost wolumenu spot** ➜ realny popyt.
""")
