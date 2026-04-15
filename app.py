import base64
import io
import os
import re
import requests
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter
from docx import Document
from datetime import date
import zipfile

app = Flask(__name__)

CONCIERGE_TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/Concierge%20Form%20May%2025%20v2%20editable.pdf"
DIP_TEMPLATE_URL = "https://raw.githubusercontent.com/313Financial/313-pdf-filler/main/DIP_CERT_TEMPLATE.docx"

FIELD_MAP = {
    "borrower_name":        "Borrower name",
    "rate_product":         "Rate / product",
    "use_of_funds":         "Use of funds",
    "charge_type":          "charge type",
    "security_address":     "Sales particulars",
    "serviced_or_retained": "Serviced or retained",
    "dual_rep":             "Dual rep",
    "sols_email":           "Sols email",
    "exit_strategy":        "Exit strategy",
    "gross_loan":           "gross loan",
    "net_loan":             "net loan",
    "loan_term":            "Term",
    "broker_fee":           "Broker fee",
}

CHECKBOX_MAP = {
    "rate_product":         "Rate",
    "use_of_funds":         "Use",
    "charge_type":          "Charge",
    "serviced_or_retained": "Serviced",
    "sols_email":           "Sol email",
}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/fill-pdf", methods=["POST"])
def fill_pdf():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON body"}), 400

        response = requests.get(CONCIERGE_TEMPLATE_URL, timeout=30)
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
                fields[pdf_field] = str(value)

        for json_key, checkbox_field in CHECKBOX_MAP.items():
            if data.get(json_key, ""):
                fields[checkbox_field] = "/Yes"

        writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)

        buf = io.BytesIO()
        writer.write(buf)
        pdf_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        borrower = data.get("borrower_name", "Unknown").replace(" ", "_")
        return jsonify({"pdf_base64": pdf_base64, "filename": f"Together_Concierge_{borrower}.pdf"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate-dip", methods=["POST"])
def generate_dip():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON body"}), 400

        replacements = {
            "{{CUSTOMER_NAMES}}": data.get("customer_names", ""),
            "{{COMPANY_NAME}}":   data.get("company_name", "N/A"),
            "{{LOAN_AMOUNT}}":    data.get("loan_amount", ""),
            "{{ADVISER_NAME}}":   data.get("adviser_name", "Paul Gray"),
            "{{ADVISER_EMAIL}}":  data.get("adviser_email", "paul@313group.co.uk"),
            "{{ADVISER_PHONE}}":  data.get("adviser_phone", "01912286969"),
            "{{DECISION_DATE}}":  date.today().strftime("%d/%m/%Y"),
        }

        response = requests.get(DIP_TEMPLATE_URL, timeout=30)
        if response.status_code != 200:
            return jsonify({"error": f"Failed to download DIP template: {response.status_code}"}), 500

        # Replace in raw XML to handle text boxes and split runs
        docx_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(docx_bytes), 'r') as zin:
            names = zin.namelist()
            files = {}
            for name in names:
                files[name] = zin.read(name)

        xml = files['word/document.xml'].decode('utf-8')
        for placeholder, value in replacements.items():
            xml = xml.replace(placeholder, value)
        files['word/document.xml'] = xml.encode('utf-8')

        out_buf = io.BytesIO()
        with zipfile.ZipFile(out_buf, 'w', zipfile.ZIP_DEFLATED) as zout:
            for name, content in files.items():
                zout.writestr(name, content)

        docx_base64 = base64.b64encode(out_buf.getvalue()).decode("utf-8")
        safe_name = data.get("customer_names", "Unknown").replace(" ", "_")
        return jsonify({"pdf_base64": docx_base64, "filename": f"DIP_Certificate_{safe_name}.docx"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
