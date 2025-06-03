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
    else:
        reasons.append("RSI >= 30")
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
    st.title("🔎 Analiza Tokenów AI i Blockchain")
    tokeny = get_token_list()
    default_tokens = ["Bitcoin", "Ethereum", "Virtuals Protocol"]

    selected = st.multiselect("Wybierz tokeny:", list(tokeny.keys()), default=default_tokens)
    days = st.selectbox("Zakres czasowy (dni):", [30, 90, 180], index=1)

    if st.button("📊 Pokaż raport"):
        results = []
        for token in selected:
            slug = tokeny[token]
            try:
                df = load_data(slug, days)
                rsi = compute_rsi(df['price'])
                macd, signal = compute_macd(df['price'])
                ema_s, ema_l = compute_ema(df['price'])
                price = df['price'].iloc[-1]
                conf, cause = compute_confidence(rsi.iloc[-1], macd.iloc[-1], signal.iloc[-1], price, ema_s.iloc[-1], ema_l.iloc[-1])

                decision = "TAK" if conf >= 66 else "MOŻE" if conf >= 33 else "NIE"

                results.append({
                    "Token": token,
                    "RSI": round(rsi.iloc[-1], 1),
                    "Ocena zakupu": decision,
                    "Cena": round(price, 2),
                    "MACD": round(macd.iloc[-1], 4),
                    "Sygnał MACD": round(signal.iloc[-1], 4),
                    "EMA12": round(ema_s.iloc[-1], 2),
                    "EMA26": round(ema_l.iloc[-1], 2),
                    "Pewność [%]": conf,
                    "Uzasadnienie": cause
                })
            except Exception as e:
                results.append({"Token": token, "Ocena zakupu": f"Błąd: {str(e)}"})

        df = pd.DataFrame(results)

        def highlight(row):
            color = "#c8e6c9" if row["Ocena zakupu"] == "TAK" else ("#fff9c4" if row["Ocena zakupu"] == "MOŻE" else "#ffcdd2")
            return ["background-color: " + color if col == "Ocena zakupu" else "" for col in row.index]

        st.dataframe(df.style.apply(highlight, axis=1))

if __name__ == "__main__":
    main()
