import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import requests
import os
import smtplib
import time
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from fpdf import FPDF
from datetime import datetime

load_dotenv()

# Obliczenia techniczne
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

def load_token_from_coingecko(slug, days=90):
    url = f"https://api.coingecko.com/api/v3/coins/{slug}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise ValueError(f"Brak danych z CoinGecko dla {slug}: {r.json()}")
    data = r.json()
    prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
    df = prices.merge(volumes, on='timestamp')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['price'] = df['price'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

# Tylko Virtuals Protocol
tokens = {
    "Virtuals Protocol": "virtual-protocol"
}

def analyze_tokens(selected_tokens):
    results = {}
    for token, slug in selected_tokens.items():
        try:
            df = load_token_from_coingecko(slug)
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

            signal = "🔴 Nie – RSI nie jest poniżej 30"
            if latest_rsi < 30:
                signal = "🟢 Tak – RSI < 30"

            results[token] = {
                "symbol": slug,
                "RSI": round(latest_rsi, 2),
                "Cena": round(latest_price, 3),
                "Wolumen": round(volume, 2),
                "MACD": round(latest_macd, 4),
                "MACD_signal": round(latest_macd_signal, 4),
                "EMA_short": round(latest_ema_short, 3),
                "EMA_long": round(latest_ema_long, 3),
                "BB_upper": round(latest_bb_upper, 3),
                "BB_lower": round(latest_bb_lower, 3),
                "Ocena zakupu": signal,
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

def main():
    st.title("Analiza Virtuals Protocol z CoinGecko")
    selected = st.multiselect("Wybierz tokeny:", list(tokens.keys()), default=list(tokens.keys()))
    if st.button("📄 Wygeneruj PDF"):
        result = analyze_tokens({k: tokens[k] for k in selected})
        st.success("PDF został wygenerowany.")
    if st.button("📊 Pokaż raport na stronie"):
        result = analyze_tokens({k: tokens[k] for k in selected})
        for token, data in result.items():
            st.subheader(token)
            if "Błąd" in data.get("Ocena zakupu", ""):
                st.error(data["Ocena zakupu"])
                continue

            df_display = pd.DataFrame.from_dict({
                "RSI": [data["RSI"]],
                "Cena": [data["Cena"]],
                "Wolumen": [data["Wolumen"]],
                "MACD": [data["MACD"]],
                "MACD_signal": [data["MACD_signal"]],
                "EMA_short": [data["EMA_short"]],
                "EMA_long": [data["EMA_long"]],
                "BB_upper": [data["BB_upper"]],
                "BB_lower": [data["BB_lower"]],
                "Ocena zakupu": [data["Ocena zakupu"]]
            }, orient='columns')
            st.dataframe(df_display.style.applymap(
                lambda val: 'background-color: #c8e6c9' if '🟢' in str(val)
                else ('background-color: #fff9c4' if '🟡' in str(val)
                else ('background-color: #ffcdd2' if '🔴' in str(val) else ''))
            ))

            st.write("### Wykres RSI")
            fig_rsi, ax_rsi = plt.subplots()
            data["rsi_series"].plot(ax=ax_rsi, label="RSI")
            ax_rsi.axhline(30, color="red", linestyle="--")
            ax_rsi.axhline(70, color="green", linestyle="--")
            ax_rsi.set_title("RSI")
            st.pyplot(fig_rsi)

            st.write("### Wykres MACD")
            fig_macd, ax_macd = plt.subplots()
            data["macd"].plot(ax=ax_macd, label="MACD")
            data["macd_signal"].plot(ax=ax_macd, label="MACD sygnał")
            ax_macd.legend()
            ax_macd.set_title("MACD")
            st.pyplot(fig_macd)

            st.write("### Wykres EMA")
            fig_ema, ax_ema = plt.subplots()
            data["df"]["price"].plot(ax=ax_ema, label="Cena")
            data["ema_short"].plot(ax=ax_ema, label="EMA 12")
            data["ema_long"].plot(ax=ax_ema, label="EMA 26")
            ax_ema.legend()
            ax_ema.set_title("EMA crossover")
            st.pyplot(fig_ema)

            st.write("### Bollinger Bands")
            fig_bb, ax_bb = plt.subplots()
            data["df"]["price"].plot(ax=ax_bb, label="Cena")
            data["bb_upper"].plot(ax=ax_bb, linestyle='--', label="Górna BB")
            data["bb_lower"].plot(ax=ax_bb, linestyle='--', label="Dolna BB")
            ax_bb.legend()
            ax_bb.set_title("Bollinger Bands")
            st.pyplot(fig_bb)

if __name__ == "__main__":
    main()
