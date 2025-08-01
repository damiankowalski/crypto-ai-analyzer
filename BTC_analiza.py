import streamlit as st
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIG ---
CMC_API_KEY = "4f9d6276-feee-4925-aaa6-cc6d68701e12"
HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

# --- HELPER FUNCTIONS ---
def get_btc_data():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC", "convert": "USD"}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    return data["data"]["BTC"]

def get_etf_flows():
    # Placeholder – simulate with dummy data until CMC exposes ETF endpoint
    today = datetime.date.today()
    return pd.DataFrame({
        "Date": [today - datetime.timedelta(days=i) for i in range(5)],
        "Inflows (USD)": [34.4e6, -12.5e6, 3.1e6, -6.2e6, -2.7e6]
    })

def get_sentiment():
    # Dummy sentiment from external analysis (normally would pull from a source)
    return {
        "RSI(14)": 31.5,
        "MACD": -676,
        "Interpretacja": "RSI wskazuje na niemal wyprzedany rynek; MACD sugeruje kontynuację trendu spadkowego."
    }

def plot_etf_flows(df):
    fig, ax = plt.subplots(figsize=(6, 3))  # Reduced size
    ax.bar(df['Date'], df['Inflows (USD)'], color=["green" if x > 0 else "red" for x in df['Inflows (USD)']])
    ax.axhline(0, color='black', linestyle='--')
    ax.set_title("Napływy do ETF BTC (symulacja)")
    ax.set_ylabel("USD")
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# --- STREAMLIT UI ---
st.set_page_config(page_title="BTC Decision Dashboard", layout="wide")
st.title("📊 BTC Decision Support Dashboard")

btc = get_btc_data()
sentiment = get_sentiment()
etf_df = get_etf_flows()

# --- BTC Data ---
st.subheader("📈 Aktualna sytuacja BTC")
st.markdown(f"**Cena:** ${btc['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana 24h:** {btc['quote']['USD']['percent_change_24h']:.2f}%  ")
st.markdown(f"**Wolumen 24h:** ${btc['quote']['USD']['volume_24h'] / 1e9:.2f} mld  ")
st.markdown(f"**Dominacja BTC:** {btc['quote']['USD']['market_cap_dominance']:.2f}%  ")

# --- Techniczne ---
st.subheader("🔍 Wskaźniki techniczne (1h/4h)")
st.write(sentiment)

# --- ETF flows ---
st.subheader("💰 Napływy do ETF BTC")
st.pyplot(plot_etf_flows(etf_df), use_container_width=True)
st.caption("Źródło: symulowane dane na podstawie analizy CoinGlass i Blockchain.News")

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
    st.markdown("""
- *„RSI bliski strefy wyprzedania, MACD silnie ujemny – to może sugerować dalszy spadek ceny BTC przed ewentualnym odbiciem”* – Investing.com
- *„Liczba aktywnych adresów BTC spadła do 380 000 z 570–800k”* – AInvest
- *„Ethereum przejmuje dominację w inflows ETF – może to przyciągać uwagę inwestorów kosztem Bitcoina”* – EconomicTimes
- *„BlackRock zgłosił +34.4 mln USD napływów do ETF”* – Blockchain.News
    """)

# --- Stopka ---
st.markdown("---")
st.caption("Dashboard by GPT | Źródła danych: CoinMarketCap API, symulacje CoinGlass, analiza on-chain")
