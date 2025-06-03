import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import requests
from datetime import datetime

# --- Techniczne wskaźniki ---
def compute_rsi(data, window=14):
    delta = data.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_macd(data):
    exp1 = data.ewm(span=12, adjust=False).mean()
    exp2 = data.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def compute_ema_crossover(data):
    ema_short = data.ewm(span=12, adjust=False).mean()
    ema_long = data.ewm(span=26, adjust=False).mean()
    return ema_short, ema_long

def compute_bollinger_bands(data, window=20):
    ma = data.rolling(window).mean()
    std = data.rolling(window).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    return ma, upper, lower

def compute_confidence_score(rsi, macd, macd_signal, price, ema_short, ema_long):
    score = 0
    if rsi < 30:
        score += 1
    if macd > macd_signal:
        score += 1
    if price > ema_short and price > ema_long:
        score += 1
    return score / 3 * 100

# --- Dane z CoinGecko ---
def load_token_from_coingecko(slug, days):
    url = f"https://api.coingecko.com/api/v3/coins/{slug}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
    df = prices.merge(volumes, on='timestamp')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['price'] = df['price'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

# --- Tokeny ---
all_tokens = {
    "Virtuals Protocol": "virtual-protocol",
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Fetch.ai": "fetch-ai",
    "SingularityNET": "singularitynet",
    "Ocean Protocol": "ocean-protocol",
    "Render": "render-token",
    "Graph": "the-graph"
}

def analyze_tokens(selected_tokens, interval):
    results = {}
    for token, slug in selected_tokens.items():
        try:
            df = load_token_from_coingecko(slug, days=interval)
            rsi = compute_rsi(df["price"])
            macd, macd_signal = compute_macd(df["price"])
            ema_short, ema_long = compute_ema_crossover(df["price"])
            bb_ma, bb_upper, bb_lower = compute_bollinger_bands(df["price"])

            latest_price = df["price"].iloc[-1]
            latest_rsi = rsi.iloc[-1]
            volume = df['volume'].iloc[-1]
            latest_macd = macd.iloc[-1]
            latest_macd_signal = macd_signal.iloc[-1]
            latest_ema_short = ema_short.iloc[-1]
            latest_ema_long = ema_long.iloc[-1]
            latest_bb_upper = bb_upper.iloc[-1]
            latest_bb_lower = bb_lower.iloc[-1]

            score = compute_confidence_score(latest_rsi, latest_macd, latest_macd_signal, latest_price, latest_ema_short, latest_ema_long)
            signal = "Tak" if score >= 66 else "Może" if score >= 33 else "Nie"

            results[token] = {
                "symbol": slug,
                "RSI": round(latest_rsi, 2),
                "Ocena zakupu": signal,
                "Cena": round(latest_price, 3),
                "Wolumen": round(volume, 2),
                "MACD": round(latest_macd, 4),
                "MACD_signal": round(latest_macd_signal, 4),
                "EMA_short": round(latest_ema_short, 3),
                "EMA_long": round(latest_ema_long, 3),
                "BB_upper": round(latest_bb_upper, 3),
                "BB_lower": round(latest_bb_lower, 3),
                "Confidence": f"{score:.1f}%",
                "df": df,
                "rsi_series": rsi,
                "macd": macd,
                "macd_signal": macd_signal,
                "ema_short": ema_short,
                "ema_long": ema_long,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower
            }
        except Exception as e:
            results[token] = {"Ocena zakupu": f"Błąd: {e}"}
    return results

# --- Główna aplikacja Streamlit ---
def main():
    st.set_page_config(page_title="Analiza Tokenów AI", layout="wide")
    st.title("📈 Analiza Tokenów z CoinGecko")

    default_tokens = ["Bitcoin", "Ethereum", "Virtuals Protocol"]
    selected = st.multiselect("Wybierz tokeny:", list(all_tokens.keys()), default=default_tokens)
    interval = st.selectbox("Zakres danych (dni):", [30, 90, 180], index=1)

    if st.button("🔍 Analizuj"):
        result = analyze_tokens({k: all_tokens[k] for k in selected}, interval)

        st.subheader("📊 Podsumowanie")
        combined_data = []
        for token, data in result.items():
            if "Błąd" in data.get("Ocena zakupu", ""):
                continue
            row = {
                "Token": token,
                "RSI": data["RSI"],
                "Ocena zakupu": data["Ocena zakupu"],
                "Cena": data["Cena"],
                "Wolumen": data["Wolumen"],
                "MACD": data["MACD"],
                "MACD_signal": data["MACD_signal"],
                "EMA_short": data["EMA_short"],
                "EMA_long": data["EMA_long"],
                "BB_upper": data["BB_upper"],
                "BB_lower": data["BB_lower"],
                "Confidence": data["Confidence"]
            }
            combined_data.append(row)

        if combined_data:
            df_summary = pd.DataFrame(combined_data)
            st.dataframe(df_summary.style.applymap(
                lambda val: 'background-color: #c8e6c9' if val == "Tak" else
                            'background-color: #fff9c4' if val == "Może" else
                            'background-color: #ffcdd2' if val == "Nie" else '')
            )

        tabs = st.tabs(list(result.keys()))
        for idx, (token, data) in enumerate(result.items()):
            with tabs[idx]:
                if "Błąd" in data.get("Ocena zakupu", ""):
                    st.error(data["Ocena zakupu"])
                    continue

                st.subheader(f"Wykresy dla {token}")

                st.write("### RSI")
                fig_rsi, ax_rsi = plt.subplots(figsize=(8, 3), dpi=150)
                data["rsi_series"].plot(ax=ax_rsi, label="RSI")
                ax_rsi.axhline(30, color="red", linestyle="--")
                ax_rsi.axhline(70, color="green", linestyle="--")
                ax_rsi.set_title("RSI")
                st.pyplot(fig_rsi)

                st.write("### MACD")
                fig_macd, ax_macd = plt.subplots(figsize=(8, 3), dpi=150)
                data["macd"].plot(ax=ax_macd, label="MACD")
                data["macd_signal"].plot(ax=ax_macd, label="Sygnał")
                ax_macd.legend()
                ax_macd.set_title("MACD")
                st.pyplot(fig_macd)

                st.write("### EMA")
                fig_ema, ax_ema = plt.subplots(figsize=(8, 3), dpi=150)
                data["df"]["price"].plot(ax=ax_ema, label="Cena")
                data["ema_short"].plot(ax=ax_ema, label="EMA 12")
                data["ema_long"].plot(ax=ax_ema, label="EMA 26")
                ax_ema.legend()
                ax_ema.set_title("EMA Crossover")
                st.pyplot(fig_ema)

                st.write("### Bollinger Bands")
                fig_bb, ax_bb = plt.subplots(figsize=(8, 3), dpi=150)
                data["df"]["price"].plot(ax=ax_bb, label="Cena")
                data["bb_upper"].plot(ax=ax_bb, linestyle='--', label="Górna BB")
                data["bb_lower"].plot(ax=ax_bb, linestyle='--', label="Dolna BB")
                ax_bb.legend()
                ax_bb.set_title("Bollinger Bands")
                st.pyplot(fig_bb)

if __name__ == "__main__":
    main()
