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
def get_sentiment():
    return {
        "RSI(14)": 31.5,
        "MACD": -676,
        "Interpretacja": "RSI wskazuje na niemal wyprzedany rynek; MACD sugeruje kontynuację trendu spadkowego."
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
sentiment = get_sentiment()
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
st.markdown("""
### ✅ **ZA ZAKUPEM**:
- RSI bliski wyprzedania (poniżej 32), możliwe techniczne odbicie
- ETF BlackRock z napływem +34.4 mln USD [Blockchain.News]
- Możliwe stabilizowanie się po spadkach (obrona poziomu ~115k USD)

### ❌ **PRZECIW ZAKUPOWI**:
- MACD silnie negatywny: –676 (sygnał kontynuacji spadków)
- Wolumen rośnie przy spadającej cenie → presja sprzedażowa
- Spadająca dominacja BTC i rosnące inflows w ETH ETF (rotacja kapitału)
- Liczba aktywnych adresów BTC spadła o ~47% w lipcu (źródło: AInvest)

➡️ **Rekomendacja**: Obserwuj RSI < 30 i napływy ETF. Krótkoterminowo możliwe dalsze osunięcie.
""")

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
