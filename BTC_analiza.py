import streamlit as st
import requests
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import feedparser

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
def get_etf_flows():
    today = datetime.date.today()
    return pd.DataFrame({
        "Date": [today - datetime.timedelta(days=i) for i in range(5)][::-1],
        "Inflows (USD)": [34.4e6, -12.5e6, 3.1e6, -6.2e6, -2.7e6],
        "BTC Price": [None, None, None, None, None]
    })

@st.cache_data(show_spinner=False)
def get_rss_quotes(keyword=None):
    feeds = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
        "https://bitcoinist.com/feed/"
    ]
    quotes = []
    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:10]:
            title = entry.title
            link = entry.link
            published = entry.published if "published" in entry else ""
            source = feed.feed.get("title", "")
            if keyword and keyword.lower() not in title.lower():
                continue
            quotes.append({"title": title, "link": link, "date": published[:10], "source": source, "desc": feed_url})
    return sorted(quotes, key=lambda x: x["date"], reverse=True)

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
etf_df = get_etf_flows()

etf_df.at[etf_df.index[-1], "BTC Price"] = btc['quote']['USD']['price']
if pd.isna(etf_df.iloc[-2]['BTC Price']):
    etf_df.at[etf_df.index[-2], "BTC Price"] = btc['quote']['USD']['price']

# --- BTC Data ---
st.subheader("\U0001F4C8 Aktualna sytuacja BTC")
st.markdown(f"**Cena BTC:** ${btc['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana 24h:** {btc['quote']['USD']['percent_change_24h']:.2f}%  ")
st.markdown(f"**Dominacja BTC:** {btc['quote']['USD']['market_cap_dominance']:.2f}%  ")
st.markdown(f"**Cena ETH:** ${eth['quote']['USD']['price']:.2f}  ")
st.markdown(f"**Zmiana ETH 24h:** {eth['quote']['USD']['percent_change_24h']:.2f}%  ")

# --- Momentum signal ---
st.subheader("\U0001F4CA Sygnał momentum")
latest_inflow = etf_df.iloc[-1]['Inflows (USD)']
latest_price = etf_df.iloc[-1]['BTC Price']
prev_price = etf_df.iloc[-2]['BTC Price']

if pd.notnull(latest_price) and pd.notnull(prev_price):
    if latest_inflow > 0 and latest_price > prev_price:
        st.success("\U0001F4C8 Momentum: **BYCZO** – ETF inflows rosną, a cena BTC również!")
    elif latest_inflow < 0 and latest_price < prev_price:
        st.warning("\U0001F4C9 Momentum: **NEGATYWNE** – spadki zarówno inflowów jak i ceny.")
    else:
        st.info("\U0001F914 Momentum: **NIEJEDNOZNACZNE** – sprzeczne sygnały z ETF i cen.")
else:
    st.info("Brak danych do oceny momentum.")

# --- ETF flows chart ---
st.subheader("\U0001F4CA Napływy ETF vs Cena BTC")
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
st.subheader("\U0001F50D Wskaźniki techniczne (1h/4h)")
st.write(sentiment)

# --- ETF flows bar ---
st.subheader("\U0001F4B0 Napływy do ETF BTC")
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

# --- Historia rekomendacji ---
st.subheader("\U0001F4C5 Historia rekomendacji")
history_df = etf_df.copy()
history_df["Momentum"] = []
for i, row in etf_df.iterrows():
    if i == 0 or pd.isna(row["BTC Price"]) or pd.isna(etf_df.iloc[i-1]["BTC Price"]):
        history_df.at[i, "Momentum"] = "BRAK DANYCH"
    elif row["Inflows (USD)"] > 0 and row["BTC Price"] > etf_df.iloc[i-1]["BTC Price"]:
        history_df.at[i, "Momentum"] = "BYCZO"
    elif row["Inflows (USD)"] < 0 and row["BTC Price"] < etf_df.iloc[i-1]["BTC Price"]:
        history_df.at[i, "Momentum"] = "NEGATYWNE"
    else:
        history_df.at[i, "Momentum"] = "NIEJEDNOZNACZNE"

st.dataframe(history_df.rename(columns={"Date": "Data", "Inflows (USD)": "Napływ ETF", "BTC Price": "Cena BTC"}))

# --- Cytaty z RSS ---
st.subheader("\U0001F4DA Cytaty z analiz i źródeł")
keyword = st.text_input("Filtruj cytaty po słowie kluczowym (np. ETF, reversal):")
quotes = get_rss_quotes(keyword)
if quotes:
    for quote in quotes:
        with st.expander(f"{quote['date']} – {quote['title']} ({quote['source']})"):
            st.markdown(f"\U0001F4CE [Pełny tekst artykułu]({quote['link']})")
            st.caption(f"Źródło: {quote['desc']}")
else:
    st.warning("Brak aktualnych cytatów z kanałów RSS.")

# --- Stopka ---
st.markdown("---")
st.caption("Dashboard by GPT | Źródła danych: CoinMarketCap API, RSS (Coindesk, Cointelegraph, Bitcoinist)")
