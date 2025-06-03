import os
import smtplib
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF
from datetime import datetime

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

# --- PDF ---
class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", "DejaVuSans.ttf")
        self.set_font("DejaVu", "", 14)

    def header(self):
        self.set_font("DejaVu", "", 14)
        self.cell(0, 10, "Raport Sygnałów Zakupu Tokenów AI", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(10)

    def summary_table(self, rows):
        self.set_font("DejaVu", "", 11)
        self.set_fill_color(220, 220, 220)
        self.cell(60, 10, "Token", 1, 0, "C", 1)
        self.cell(120, 10, "Ocena zakupu", 1, 1, "C", 1)
        for token, ocena in rows:
            self.set_fill_color(255, 255, 255)
            self.cell(60, 10, token, 1, 0, "L", 1)
            self.cell(120, 10, ocena, 1, 1, "L", 1)

def generate_pdf(rows, filename="crypto_report.pdf"):
    pdf = PDFReport()
    pdf.add_page()
    pdf.summary_table(rows)
    pdf.output(filename)
    return filename

# --- Pobierz dane z CoinGecko ---
def load_data(slug):
    url = f"https://api.coingecko.com/api/v3/coins/{slug}/market_chart"
    params = {"vs_currency": "usd", "days": 90, "interval": "daily"}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise ValueError(f"Blad pobierania danych dla {slug}: {r.json()}")
    data = r.json()
    df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['price'] = df['price'].astype(float)
    return df

# --- Wysyłka e-mail ---
def send_email(body, attachment_paths=None):
    msg = MIMEMultipart()
    msg['From'] = os.getenv("EMAIL_ADDRESS")
    msg['To'] = os.getenv("EMAIL_ADDRESS")
    msg['Subject'] = 'Raport zakupu AI tokenów'
    msg.attach(MIMEText(body, 'plain'))

    if attachment_paths:
        for path in attachment_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    attach = MIMEApplication(f.read(), _subtype=os.path.splitext(path)[-1][1:])
                    attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(path))
                    msg.attach(attach)

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
rows = []
details = []
date_str = datetime.now().strftime("%Y-%m-%d")
log_entries = []

for name, slug in tokens.items():
    try:
        df = load_data(slug)
        rsi = compute_rsi(df['price'])
        macd, signal = compute_macd(df['price'])
        ema_s, ema_l = compute_ema(df['price'])
        price = df['price'].iloc[-1]

        rsi_val = rsi.iloc[-1]
        macd_val = macd.iloc[-1]
        signal_val = signal.iloc[-1]
        ema_s_val = ema_s.iloc[-1]
        ema_l_val = ema_l.iloc[-1]

        conf = compute_confidence(rsi_val, macd_val, signal_val, price, ema_s_val, ema_l_val)
        decision = "TAK" if conf >= 66 else "MOZE" if conf >= 33 else "NIE"

        line = f"{name}: {decision} (RSI={rsi_val:.1f}, MACD={macd_val:.4f}, SIGNAL={signal_val:.4f}, EMA_S={ema_s_val:.2f}, EMA_L={ema_l_val:.2f}, Conf={conf}%)"
        summary.append(line)
        rows.append((name, f"{decision} ({conf}%)"))

        if decision != "NIE":
            log_entries.append([date_str, name, decision, conf, rsi_val, macd_val, signal_val, ema_s_val, ema_l_val, price])

    except Exception as e:
        error_msg = f"{name}: Blad: {str(e)}"
        summary.append(error_msg)
        rows.append((name, error_msg))

# Zapisz log do CSV jesli byly pozytywne sygnaly
csv_path = None
if log_entries:
    df_log = pd.DataFrame(log_entries, columns=["Data", "Token", "Decyzja", "Confidence", "RSI", "MACD", "SIGNAL", "EMA_S", "EMA_L", "Cena"])
    csv_path = f"crypto_log_{date_str}.csv"
    df_log.to_csv(csv_path, index=False)

# PDF + Email
pdf_path = generate_pdf(rows)
full_text = "\n".join(summary)

attachment_paths = [pdf_path]
if csv_path:
    attachment_paths.append(csv_path)

send_email(body=full_text, attachment_paths=attachment_paths)


# --- Wyślij tylko jeśli jest sygnał kupna ---
# pos = [line for line in summary if "TAK" in line]
# if pos:
#     pdf_path = generate_pdf(rows)
#     send_email("\n".join(pos), attachment_path=pdf_path)

# --- WYŚLIJ ZAWSZE (TEST) ---
#pdf_path = generate_pdf(rows)
#send_email("To jest testowy e-mail z GitHub Actions. Skrypt działa prawidłowo.", attachment_path=pdf_path)
