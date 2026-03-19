import base64, io, os, requests, zipfile
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter
from docx import Document
from datetime import datetime

app = Flask(__name__)

TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/Concierge%20Form%20May%202025%20v2%20editable.pdf"
DIP_TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/DIP_CERT_TEMPLATE.docx"

FIELD_MAP = {
    "borrower_name": "Borrower name", "rate_product": "Rate / product",
    "use_of_funds": "Use of funds", "charge_type": "charge type",
    "security_address": "Sales particulars", "serviced_or_retained": "Serviced or retained",
    "dual_rep": "Dual rep", "sols_email": "Sol email", "exit_strategy": "Exit strategy",
    "gross_loan": "gross loan", "net_loan": "net loan", "loan_term": "Term", "broker_fee": "Broker fee",
}
CHECKBOX_MAP = {
    "rate_product": "Rate", "use_of_funds": "Use", "charge_type": "Charge",
    "serviced_or_retained": "Serviced", "sols_email": "Sol email",
}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/fill-pdf", methods=["POST"])
def fill_pdf():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    response = requests.get(TEMPLATE_URL, timeout=30)
    if response.status_code != 200:
        return jsonify({"error": f"Template download failed: {response.status_code}"}), 500
    reader = PdfReader(io.BytesIO(response.content))
    writer = PdfWriter()
    writer.append(reader)
    fields = {}
    for key, label in FIELD_MAP.items():
        if key in data:
            fields[label] = data[key]
    for key, label in CHECKBOX_MAP.items():
        if key in data:
            fields[label] = data[key]
    writer.update_page_form_field_values(writer.pages[0], fields)
    out = io.BytesIO()
    writer.write(out)
    return jsonify({"pdf_base64": base64.b64encode(out.getvalue()).decode()})

def _ordinal(n):
    n = int(n)
    suffix = ["th","st","nd","rd","th","th","th","th","th","th"]
    return f"{n}{suffix[n % 10] if n % 10 < 4 and not (11 <= n % 100 <= 13) else 'th'}"

def _today():
    d = datetime.today()
    return f"{_ordinal(d.day)} {d.strftime('%B %Y')}"

def _replace_in_docx_bytes(docx_bytes, replacements):
    src = io.BytesIO(docx_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(src, 'r') as zin:
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith('.xml') or item.filename.endswith('.rels'):
                    text = data.decode('utf-8')
                    for key, val in replacements.items():
                        text = text.replace(key, val)
                    data = text.encode('utf-8')
                zout.writestr(item, data)
    return out.getvalue()

@app.route("/generate-dip", methods=["POST"])
def generate_dip():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    names = data.get("customer_names","").strip()
    amount = data.get("loan_amount","").strip()
    if not names or not amount:
        return jsonify({"error": "customer_names and loan_amount required"}), 400
    resp = requests.get(DIP_TEMPLATE_URL, timeout=30)
    if resp.status_code != 200:
        return jsonify({"error": f"Template download failed: {resp.status_code}"}), 500
    filled = _replace_in_docx_bytes(resp.content, {
        "{{CUSTOMER_NAMES}}": names,
        "{{COMPANY_NAME}}":   data.get("company_name","N/A").strip(),
        "{{LOAN_AMOUNT}}":    amount,
        "{{DECISION_DATE}}":  _today(),
        "{{ADVISER_NAME}}":   "Paul Gray",
        "{{ADVISER_EMAIL}}":  "paul@313group.co.uk",
        "{{ADVISER_PHONE}}":  "01912286969",
    })
    return jsonify({"pdf_base64": base64.b64encode(filled).decode()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
