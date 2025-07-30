import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="BTC Dashboard - CMC API", layout="wide")

# 💄 Stylizacja
st.markdown("""
<style>
    .big-font { font-size:24px !important; }
    .small-font { font-size:14px !important; }
    .metric-label > div { font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

CMC_API_KEY = "4f9d6276-feee-4925-aaa6-cc6d68701e12"
HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

# === API ===
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

def get_tokens(symbols):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": ",".join(symbols), "convert": "USD"}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json().get("data", {})
    result = []
    for sym, info in data.items():
        q = info["quote"]["USD"]
        result.append({
            "symbol": sym,
            "price": q["price"],
            "change24h": q["percent_change_24h"],
            "volume24h": q["volume_24h"]
        })
    return result

# === Logika ===
def get_signal(change, volume):
    if change > 0 and volume > 20_000_000_000:
        return "🟢 BYCZO – rośnie cena i wolumen"
    elif change < 0 and volume > 20_000_000_000:
        return "🔴 SPADKOWO – cena spada mimo wysokiego wolumenu"
    else:
        return "🟡 NEUTRALNIE"

# === DASHBOARD ===
st.title("📊 BTC Market Overview (CMC API – Hobbyist)")

try:
    btc = get_btc_data()
    df = get_btc_history()

    price_7d_change = ((df.iloc[-1]["price"] - df.iloc[-7]["price"]) / df.iloc[-7]["price"]) * 100
    price_30d_change = ((df.iloc[-1]["price"] - df.iloc[0]["price"]) / df.iloc[0]["price"]) * 100
    avg_volume_3d = df.tail(3)["volume"].mean()
    avg_volume_30d = df["volume"].mean()
    volume_trend = "🔼 rośnie" if avg_volume_3d > avg_volume_30d else "🔽 spada"

    st.subheader("📌 Dane BTC")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Cena BTC", f"${btc['price']:.2f}")
    col2.metric("📉 Zmiana 24h", f"{btc['percent_change_24h']:.2f}%")
    col3.metric("📊 Market Cap", f"${btc['market_cap'] / 1e9:.2f}B")

    col4, col5 = st.columns(2)
    col4.metric("🔁 Wolumen 24h", f"${btc['volume_24h'] / 1e9:.2f}B")
    col5.metric("🔄 Obieg BTC", f"{btc['circulating_supply']:.0f} BTC")

    st.subheader("📈 Ocena sytuacji")
    signal = get_signal(btc['percent_change_24h'], btc['volume_24h'])
    if signal.startswith("🟢"):
        st.success(signal)
    elif signal.startswith("🟡"):
        st.warning(signal)
    else:
        st.error(signal)

    col6, col7 = st.columns(2)
    col6.metric("📆 Zmiana 7 dni", f"{price_7d_change:.2f}%")
    col7.metric("📆 Zmiana 30 dni", f"{price_30d_change:.2f}%")
    st.caption(f"📊 Trend wolumenu: {volume_trend}")

except Exception as e:
    st.error(f"Błąd podczas pobierania danych BTC: {e}")

st.divider()
st.header("🌍 Globalne metryki rynku")
try:
    global_data = get_global_metrics()
    col1, col2 = st.columns(2)
    col1.metric("🪙 Dominacja BTC", f"{global_data['btc_dominance']:.2f}%")
    col2.metric("🌐 Market Cap", f"${global_data['total_market_cap'] / 1e12:.2f}T")
    st.metric("🔁 Wolumen rynku 24h", f"${global_data['total_volume_24h'] / 1e9:.2f}B")

    if global_data['market_cap_change_24h']:
        st.caption(f"Zmiana kapitalizacji rynku 24h: {global_data['market_cap_change_24h']:.2f} USD")
except Exception as e:
    st.error(f"Błąd podczas pobierania metryk globalnych: {e}")

st.divider()
st.header("🔎 Porównanie tokenów wg kategorii")

# Przykładowe tokeny
tokens_AI = ["FET", "INJ", "GRT"]
tokens_DeFi = ["UNI", "AAVE", "COMP"]

for category, tickers in [("AI & Big Data", tokens_AI), ("DeFi", tokens_DeFi)]:
    try:
        data = get_tokens(tickers)
        df = pd.DataFrame(data)
        st.subheader(f"{category}")
        st.table(df)
    except Exception as e:
        st.warning(f"Błąd przy pobieraniu danych {category}: {e}")

st.divider()
st.header("📌 Premia ETF i aktywność AP")
st.markdown("""
- 🔗 [Coinglass – ETF Premium Tracker](https://www.coinglass.com/etf)
- 🔗 [Blockworks – ETF Flows](https://blockworks.co/etf-tracker)

🧭 Obserwuj:
- Czy ETF-y mają premię czy dyskonto względem ceny BTC
- Czy fundusze typu IBIT, GBTC mają napływy (tworzenie jednostek przez AP)
- Przy dodatniej premii i napływie – może być to sygnał byczy 🟢
- Przy odpływach i ujemnej premii – może to sugerować presję sprzedażową 🔴
""")
