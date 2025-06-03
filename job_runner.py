from your_analysis_module import analyze_tokens, tokens  # lub wklej funkcje tu
from fpdf import FPDF
import pandas as pd

def generate_pdf(results, filename="report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Raport AI Tokenów", ln=True, align="C")
    pdf.ln(10)
    for token, data in results.items():
        pdf.cell(200, 10, txt=f"{token} - {data['Ocena zakupu']}", ln=True)
    pdf.output(filename)

def main():
    results = analyze_tokens(tokens)
    generate_pdf(results)
    pd.DataFrame(results).T.to_csv("report.csv")
    print("Raport został wygenerowany.")

if __name__ == "__main__":
    main()
