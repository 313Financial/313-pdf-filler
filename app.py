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
# ── DIP Certificate Generator ──────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, Frame, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from datetime import datetime

def _dip_ordinal(n):
    if 11 <= n % 100 <= 13:
        return "th"
    return {1:"st",2:"nd",3:"rd"}.get(n % 10, "th")

def _dip_today():
    d = datetime.today()
    return f"{d.day}{_dip_ordinal(d.day)} {d.strftime('%B %Y')}"

def build_dip_pdf(customer_names, company_name, loan_amount, adviser_name, adviser_email, adviser_phone):
    ORANGE = rl_colors.HexColor("#E8770A")
    BLACK  = rl_colors.HexColor("#1A1A1A")
    PW, PH = A4
    ML = 20*mm; MR = 20*mm; CW = PW - ML - MR

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Agreement in Principle Certificate - 313 Commercial")

    cx = PW/2
    cy = PH - 22*mm
    c.setStrokeColor(rl_colors.HexColor("#C0C0C0"))
    c.setLineWidth(1.5)
    c.circle(cx - 28*mm, cy, 12*mm, stroke=1, fill=0)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(cx - 28*mm, cy - 2.5*mm, "313")
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(cx - 13*mm, cy - 2.5*mm, "COMMERCIAL")

    bt = PH - 38*mm; bh = 26*mm
    c.setFillColor(ORANGE)
    c.rect(0, bt - bh, PW, bh, fill=1, stroke=0)
    c.setFillColor(rl_colors.white)
    c.setFont("Helvetica-BoldOblique", 12)
    c.drawCentredString(PW/2, bt - 9*mm, "Agreement in Principle")
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(PW/2, bt - 22*mm, "CERTIFICATE")

    bb = bt - bh
    ft = bb - 5*mm
    fh = ft - 18*mm

    def p(text, bold=False):
        return Paragraph(text, ParagraphStyle("s", fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=9.5, leading=14, textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=4))
    def sp():
        return Paragraph("&nbsp;", ParagraphStyle("sp", fontSize=4, leading=6))
    def bullet(text):
        return Paragraph(f"• {text}", ParagraphStyle("b", fontName="Helvetica",
            fontSize=9.5, leading=14, textColor=BLACK, leftIndent=10, firstLineIndent=-10, spaceAfter=4))

    story = [
        p("Following our discussion, we are pleased to provide you with a 313 Commercial Agreement in Principle, which will help you when it comes to proceeding with an offer on a property."),
        sp(),
        p("<b>Decision details:</b>"),
        p(f"This is a certificate to confirm that based on the information you have given; you are able to borrow <b>{loan_amount}</b>."),
        p("We have checked your details, including income and credit file and we can confirm that a decision in principle will be <b>ACCEPTED</b>. A full application will be submitted once an offer for a property has been accepted."),
        sp(),
    ]

    lbl = ParagraphStyle("lbl", fontName="Helvetica-Bold", fontSize=9.5, leading=15, textColor=BLACK)
    val = ParagraphStyle("val", fontName="Helvetica", fontSize=9.5, leading=15, textColor=BLACK)
    tbl = Table([
        [Paragraph("Customer Name(s):", lbl), Paragraph(customer_names, val)],
        [Paragraph("Company Name:",     lbl), Paragraph(company_name,   val)],
        [Paragraph("Decision Date:",    lbl), Paragraph(_dip_today(),   val)],
        [Paragraph("Your Adviser:",     lbl), Paragraph(adviser_name,   val)],
    ], colWidths=[44*mm, CW - 44*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1),
    ]))
    story += [tbl, sp(),
        p("Please note that this does not represent a formal mortgage offer or guarantee of a mortgage as the underwriter has not completed their final checks with your case."),
        sp(), p("<b>How to Proceed:</b>"),
        bullet("At 313 Commercial we advocate responsible borrowing - if your circumstances change in the meantime or if you wish to discuss your options further please do not hesitate to contact me."),
        bullet("I am more than happy to speak to your estate agent if required when you are making an offer - please feel free to pass on my contact details."),
        sp(),
        p("Finally, I wish you good luck with the property search and we will look forward to speaking to you once your offer is accepted. However, if you have any questions in the meantime please do not hesitate to call."),
        sp(),
    ]
    so = ParagraphStyle("so", fontName="Helvetica-Bold", fontSize=9.5, leading=15, textColor=BLACK)
    story += [Paragraph(adviser_email, so), Paragraph("Mortgage Adviser", so), Paragraph(adviser_phone, so)]

    Frame(ML, PH - ft - fh, CW, fh, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0).addFromList(story, c)

    c.setStrokeColor(ORANGE); c.setLineWidth(1)
    c.line(ML, 14*mm, PW - MR, 14*mm)
    c.setFont("Helvetica", 7.5); c.setFillColor(rl_colors.HexColor("#888888"))
    c.drawCentredString(PW/2, 9*mm, "313 Commercial Ltd  |  www.313commercial.co.uk  |  FCA Authorised")
    c.save(); buf.seek(0)
    return buf.read()

@app.route("/generate-dip", methods=["POST"])
def generate_dip():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    customer_names = data.get("customer_names", "").strip()
    loan_amount    = data.get("loan_amount", "").strip()
    if not customer_names or not loan_amount:
        return jsonify({"error": "customer_names and loan_amount are required"}), 400
    pdf_bytes = build_dip_pdf(
        customer_names=customer_names,
        company_name=data.get("company_name", "N/A").strip(),
        loan_amount=loan_amount,
        adviser_name=data.get("adviser_name", "Paul Gray").strip(),
        adviser_email=data.get("adviser_email", "paul@313group.co.uk").strip(),
        adviser_phone=data.get("adviser_phone", "0191 228 6969").strip(),
    )
    return jsonify({"pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")})
