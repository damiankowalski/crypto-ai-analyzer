import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import requests
import os
import smtplib
import schedule
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

def load_token_from_binance(symbol, interval='1d', limit=180):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params)
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"Błąd pobierania danych dla {symbol}: {data}")
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close",
        "volume", "close_time", "quote_asset_volume",
        "number_of_trades", "taker_buy_base_volume",
        "taker_buy_quote_volume", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# Zaktualizowane symbole tokenów (2025)
tokens = {
    "Virtuals Protocol": "VIRTUALUSDT",
    "Fetch.ai": "FETUSDT",
    "Ocean Protocol": "OCEANUSDT",
    "SingularityNET": "AGIXUSDT",
    "Render": "RENDERUSDT",
    "Bittensor": "TAOUSDT",
    "Numerai": "NMRUSDT",
    "Cortex": "CTXCUSDT"
}

# Generowanie raportu PDF z fpdf2
class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 12)

    def summary_table(self, summaries):
        self.add_page()
        self.set_font("DejaVu", "", 14)
        self.cell(0, 10, "Podddddddsumowanie sygnałów zakupu", ln=True, align="C")
        self.ln(5)
        self.set_font("DejaVu", "", 12)
        self.set_fill_color(200, 200, 200)
        self.cell(60, 10, "Token", 1, 0, "C", True)
        self.cell(120, 10, "Ocena zakupu", 1, 1, "C", True)

        for token, ocena in summaries.items():
            if "🟢" in ocena:
                self.set_fill_color(180, 255, 180)
            elif "🟡" in ocena:
                self.set_fill_color(255, 240, 150)
            else:
                self.set_fill_color(255, 180, 180)
            self.cell(60, 10, token, 1, 0, "L", True)
            self.cell(120, 10, ocena, 1, 1, "L", True)

def analyze_tokens(selected_tokens):
    results = {}
    for token, symbol in selected_tokens.items():
        try:
            df = load_token_from_binance(symbol)
            rsi = compute_rsi(df["close"])
            macd, macd_signal = compute_macd(df["close"])
            ma50 = df["close"].rolling(window=50).mean()
            ma200 = df["close"].rolling(window=200).mean()

            latest_price = df["close"].iloc[-1]
            latest_rsi = rsi.iloc[-1]
            above_ma50 = latest_price > ma50.iloc[-1]
            above_ma200 = latest_price > ma200.iloc[-1]

            # Sygnał
            if latest_rsi < 30:
                if above_ma50 and above_ma200:
                    signal = "🟢 Tak – RSI < 30 i cena > MA50/MA200"
                elif above_ma50 or above_ma200:
                    signal = "🟡 Może – RSI < 30, ale tylko jedna z MA"
                else:
                    signal = "🔴 Nie – RSI < 30, cena poniżej obu MA"
            else:
                signal = "🔴 Nie – RSI nie jest poniżej 30"

            results[token] = {
                "symbol": symbol,
                "RSI": round(latest_rsi, 2),
                "Cena": round(latest_price, 3),
                "Wolumen": round(df['volume'].iloc[-1], 2),
                "MACD": round(macd.iloc[-1], 4),
                "MACD_signal": round(macd_signal.iloc[-1], 4),
                "Ocena zakupu": signal
            }
        except Exception as e:
            results[token] = {"Ocena zakupu": f"Błąd: {e}"}
    return results

def generate_pdf_report(results, filename="daily_report.pdf"):
    pdf = ReportPDF()
    summary = {token: data.get("Ocena zakupu", "Brak") for token, data in results.items()}
    pdf.summary_table(summary)
    pdf.output(filename)

def export_csv(results, filename="daily_report.csv"):
    df = pd.DataFrame(results).T
    df.index.name = "Token"
    df.to_csv(filename)

def send_email_with_pdf(filename, to_address):
    msg = MIMEMultipart()
    msg['Subject'] = 'Codzienny raport AI tokenów'
    msg['From'] = os.getenv("EMAIL_ADDRESS")
    msg['To'] = to_address
    body = MIMEText("W załączeniu codzienny raport.", 'plain')
    msg.attach(body)
    with open(filename, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(attach)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)

def main():
    st.title("Analiza Tokenów AI (RSI, MACD, MA)")
    selected = st.multiselect("Wybierz tokeny:", list(tokens.keys()), default=list(tokens.keys()))

    if st.button("📄 Wygeneruj PDF do pobrania"):
        result = analyze_tokens({k: tokens[k] for k in selected})
        generate_pdf_report(result)
        export_csv(result)
        with open("daily_report.pdf", "rb") as f:
            st.download_button("📥 Pobierz PDF", f, file_name="daily_report.pdf")

    if st.button("📊 Pokaż raport na stronie"):
        result = analyze_tokens({k: tokens[k] for k in selected})
        for token, data in result.items():
            st.subheader(token)
            for key, val in data.items():
                st.write(f"{key}: {val}")

if __name__ == "__main__":
    main()
