import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import requests
from datetime import datetime

# --- Wskaźniki techniczne ---
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

def compute_ema(data, short=12, long=26):
    return data.ewm(span=short).mean(), data.ewm(span=long).mean()

def compute_confidence(rsi, macd, signal, price, ema_s, ema_l):
    score = 0
    reasons = []
    if rsi < 30:
        score += 1
        reasons.append("RSI < 30")
    elif rsi > 70:
        reasons.append("RSI > 70 (sygnał sprzedaży)")
    else:
        reasons.append("RSI neutralne")

    if macd > signal:
        score += 1
        reasons.append("MACD > sygnał")
    else:
        reasons.append("MACD <= sygnał")

    if price > ema_s and price > ema_l:
        score += 1
        reasons.append("Cena > EMA12 i EMA26")
    else:
        reasons.append("Cena ≤ EMA12 lub EMA26")

    confidence = round(score / 3 * 100, 1)
    return confidence, ", ".join(reasons)

# --- API ---
def load_data(slug, days):
    url = f"https://api.coingecko.com/api/v3/coins/{slug}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise ValueError(f"Błąd pobierania danych dla {slug}: {r.json()}")
    data = r.json()
    df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['price'] = df['price'].astype(float)
    return df

# --- Tokeny ---
def get_token_list():
    return {
        "Virtuals Protocol": "virtual-protocol",
        "Bitcoin": "bitcoin",
        "Ethereum": "ethereum",
        "Fetch.ai": "fetch-ai",
        "Ocean Protocol": "ocean-protocol",
        "Render": "render-token",
        "The Graph": "the-graph",
        "SingularityNET": "singularitynet",
        "Bittensor": "bittensor",
        "iExec RLC": "iexec-rlc"
    }

# --- Główna logika ---
def main():
    st.set_page_config(layout="wide")
    st.title("🔎 Analiza Tokenów AI i Blockchain")
    tokeny = get_token_list()
    default_tokens = ["Bitcoin", "Ethereum", "Virtuals Protocol"]

    selected = st.multiselect("Wybierz tokeny:", list(tokeny.keys()), default=default_tokens)
    days = st.selectbox("Zakres czasowy (dni):", [30, 90, 180], index=1)

    if st.button("📊 Pokaż raport"):
        results = []
        charts = {}

        for token in selected:
            slug = tokeny[token]
            try:
                df = load_data(slug, days)
                rsi = compute_rsi(df['price'])
                macd, signal = compute_macd(df['price'])
                ema_s, ema_l = compute_ema(df['price'])

                rsi.index = df.index
                macd.index = df.index
                signal.index = df.index
                ema_s.index = df.index
                ema_l.index = df.index

                price = df['price'].iloc[-1]
                rsi_value = rsi.iloc[-1]
                conf, cause = compute_confidence(rsi_value, macd.iloc[-1], signal.iloc[-1], price, ema_s.iloc[-1], ema_l.iloc[-1])

                if rsi_value > 70:
                    decision = "SPRZEDAJ"
                elif conf >= 66:
                    decision = "KUP"
                elif conf >= 33:
                    decision = "MOŻE"
                else:
                    decision = "NIE"

                results.append({
                    "Token": token,
                    "RSI": round(rsi_value, 1),
                    "Ocena zakupu": decision,
                    "Cena": round(price, 2),
                    "MACD": round(macd.iloc[-1], 4),
                    "Sygnał MACD": round(signal.iloc[-1], 4),
                    "EMA12": round(ema_s.iloc[-1], 2),
                    "EMA26": round(ema_l.iloc[-1], 2),
                    "Pewność [%]": conf,
                    "Uzasadnienie": cause
                })

                # Przygotuj wykresy
                figs = []

                fig1, ax1 = plt.subplots()
                rsi.plot(ax=ax1)
                ax1.axhline(30, color='red', linestyle='--')
                ax1.axhline(70, color='green', linestyle='--')
                ax1.set_title("RSI")
                figs.append(fig1)

                fig2, ax2 = plt.subplots()
                macd.plot(ax=ax2, label='MACD')
                signal.plot(ax=ax2, label='Sygnał')
                ax2.legend()
                ax2.set_title("MACD")
                figs.append(fig2)

                fig3, ax3 = plt.subplots()
                df['price'].plot(ax=ax3, label='Cena')
                ema_s.plot(ax=ax3, label='EMA12')
                ema_l.plot(ax=ax3, label='EMA26')
                ax3.legend()
                ax3.set_title("EMA")
                figs.append(fig3)

                charts[token] = figs

            except Exception as e:
                results.append({"Token": token, "Ocena zakupu": f"Błąd: {str(e)}"})

        df_results = pd.DataFrame(results)

        def style_func(row):
            color_map = {
                "KUP": "#c8e6c9",
                "MOŻE": "#fff9c4",
                "NIE": "#ffcdd2",
                "SPRZEDAJ": "#ffab91"
            }
            bg = color_map.get(row["Ocena zakupu"], "#ffffff")
            return [f"background-color: {bg}; color: black; font-weight: bold" if col == "Ocena zakupu" else "" for col in row.index]

        st.subheader("📄 Podsumowanie")
        st.dataframe(df_results.style.apply(style_func, axis=1), use_container_width=True)

        for token in charts:
            with st.expander(f"Wykresy: {token}"):
                for fig in charts[token]:
                    st.pyplot(fig)

if __name__ == "__main__":
    main()
