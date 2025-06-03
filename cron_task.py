import os
import smtplib
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

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
    if rsi < 30:
        score += 1
    if macd > signal:
        score += 1
    if price > ema_s and price > ema_l:
        score += 1
    return round(score / 3 * 100, 1)

# --- Pobierz dane z CoinGecko ---
def load_data(slug):
    url = f"https://api.coingecko.com/api/v3/coins/{slug}/market_chart"
    params = {"vs_currency": "usd", "days": 90, "interval": "daily"}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise ValueError(f"Błąd pobierania danych dla {slug}: {r.json()}")
    data = r.json()
    df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['price'] = df['price'].astype(float)
    return df

# --- Wysyłka e-mail ---
def send_email(body):
    msg = MIMEMultipart()
    msg['From'] = os.getenv("EMAIL_ADDRESS")
    msg['To'] = os.getenv("EMAIL_ADDRESS")
    msg['Subject'] = '🔔 Sygnał zakupu AI tokenów'
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)

# --- Tokeny ---
tokens = {
    "Virtuals Protocol": "virtual-protocol",
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum"
}

# --- Główna logika ---
summary = []
for name, slug in tokens.items():
    try:
        df = load_data(slug)
        rsi = compute_rsi(df['price'])
        macd, signal = compute_macd(df['price'])
        ema_s, ema_l = compute_ema(df['price'])
        price = df['price'].iloc[-1]

        conf = compute_confidence(rsi.iloc[-1], macd.iloc[-1], signal.iloc[-1], price, ema_s.iloc[-1], ema_l.iloc[-1])
        decision = "🟢 TAK" if conf >= 66 else "🟡 MOŻE" if conf >= 33 else "🔴 NIE"

        summary.append(f"{name}: {decision} (RSI={rsi.iloc[-1]:.1f}, Conf={conf}%)")
    except Exception as e:
        summary.append(f"{name}: Błąd: {str(e)}")

# --- Wyślij tylko jeśli jest sygnał kupna ---
pos = [line for line in summary if "🟢" in line]
if pos:
    send_email("\n".join(pos))
