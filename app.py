import base64, io, os, subprocess, tempfile, requests
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter
from docx import Document
from datetime import datetime

app = Flask(__name__)

TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/Concierge%20Form%20May%2025%20v2%20editable.pdf"
DIP_TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/DIP_CERT_TEMPLATE.docx"

FIELD_MAP = {
    "borrower_name": "Borrower name", "rate_product": "Rate / product",
    "use_of_funds": "Use of funds", "charge_type": "charge type",
    "security_address": "Sales particulars", "serviced_or_retained": "Serviced or retained",
    "dual_rep": "Dual rep", "sols_email": "Sols email", "exit_strategy": "Exit strategy",
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
        return jsonify({"error": f"Failed to download template: {response.status_code}"}), 500
    reader = PdfReader(io.BytesIO(response.content))
    writer = PdfWriter()
    writer.append(reader)
    fields = {pdf_field: data[json_key] for json_key, pdf_field in FIELD_MAP.items() if data.get(json_key)}
    for json_key, checkbox_field in CHECKBOX_MAP.items():
        if data.get(json_key):
            fields[checkbox_field] = "/Yes"
    writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)
    buf = io.BytesIO()
    writer.write(buf)
    borrower = data.get("borrower_name", "Unknown").replace(" ", "_")
    return jsonify({"pdf_base64": base64.b64encode(buf.getvalue()).decode(), "filename": f"Together_Concierge_{borrower}.pdf"})

def _ordinal(n):
    if 11 <= n % 100 <= 13: return "th"
    return {1:"st",2:"nd",3:"rd"}.get(n % 10, "th")

def _today():
    d = datetime.today()
    return f"{d.day}{_ordinal(d.day)} {d.strftime('%B %Y')}"

def _replace_in_docx(doc, replacements):
    from docx.oxml.ns import qn
    for t in doc.element.body.iter(qn('w:t')):
        for k, v in replacements.items():
            if k in (t.text or ''):
                t.text = t.text.replace(k, v)

def _to_pdf(docx_bytes):
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "in.docx")
        out = os.path.join(d, "in.pdf")
        open(src, "wb").write(docx_bytes)
        r = subprocess.run(["libreoffice","--headless","--convert-to","pdf","--outdir",d,src],
                           capture_output=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode())
        return open(out,"rb").read()

@app.route("/generate-dip", methods=["POST"])
def generate_dip():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    names  = data.get("customer_names","").strip()
    amount = data.get("loan_amount","").strip()
    if not names or not amount:
        return jsonify({"error": "customer_names and loan_amount required"}), 400
    resp = requests.get(DIP_TEMPLATE_URL, timeout=30)
    if resp.status_code != 200:
        return jsonify({"error": f"Template download failed: {resp.status_code}"}), 500
    doc = Document(io.BytesIO(resp.content))
    _replace_in_docx(doc, {
        "{{CUSTOMER_NAMES}}": names,
        "{{COMPANY_NAME}}":   data.get("company_name","N/A").strip(),
        "{{LOAN_AMOUNT}}":    amount,
        "{{DECISION_DATE}}":  _today(),
        "{{ADVISER_NAME}}":   "Paul Gray",
        "{{ADVISER_EMAIL}}":  "paul@313group.co.uk",
        "{{ADVISER_PHONE}}":  "01912286969",
    })
    buf = io.BytesIO()
    doc.save(buf)
    try:
        pdf = _to_pdf(buf.getvalue())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"pdf_base64": base64.b64encode(pdf).decode()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
