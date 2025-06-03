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
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 14)

    def header(self):
        self.set_font("DejaVu", "", 14)
        self.cell(0, 10, "Raport Sygnałów Zakupu Tokenów AI", ln=True, align="C")
        self.ln(10)

    def summary_table(self, rows):
        self.set_font("DejaVu", "", 11)
        self.set_fill_color(220, 220, 220)
        self.cell(60, 10, "Token", 1, 0, "C", 1)
        self.cell(120, 10, "Ocena zakupu", 1, 1, "C", 1)
        for token, ocena in rows:
            if "🟢" in ocena:
                self.set_fill_color(180, 255, 180)
            elif "🟡" in ocena:
                self.set_fill_color(255, 240, 150)
            else:
                self.set_fill_color(255, 180, 180)
            self.cell(60, 10, token, 1, 0, "L", 1)
            self.cell(120, 10, ocena, 1, 1, "L", 1)

def generate_pdf(rows, filename="crypto_report.pdf"):
    pdf = PDFReport()
    pdf.add_page()
    pdf.summary_table(rows)
    path = os.path.join(os.getcwd(), filename)
    pdf.output(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF nie został zapisany: {path}")
    return path

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
def send_email(body, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = os.getenv("EMAIL_ADDRESS")
    msg['To'] = os.getenv("EMAIL_ADDRESS")
    msg['Subject'] = 'Sygnał zakupu AI tokenów'
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        print(f"➕ Załącznik PDF: {attachment_path}")
        if os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(attach)
        else:
            print(f"⚠️ Plik PDF nie istnieje: {attachment_path}")

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
for name, slug in tokens.items():
    try:
        df = load_data(slug)
        rsi = compute_rsi(df['price'])
        macd, signal = compute_macd(df['price'])
        ema_s, ema_l = compute_ema(df['price'])
        price = df['price'].iloc[-1]

        conf = compute_confidence(rsi.iloc[-1], macd.iloc[-1], signal.iloc[-1], price, ema_s.iloc[-1], ema_l.iloc[-1])
        decision = "TAK" if conf >= 66 else "MOŻE" if conf >= 33 else "NIE"

        line = f"{name}: {decision} (RSI={rsi.iloc[-1]:.1f}, Conf={conf}%)"
        summary.append(line)
        rows.append((name, line))
    except Exception as e:
        summary.append(f"{name}: Błąd: {str(e)}")
        rows.append((name, f"Błąd: {str(e)}"))

# --- Wyślij tylko jeśli jest sygnał kupna ---
#pos = [line for line in summary if "🟢" in line]
#if pos:
#    pdf_path = generate_pdf(rows)
#    send_email("\n".join(pos), attachment_path=pdf_path)

# --- WYŚLIJ ZAWSZE (TEST) ---
pdf_path = generate_pdf(rows)
send_email("✅ To jest testowy e-mail z GitHub Actions. Skrypt działa prawidłowo.")
