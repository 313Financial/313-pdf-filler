import base64
import io
import os
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "form_template.pdf")

# Mapping from Claude JSON keys to PDF field IDs
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

# Checkboxes to tick based on field values
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

    reader = PdfReader(TEMPLATE_PATH)
    writer = PdfWriter()
    writer.append(reader)

    # Build field values dict
    fields = {}
    for json_key, pdf_field in FIELD_MAP.items():
        value = data.get(json_key, "")
        if value:
            fields[pdf_field] = value

    # Tick checkboxes where the corresponding field has a value
    for json_key, checkbox_field in CHECKBOX_MAP.items():
        if data.get(json_key, ""):
            fields[checkbox_field] = "/Yes"

    writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    pdf_b64 = base64.b64encode(buf.read()).decode("utf-8")

    borrower = data.get("borrower_name", "Unknown")
    return jsonify({
        "pdf_base64": pdf_b64,
        "filename": f"Together_Concierge_{borrower.replace(' ', '_')}.pdf"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
