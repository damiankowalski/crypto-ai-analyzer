import streamlit as st
import requests
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import feedparser
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
CMC_API_KEY = st.secrets["api_keys"]["cmc"]
HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

# --- HELPER FUNCTIONS ---
@st.cache_data(show_spinner=False)
def get_btc_data():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC,ETH", "convert": "USD"}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    return data["data"]

@st.cache_data(show_spinner=False)
def get_sentiment(btc):
    volume = btc['quote']['USD']['volume_24h']
    return {
        "RSI(14)": 49.8,  # Placeholder
        "MACD": -123,    # Placeholder
        "Volume_24h": volume,
        "EMA_trend": "spadkowy",
        "Interpretacja": f"Wolumen 24h: {volume/1e9:.2f} mld USD. Pozostałe dane: RSI/MACD - tymczasowe."
    }

@st.cache_data(show_spinner=False)
def get_rss_articles():
    feeds = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
        "https://cointelegraph.com/rss",
        "https://bitcoinist.com/feed"
    ]
    articles = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get("published", "brak daty")
                })
        except Exception as e:
            continue
    return articles

# --- GENERATE DYNAMIC ARGUMENTS ---
def generate_dynamic_arguments(btc, sentiment):
    price_change = btc['quote']['USD']['percent_change_24h']
    rsi = sentiment.get("RSI(14)", 50)
    macd = sentiment.get("MACD", 0)
    volume = sentiment.get("Volume_24h", 0)
    ema_trend = sentiment.get("EMA_trend", "neutralny")
    dominance = btc['quote']['USD'].get("market_cap_dominance", 50)

    arguments_for = []
    arguments_against = []

    if rsi < 32:
        arguments_for.append(f"RSI {rsi:.1f} wskazuje na wyprzedany rynek")
    else:
        arguments_against.append(f"RSI {rsi:.1f} nie wskazuje jeszcze na wyprzedanie")

    if price_change > 0:
        arguments_for.append(f"Cena BTC rośnie: +{price_change:.2f}% (24h)")
    else:
        arguments_against.append(f"Cena BTC spada: {price_change:.2f}% (24h)")

    if macd > 0:
        arguments_for.append(f"MACD dodatni: {macd}")
    else:
        arguments_against.append(f"MACD ujemny: {macd}")

    if dominance > 50:
        arguments_for.append(f"Dominacja BTC: {dominance:.2f}% (powyżej 50%)")
    else:
        arguments_against.append(f"Dominacja BTC: {dominance:.2f}% (poniżej 50%)")

    if ema_trend == "wzrostowy":
        arguments_for.append("EMA wskazuje na wzrostowy trend")
    elif ema_trend == "spadkowy":
        arguments_against.append("EMA wskazuje na spadkowy trend")

    if volume > 10e9:
        arguments_for.append(f"Wolumen 24h wysoki: {volume/1e9:.2f} mld USD")
    else:
        arguments_against.append(f"Wolumen 24h niski: {volume/1e9:.2f} mld USD")

    return arguments_for, arguments_against

# --- STREAMLIT UI ---
st.set_page_config(page_title="BTC Decision Dashboard", layout="wide")
st.title("\U0001F4CA BTC Decision Support Dashboard")

refresh_interval = 10 * 60 * 1000
st_autorefresh(interval=refresh_interval, key="datarefresh")

if st.button("\U0001F504 Odśwież dane teraz"):
    st.cache_data.clear()
    st.rerun()

crypto = get_btc_data()
btc = crypto.get("BTC", {})
eth = crypto.get("ETH", {})
sentiment = get_sentiment(btc)
articles = get_rss_articles()

# --- BTC Data ---
st.subheader("\U0001F4C8 Aktualna sytuacja BTC")
st.markdown(f"**Cena BTC:** ${btc['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana 24h:** {btc['quote']['USD']['percent_change_24h']:.2f}%  ")
st.markdown(f"**Dominacja BTC:** {btc['quote']['USD']['market_cap_dominance']:.2f}%  ")
st.markdown(f"**Cena ETH:** ${eth['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana ETH 24h:** {eth['quote']['USD']['percent_change_24h']:.2f}%  ")

# --- Techniczne ---
st.subheader("\U0001F50D Wskaźniki techniczne (1h/4h)")
st.write(sentiment)

# --- Argumentacja ---
st.subheader("\U0001F9E0 Argumenty za / przeciw zakupowi BTC")
args_for, args_against = generate_dynamic_arguments(btc, sentiment)

st.markdown("### ✅ **ZA ZAKUPEM**:")
for arg in args_for:
    st.markdown(f"- {arg}")

st.markdown("### ❌ **PRZECIW ZAKUPOWI**:")
for arg in args_against:
    st.markdown(f"- {arg}")

# --- Cytaty z RSS ---
st.subheader("\U0001F4DA Cytaty z analiz i źródeł")
if articles:
    for art in articles:
        st.markdown(f"**{art['title']}**  ")
        st.caption(f"{art['published']}")
        st.write(f"[Link do artykułu]({art['link']})")
else:
    st.info("Brak aktualnych cytatów z kanałów RSS.")

# --- Stopka ---
st.markdown("---")
st.caption("Dashboard by GPT | Źródła danych: CoinMarketCap API + RSS feeds")
