import streamlit as st
import requests
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIG ---
CMC_API_KEY = st.secrets["api_keys"]["cmc"]
CRYPTOPANIC_KEY = st.secrets["api_keys"]["cryptopanic"]
HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

# --- HELPER FUNCTIONS ---
def get_btc_data():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC", "convert": "USD"}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    return data["data"]["BTC"]

def get_sentiment():
    return {
        "RSI(14)": 31.5,
        "MACD": -676,
        "Interpretacja": "RSI wskazuje na niemal wyprzedany rynek; MACD sugeruje kontynuację trendu spadkowego."
    }

def get_dynamic_quotes():
    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": CRYPTOPANIC_KEY,
        "currencies": "BTC",
        "public": "true"
    }
    try:
        response = requests.get(url, params=params)
        news = response.json().get("results", [])
        quotes = []
        for item in news[:5]:
            title = item.get("title", "")
            source = item.get("source", {}).get("title", "")
            link = item.get("url", "")
            quotes.append(f"[{title}]({link}) – {source}")
        return quotes if quotes else ["Brak aktualnych cytatów z CryptoPanic."]
    except Exception:
        return ["Błąd pobierania cytatów z CryptoPanic API"]

# --- STREAMLIT UI ---
st.set_page_config(page_title="BTC Decision Dashboard", layout="wide")
st.title("📊 BTC Decision Support Dashboard")

btc = get_btc_data()
sentiment = get_sentiment()

# --- BTC Data ---
st.subheader("📈 Aktualna sytuacja BTC")
st.markdown(f"**Cena:** ${btc['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana 24h:** {btc['quote']['USD']['percent_change_24h']:.2f}%  ")
st.markdown(f"**Wolumen 24h:** ${btc['quote']['USD']['volume_24h'] / 1e9:.2f} mld  ")
st.markdown(f"**Dominacja BTC:** {btc['quote']['USD']['market_cap_dominance']:.2f}%  ")

# --- Techniczne ---
st.subheader("🔍 Wskaźniki techniczne (1h/4h)")
st.write(sentiment)

# --- Argumentacja ---
st.subheader("🧠 Argumenty za / przeciw zakupowi BTC")
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

# --- Odczyt danych źródłowych ---
with st.expander("📚 Cytaty z analiz i źródeł"):
    for quote in get_dynamic_quotes():
        st.markdown(f"- *{quote}*")

# --- Stopka ---
st.markdown("---")
st.caption("Dashboard by GPT | Źródła danych: CoinMarketCap API, CryptoPanic")
