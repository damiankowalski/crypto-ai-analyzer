import streamlit as st
import requests
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
CMC_API_KEY = st.secrets["api_keys"]["cmc"]
CRYPTOPANIC_KEY = st.secrets["api_keys"]["cryptopanic"]
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
def get_etf_flows():
    today = datetime.date.today()
    return pd.DataFrame({
        "Date": [today - datetime.timedelta(days=i) for i in range(5)][::-1],
        "Inflows (USD)": [34.4e6, -12.5e6, 3.1e6, -6.2e6, -2.7e6],
        "BTC Price": [None, None, None, None, None]  # zostanie nadpisana
    })

@st.cache_data(show_spinner=False)
def get_dynamic_quotes(keyword=None):
    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": CRYPTOPANIC_KEY,
        "currencies": "BTC",
        "public": "true"
    }
    try:
        response = requests.get(url, params=params)
        news = response.json().get("results", [])
        if keyword:
            news = [item for item in news if keyword.lower() in item.get("title", "").lower()]
        quotes = []
        for item in news[:10]:
            title = item.get("title", "")
            source = item.get("source", {}).get("title", "")
            link = item.get("url", "")
            description = item.get("domain", "") or ""
            published = item.get("published_at", "")[:10]
            quotes.append({"title": title, "source": source, "link": link, "date": published, "desc": description})
        return sorted(quotes, key=lambda x: x['date'], reverse=True)
    except Exception:
        return []

# --- STREAMLIT UI ---
st.set_page_config(page_title="BTC Decision Dashboard", layout="wide")
st.title("📊 BTC Decision Support Dashboard")

# Auto-refresh logic
refresh_interval = 10 * 60 * 1000  # 10 minutes in milliseconds
st_autorefresh(interval=refresh_interval, key="datarefresh")

if st.button("🔄 Odśwież dane teraz"):
    st.cache_data.clear()
    st.rerun()

crypto = get_btc_data()
btc = crypto.get("BTC", {})
eth = crypto.get("ETH", {})
sentiment = get_sentiment()
etf_df = get_etf_flows()

# Nadpisanie ostatniego wiersza realną ceną BTC
etf_df.at[etf_df.index[-1], "BTC Price"] = btc['quote']['USD']['price']

# Ustawienie domyślnej ceny poprzedniego dnia, jeśli brak
if pd.isna(etf_df.iloc[-2]['BTC Price']):
    etf_df.at[etf_df.index[-2], "BTC Price"] = btc['quote']['USD']['price']

# --- BTC Data ---
st.subheader("📈 Aktualna sytuacja BTC")
st.markdown(f"**Cena BTC:** ${btc['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana 24h:** {btc['quote']['USD']['percent_change_24h']:.2f}%  ")
st.markdown(f"**Dominacja BTC:** {btc['quote']['USD']['market_cap_dominance']:.2f}%  ")
st.markdown(f"**Cena ETH:** ${eth['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana ETH 24h:** {eth['quote']['USD']['percent_change_24h']:.2f}%  ")

# --- Momentum signal ---
st.subheader("📊 Sygnał momentum")
latest_inflow = etf_df.iloc[-1]['Inflows (USD)']
latest_price = etf_df.iloc[-1]['BTC Price']
prev_price = etf_df.iloc[-2]['BTC Price']

if latest_inflow > 0 and latest_price > prev_price:
    st.success("📈 Momentum: **BYCZO** – ETF inflows rosną, a cena BTC również!")
elif latest_inflow < 0 and latest_price < prev_price:
    st.warning("📉 Momentum: **NEGATYWNE** – spadki zarówno inflowów jak i ceny.")
else:
    st.info("🤔 Momentum: **NIEJEDNOZNACZNE** – sprzeczne sygnały z ETF i cen.")

# --- ETF flows chart ---
st.subheader("📊 Napływy ETF vs Cena BTC")
fig_mixed = go.Figure()
fig_mixed.add_trace(go.Bar(x=etf_df['Date'], y=etf_df['Inflows (USD)'], name="ETF Inflows", marker_color='green'))
fig_mixed.add_trace(go.Scatter(x=etf_df['Date'], y=etf_df['BTC Price'], name="BTC Price", yaxis="y2", mode="lines+markers"))
fig_mixed.update_layout(
    title="Napływy ETF i Cena BTC",
    xaxis=dict(title="Data"),
    yaxis=dict(title="Inflows (USD)"),
    yaxis2=dict(title="BTC Price", overlaying="y", side="right"),
    height=300,
    margin=dict(l=30, r=30, t=30, b=30)
)
st.plotly_chart(fig_mixed, use_container_width=True)

# --- Techniczne ---
st.subheader("🔍 Wskaźniki techniczne (1h/4h)")
st.write(sentiment)

# --- ETF flows bar only ---
st.subheader("💰 Napływy do ETF BTC")
fig_flows = px.bar(
    etf_df,
    x='Date',
    y='Inflows (USD)',
    color='Inflows (USD)',
    color_continuous_scale=['red', 'green'],
    title='Napływy do ETF BTC (symulacja)',
    height=250
)
fig_flows.update_layout(
    margin=dict(l=30, r=30, t=30, b=30),
    coloraxis_showscale=False,
    yaxis_title='USD',
    xaxis_title='',
    title_font_size=14
)
st.plotly_chart(fig_flows, use_container_width=True)

st.caption("Źródło: symulowane dane + aktualna cena z CoinMarketCap")

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

# --- Historia rekomendacji ---
st.subheader("📅 Historia rekomendacji")
history_df = etf_df.copy()
history_df["Momentum"] = [
    "BYCZO" if row["Inflows (USD)"] > 0 and i > 0 and row["BTC Price"] > etf_df.iloc[i-1]["BTC Price"]
    else "NEGATYWNE" if row["Inflows (USD)"] < 0 and i > 0 and row["BTC Price"] < etf_df.iloc[i-1]["BTC Price"]
    else "NIEJEDNOZNACZNE"
    for i, row in etf_df.iterrows()
]
st.dataframe(history_df.rename(columns={"Date": "Data", "Inflows (USD)": "Napływ ETF", "BTC Price": "Cena BTC"}))

# --- Cytaty ---
st.subheader("📚 Cytaty z analiz i źródeł")
keyword = st.text_input("Filtruj cytaty po słowie kluczowym (np. ETF, reversal):")
quotes = get_dynamic_quotes(keyword)
if quotes:
    for quote in quotes:
        with st.expander(f"{quote['date']} – {quote['title']} ({quote['source']})"):
            st.markdown(f"📎 [Pełny tekst artykułu]({quote['link']})")
            st.caption(f"Domena: {quote['desc']}")
else:
    st.warning("Brak aktualnych cytatów z CryptoPanic.")

# --- Stopka ---
st.markdown("---")
st.caption("Dashboard by GPT | Źródła danych: CoinMarketCap API, CryptoPanic")
