import base64
import io
import os
import requests
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)

TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/Concierge%20Form%20May%2025%20v2%20editable.pdf"

FIELD_MAP = {
    "borrower_name":       "Borrower name",
    "rate_product":        "Rate / product",
    "use_of_funds":        "Use of funds",
    "charge_type":         "charge type",
    "security_address":    "Sales particulars",
    "serviced_or_retained":"Serviced or retained",
    "dual_rep":            "Dual rep",
    "sols_email":          "Sols email",
    "exit_strategy":       "Exit strategy",
    "gross_loan":          "gross loan",
    "net_loan":            "net loan",
    "loan_term":           "Term",
    "broker_fee":          "Broker fee",
}

CHECKBOX_MAP = {
    "rate_product":        "Rate",
    "use_of_funds":        "Use",
    "charge_type":         "Charge",
    "serviced_or_retained":"Serviced",
    "sols_email":          "Sol email",
}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/fill-pdf", methods=["POST"])
def fill_pdf():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    # Download template from GitHub
    response = requests.get(TEMPLATE_URL, timeout=30)
    if response.status_code != 200:
        return jsonify({"error": f"Failed to download template: {response.status_code}"}), 500

    template_buf = io.BytesIO(response.content)
    reader = PdfReader(template_buf)
    writer = PdfWriter()
    writer.append(reader)

    fields = {}
    for json_key, pdf_field in FIELD_MAP.items():
        value = data.get(json_key, "")
        if value:
            fields[pdf_field] = value

    for json_key, checkbox_field in CHECKBOX_MAP.items():
        if data.get(json_key, ""):
            fields[checkbox_field] = "/Yes"

    writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)

    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    borrower = data.get("borrower_name", "Unknown").replace(" ", "_")
    filename = f"Together_Concierge_{borrower}.pdf"

    return jsonify({
        "pdf_base64": pdf_base64,
        "filename": filename
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
