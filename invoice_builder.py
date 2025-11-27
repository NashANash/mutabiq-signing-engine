import xml.etree.ElementTree as ET

VAT_RATE = 0.15

def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def build_invoice_xml(data):
    # نحول القيم الرقمية
    subtotal_in = _to_float(data.get("Subtotal"))
    total_in = _to_float(data.get("Total"))
    vat_in = _to_float(data.get("VAT"))

    subtotal = subtotal_in
    vat = vat_in
    total = total_in

    # حالة: إذا عندك Subtotal فقط
    if subtotal and not total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    # حالة: Total فقط
    elif total and not subtotal:
        subtotal = round(total / (1 + VAT_RATE), 2)
        vat = round(total - subtotal, 2)

    # حالة: Subtotal + Total
    elif subtotal and total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    # ولا شيء
    else:
        subtotal = 0.0
        vat = 0.0
        total = 0.0

    root = ET.Element("Invoice")

    ET.SubElement(root, "InvoiceNumber").text = str(data.get("InvoiceNumber", ""))
    ET.SubElement(root, "IssueDate").text = str(data.get("IssueDate", ""))

    seller = ET.SubElement(root, "Seller")
    ET.SubElement(seller, "Name").text = str(data.get("SellerName", ""))
    ET.SubElement(seller, "VATNumber").text = str(data.get("SellerVAT", ""))

    buyer = ET.SubElement(root, "Buyer")
    ET.SubElement(buyer, "Name").text = str(data.get("BuyerName", ""))
    ET.SubElement(buyer, "VATNumber").text = str(data.get("BuyerVAT", ""))

    totals = ET.SubElement(root, "Totals")
    ET.SubElement(totals, "Subtotal").text = f"{subtotal:.2f}"
    ET.SubElement(totals, "VAT").text = f"{vat:.2f}"
    ET.SubElement(totals, "Total").text = f"{total:.2f}"

    return ET.tostring(root, encoding="utf-8").decode()
