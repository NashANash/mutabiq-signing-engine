from fpdf import FPDF
import xml.etree.ElementTree as ET

def generate_pdf_from_xml(xml_content):
    try:
        root = ET.fromstring(xml_content)

        invoice_id = root.find(".//{*}ID").text if root.find(".//{*}ID") is not None else "N/A"
        issue_date = root.find(".//{*}IssueDate").text if root.find(".//{*}IssueDate") is not None else "N/A"
        seller = root.find(".//{*}AccountingSupplierParty//{*}Name").text if root.find(".//{*}AccountingSupplierParty//{*}Name") is not None else "N/A"
        buyer = root.find(".//{*}AccountingCustomerParty//{*}Name").text if root.find(".//{*}AccountingCustomerParty//{*}Name") is not None else "N/A"
        total = root.find(".//{*}PayableAmount").text if root.find(".//{*}PayableAmount") is not None else "0.00"

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)

        pdf.cell(200, 10, txt="Invoice Summary", ln=True, align='C')
        pdf.ln(5)

        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Invoice ID: {invoice_id}", ln=True)
        pdf.cell(200, 10, txt=f"Issue Date: {issue_date}", ln=True)
        pdf.cell(200, 10, txt=f"Seller: {seller}", ln=True)
        pdf.cell(200, 10, txt=f"Buyer: {buyer}", ln=True)
        pdf.cell(200, 10, txt=f"Total Amount: {total} SAR", ln=True)

        filename = "invoice.pdf"
        pdf.output(filename)

        return filename

    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")