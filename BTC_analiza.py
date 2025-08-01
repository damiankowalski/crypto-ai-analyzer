import streamlit as st
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
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
    
    if "data" not in data or "BTC" not in data["data"]:
        st.error("❌ Błąd pobierania danych z CoinMarketCap. Odpowiedź API:")
        st.json(data)  # pokaże całą strukturę
        st.stop()
    
    return data["data"]["BTC"]


def get_btc_ohlcv(days):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical"
    params = {
        "symbol": "BTC",
        "convert": "USD",
        "count": days,
        "interval": "daily"
    }
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()

    if "data" not in data or "quotes" not in data["data"]:
        st.error("Brak danych OHLCV w odpowiedzi API. Sprawdź limit planu lub dostępność danych.")
        return pd.DataFrame()

    quotes = data["data"]["quotes"]
    df = pd.DataFrame([{
        "Date": q["timestamp"][:10],
        "Open": q["quote"]["USD"]["open"],
        "High": q["quote"]["USD"]["high"],
        "Low": q["quote"]["USD"]["low"],
        "Close": q["quote"]["USD"]["close"]
    } for q in quotes])
    return df


def get_etf_flows():
    today = datetime.date.today()
    return pd.DataFrame({
        "Date": [today - datetime.timedelta(days=i) for i in range(5)],
        "Inflows (USD)": [34.4e6, -12.5e6, 3.1e6, -6.2e6, -2.7e6]
    })

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
        return quotes
    except Exception as e:
        return [
            "Brak połączenia z CryptoPanic API lub demo limit osiągnięty.",
            "Wersja fallback: RSI bliski strefy wyprzedania – Investing.com",
            "Liczba aktywnych adresów BTC spadła – AInvest",
            "BlackRock ETF napływy +34.4 mln USD – Blockchain.News"
        ]

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['RSI'] = rsi
    return df

def plot_etf_flows_interactive(df):
    fig = px.bar(
        df,
        x='Date',
        y='Inflows (USD)',
        color='Inflows (USD)',
        color_continuous_scale=['red', 'green'],
        title='Napływy do ETF BTC (symulacja)',
        height=250
    )
    fig.update_layout(
        margin=dict(l=30, r=30, t=30, b=30),
        coloraxis_showscale=False,
        yaxis_title='USD',
        xaxis_title='',
        title_font_size=14
    )
    return fig

def plot_candlestick(df):
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing_line_color='green', decreasing_line_color='red'
        )
    ])
    fig.update_layout(
        title='📉 Świecowy wykres BTC',
        yaxis_title='Cena USD',
        xaxis_title='Data',
        height=400,
        margin=dict(l=30, r=30, t=30, b=30)
    )
    return fig

def plot_rsi(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], mode='lines', name='RSI'))
    fig.add_hline(y=70, line_dash='dash', line_color='red')
    fig.add_hline(y=30, line_dash='dash', line_color='green')
    fig.update_layout(
        title='📉 RSI (14-dniowe)',
        yaxis_title='RSI',
        xaxis_title='Data',
        height=300,
        margin=dict(l=30, r=30, t=30, b=30)
    )
    return fig

# --- STREAMLIT UI ---
st.set_page_config(page_title="BTC Decision Dashboard", layout="wide")
st.title("📊 BTC Decision Support Dashboard")

interval = st.sidebar.radio("Zakres analizy:", options=["30 dni (dzienny)", "180 dni (tygodniowy)"])
days = 30 if "30" in interval else 180
btc = get_btc_data()
sentiment = get_sentiment()
etf_df = get_etf_flows()
ohlcv_df = get_btc_ohlcv(days)
ohlcv_df = calculate_rsi(ohlcv_df)

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
st.plotly_chart(plot_etf_flows_interactive(etf_df), use_container_width=True)
st.caption("Źródło: symulowane dane na podstawie analizy CoinGlass i Blockchain.News")

# --- Candlestick Chart ---
st.subheader("🕯️ Wykres świecowy BTC")
st.plotly_chart(plot_candlestick(ohlcv_df), use_container_width=True)

# --- RSI ---
st.subheader("📈 RSI w czasie")
st.plotly_chart(plot_rsi(ohlcv_df), use_container_width=True)

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
st.caption("Dashboard by GPT | Źródła danych: CoinMarketCap API, symulacje CoinGlass, analiza on-chain")
