import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Minimalny CSS: mniejsze czcionki i lepszy wygląd na telefonie
st.set_page_config(page_title="BTC Dashboard - CMC API", layout="wide")
st.markdown("""
<style>
    h1, h2, h3, h4, .stText, .stMetric label, .stMarkdown {
        font-size: 16px !important;
    }
    .stMetric > div > div {
        font-size: 18px !important;
    }
    .element-container .stCaption {
        font-size: 13px !important;
        color: #bbb !important;
    }
    @media screen and (max-width: 600px) {
        h1, h2, h3 {
            font-size: 16px !important;
        }
        .stMetric > div > div {
            font-size: 16px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# API CMC
CMC_API_KEY = "tutaj_wklej_swoj_klucz"
HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

def get_btc_data():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC", "convert": "USD"}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()["data"]["BTC"]
    quote = data["quote"]["USD"]
    return {
        "price": quote["price"],
        "volume_24h": quote["volume_24h"],
        "percent_change_24h": quote["percent_change_24h"],
        "market_cap": quote["market_cap"],
        "circulating_supply": data.get("circulating_supply")
    }

def get_btc_history():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical"
    params = {"symbol": "BTC", "convert": "USD", "interval": "daily", "count": 30}
    r = requests.get(url, headers=HEADERS, params=params)
    quotes = r.json()["data"]["quotes"]
    df = pd.DataFrame([{
        "date": q["timestamp"][:10],
        "price": q["quote"]["USD"]["price"],
        "volume": q["quote"]["USD"]["volume_24h"]
    } for q in quotes])
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_global_metrics():
    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    r = requests.get(url, headers=HEADERS)
    data = r.json()["data"]
    return {
        "btc_dominance": data["btc_dominance"],
        "total_market_cap": data["quote"]["USD"]["total_market_cap"],
        "total_volume_24h": data["quote"]["USD"]["total_volume_24h"],
        "market_cap_change_24h": data["quote"]["USD"].get("market_cap_change_24h")
    }

def get_signal(change, volume):
    if change > 0 and volume > 20_000_000_000:
        return "BYCZO – rośnie cena i wolumen"
    elif change < 0 and volume > 20_000_000_000:
        return "SPADKOWO – cena spada mimo wysokiego wolumenu"
    else:
        return "NEUTRALNIE"

# UI
st.title("BTC Market Overview (CMC API – Hobbyist)")

try:
    btc = get_btc_data()
    df = get_btc_history()
    price_7d_change = ((df.iloc[-1]["price"] - df.iloc[-7]["price"]) / df.iloc[-7]["price"]) * 100
    price_30d_change = ((df.iloc[-1]["price"] - df.iloc[0]["price"]) / df.iloc[0]["price"]) * 100
    avg_volume_3d = df.tail(3)["volume"].mean()
    avg_volume_30d = df["volume"].mean()
    volume_trend = "rośnie" if avg_volume_3d > avg_volume_30d else "spada"

    st.subheader("Dane BTC")
    col1, col2, col3 = st.columns(3)
    col1.metric("Cena BTC", f"${btc['price']:.2f}")
    col2.metric("Zmiana 24h", f"{btc['percent_change_24h']:.2f}%")
    col3.metric("Market Cap", f"${btc['market_cap'] / 1e9:.2f}B")
    st.caption("Market Cap to całkowita wartość wszystkich BTC w obiegu.")

    col4, col5 = st.columns(2)
    col4.metric("Wolumen 24h", f"${btc['volume_24h'] / 1e9:.2f}B")
    col5.metric("Obieg BTC", f"{btc['circulating_supply']:.0f} BTC")
    st.caption("Obieg BTC to liczba BTC dostępnych na rynku.")

    st.subheader("Ocena sytuacji")
    signal = get_signal(btc['percent_change_24h'], btc['volume_24h'])
    if signal.startswith("BYCZO"):
        st.success(signal)
    elif signal.startswith("NEUTRALNIE"):
        st.warning(signal)
    else:
        st.error(signal)
    st.caption("Sygnał BYCZO = jednoczesny wzrost ceny i wolumenu.")

    col6, col7 = st.columns(2)
    col6.metric("Zmiana 7 dni", f"{price_7d_change:.2f}%")
    col7.metric("Zmiana 30 dni", f"{price_30d_change:.2f}%")
    st.caption(f"Trend wolumenu: {volume_trend}")

except Exception as e:
    st.error(f"Błąd pobierania danych BTC: {e}")

st.divider()
st.header("Globalne metryki rynku")
try:
    global_data = get_global_metrics()
    col1, col2 = st.columns(2)
    col1.metric("Dominacja BTC", f"{global_data['btc_dominance']:.2f}%")
    col2.metric("Market Cap", f"${global_data['total_market_cap'] / 1e12:.2f}T")
    st.metric("Wolumen rynku 24h", f"${global_data['total_volume_24h'] / 1e9:.2f}B")
    st.caption("Dominacja BTC to udział Bitcoina w całym rynku.")
    if global_data['market_cap_change_24h']:
        st.caption(f"Zmiana kapitalizacji 24h: {global_data['market_cap_change_24h']:.2f} USD")
except Exception as e:
    st.error(f"Błąd metryk globalnych: {e}")