import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import requests
import os
import smtplib
import schedule
import time
from fpdf import FPDF
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def compute_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(data):
    exp1 = data.ewm(span=12, adjust=False).mean()
    exp2 = data.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def load_token_from_binance(symbol, interval):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 180
    }
    response = requests.get(url, params=params)
    data = response.json()

    if not isinstance(data, list):
        raise ValueError(f"Brak danych z Binance dla {symbol}")

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close",
        "volume", "close_time", "quote_asset_volume",
        "number_of_trades", "taker_buy_base_volume",
        "taker_buy_quote_volume", "ignore"
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

tokens = {
    "Virtuals Protocol": "VIRTUALUSDT",
    "Fetch.ai": "FETUSDT",
    "Ocean Protocol": "OCEANUSDT",
    "SingularityNET": "AGIXUSDT",
    "Render Token": "RNDRUSDT",
    "Bittensor": "TAOUSDT",
    "Numerai": "NMRUSDT",
    "Cortex": "CTXCUSDT"
}

def generate_pdf_report(data_dict, filename="daily_report.pdf"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "", 12)

    pdf.add_page()
    pdf.set_font("DejaVu", "", 16)
    pdf.cell(200, 10, txt="Podsumowanie analizy", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("DejaVu", "", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(70, 10, "Token", 1, 0, 'C', True)
    pdf.cell(120, 10, "Ocena zakupu", 1, 1, 'C', True)
    for token, info in data_dict.items():
        ocena = info['summary'].get("Ocena zakupu", "Brak")
        if "🟢" in ocena:
            pdf.set_fill_color(200, 255, 200)
        elif "🟡" in ocena:
            pdf.set_fill_color(255, 255, 200)
        else:
            pdf.set_fill_color(255, 200, 200)
        pdf.cell(70, 10, token, 1, 0, 'L', True)
        pdf.cell(120, 10, ocena, 1, 1, 'L', True)

    for token, info in data_dict.items():
        pdf.add_page()
        pdf.set_font("DejaVu", "", 16)
        pdf.cell(200, 10, txt=f"Raport: {token}", ln=True, align='C')
        pdf.set_font("DejaVu", "", 12)
        for key, value in info['summary'].items():
            pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
        for plot_path in info['plots']:
            if os.path.exists(plot_path):
                pdf.image(plot_path, w=180)
    pdf.output(filename)

def analyze_tokens(selected_tokens, interval):
    results = {}
    for name in selected_tokens:
        try:
            df = load_token_from_binance(tokens[name], interval)
            prices = df['close']
            volume = df['volume']
            rsi = compute_rsi(prices)
            ma50 = prices.rolling(window=50).mean()
            ma200 = prices.rolling(window=200).mean()
            macd, macd_signal = compute_macd(prices)

            latest_price = prices.iloc[-1]
            latest_rsi = rsi.iloc[-1]
            above_ma50 = latest_price > ma50.iloc[-1]
            above_ma200 = latest_price > ma200.iloc[-1]

            signal = "🔴 Nie – RSI nie jest poniżej 30"
            if latest_rsi < 30:
                if above_ma50 and above_ma200:
                    signal = "🟢 Tak – RSI < 30 i cena powyżej MA50 i MA200"
                elif above_ma50 or above_ma200:
                    signal = "🟡 Może – RSI < 30, ale tylko jedna z MA"
                else:
                    signal = "🔴 Nie – RSI < 30, cena poniżej obu MA"

            summary = {
                "Data": prices.index[-1].date(),
                "Cena": round(latest_price, 4),
                "RSI": round(latest_rsi, 2),
                "Cena > MA50": above_ma50,
                "Cena > MA200": above_ma200,
                "MACD": round(macd.iloc[-1], 4),
                "MACD sygnał": round(macd_signal.iloc[-1], 4),
                "Ocena zakupu": signal
            }

            plot_paths = []
            def save_plot(fig, name):
                path = f"{name}.png"
                fig.savefig(path)
                plt.close(fig)
                plot_paths.append(path)

            fig, ax = plt.subplots()
            ax.plot(prices.index, prices, label="Cena")
            ax.plot(ma50.index, ma50, label="MA50")
            ax.plot(ma200.index, ma200, label="MA200")
            ax.set_title(f"Cena i MA – {name}")
            ax.legend()
            fig.autofmt_xdate()
            save_plot(fig, f"{name}_cena")

            fig2, ax2 = plt.subplots()
            ax2.plot(rsi.index, rsi, label="RSI", color="purple")
            ax2.axhline(30, color='red', linestyle='--')
            ax2.axhline(70, color='green', linestyle='--')
            ax2.set_title(f"RSI – {name}")
            ax2.legend()
            fig2.autofmt_xdate()
            save_plot(fig2, f"{name}_rsi")

            fig3, ax3 = plt.subplots()
            ax3.bar(volume.index, volume, label="Wolumen", color='gray')
            ax3.set_title(f"Wolumen – {name}")
            ax3.legend()
            fig3.autofmt_xdate()
            save_plot(fig3, f"{name}_volume")

            fig4, ax4 = plt.subplots()
            ax4.plot(macd.index, macd, label="MACD", color='blue')
            ax4.plot(macd_signal.index, macd_signal, label="Sygnał", color='orange')
            ax4.axhline(0, color='black', linestyle='--')
            ax4.set_title(f"MACD – {name}")
            ax4.legend()
            fig4.autofmt_xdate()
            save_plot(fig4, f"{name}_macd")

            results[name] = {"summary": summary, "plots": plot_paths, "df": df}

            csv_path = f"{name.replace(' ', '_')}_history.csv"
            df.to_csv(csv_path)
        except Exception as e:
            results[name] = {"summary": {"Błąd": str(e)}, "plots": []}
    return results

def main():
    st.title("Analiza Techniczna Tokenów AI")
    selected_tokens = st.multiselect("Wybierz tokeny do analizy:", list(tokens.keys()), default=list(tokens.keys()))
    interval = st.selectbox("Wybierz interwał danych:", ["1d", "1w"], index=0)

    if st.button("🔁 Wygeneruj i pokaż raport"):
        result = analyze_tokens(selected_tokens, interval)
        generate_pdf_report(result)

        st.success("Raport PDF został wygenerowany.")
        with open("daily_report.pdf", "rb") as f:
            st.download_button("📄 Pobierz raport PDF", f, file_name="daily_report.pdf")

        st.subheader("📊 Raport szczegółowy")
        for token, info in result.items():
            st.markdown(f"### {token}")
            ocena = info['summary'].get("Ocena zakupu", "")
            color = "#FFCCCC"
            if "🟢" in ocena:
                color = "#CCFFCC"
            elif "🟡" in ocena:
                color = "#FFFFCC"
            st.markdown(f'<div style="background-color:{color};padding:10px;border-radius:5px">{ocena}</div>', unsafe_allow_html=True)
            for key, value in info['summary'].items():
                if key != "Ocena zakupu":
                    st.write(f"**{key}**: {value}")
            for img_path in info['plots']:
                if os.path.exists(img_path):
                    st.image(img_path)
            if "df" in info:
                csv_data = info['df'].to_csv().encode('utf-8')
                st.download_button(
                    label=f"📥 Pobierz dane historyczne: {token}",
                    data=csv_data,
                    file_name=f"{token.replace(' ', '_')}_history.csv",
                    mime='text/csv'
                )

if __name__ == "__main__":
    main()
