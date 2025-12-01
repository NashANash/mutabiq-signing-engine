import xml.etree.ElementTree as ET
import base64
import uuid

VAT_RATE = 0.15  # 15%

def _to_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except:
        return default

# ------------------------------------------------------
# E-1: بناء TLV حسب متطلبات ZATCA
# ------------------------------------------------------
def _tlv(tag, value):
    encoded = value.encode('utf-8')
    return bytes([tag, len(encoded)]) + encoded

def generate_qr(seller_name, seller_vat, issue_date, total, vat_total):
    tlv_bytes = b""
    tlv_bytes += _tlv(1, seller_name)
    tlv_bytes += _tlv(2, seller_vat)
    tlv_bytes += _tlv(3, issue_date)
    tlv_bytes += _tlv(4, str(total))
    tlv_bytes += _tlv(5, str(vat_total))
    return base64.b64encode(tlv_bytes).decode()
# ------------------------------------------------------


def build_invoice_xml(data):
    currency = data.get("Currency", "SAR") or "SAR"

    # ========= حساب المجاميع =========
    items = data.get("Items", [])
    has_items = isinstance(items, list) and len(items) > 0

    subtotal = 0.0
    vat_total = 0.0

    if has_items:
        for item in items:
            qty = _to_float(item.get("Quantity"), 1)
            price = _to_float(item.get("UnitPrice"), 0)
            rate_percent = _to_float(item.get("VATRate"), 15)
            rate = rate_percent / 100

            line_sub = qty * price
            line_vat = round(line_sub * rate, 2)

            subtotal += line_sub
            vat_total += line_vat

        total = round(subtotal + vat_total, 2)

    else:
        subtotal = _to_float(data.get("Subtotal"))
        total = _to_float(data.get("Total"))
        vat_total = _to_float(data.get("VAT"))

        if subtotal and not total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = subtotal + vat_total
        elif total and not subtotal:
            subtotal = round(total / 1.15, 2)
            vat_total = total - subtotal
        elif subtotal and total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = subtotal + vat_total
        else:
            subtotal = vat_total = total = 0.0

    # ========= UBL Namespaces =========
    NSMAP = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }
    for p, u in NSMAP.items():
        ET.register_namespace(p, u)

    def q(prefix, tag):
        return f"{{{NSMAP[prefix]}}}{tag}"

    # ========= الجذر =========
    root = ET.Element(q("", "Invoice"))

    ET.SubElement(root, q("cbc", "ProfileID")).text = "reporting:1.0"
    ET.SubElement(root, q("cbc", "ID")).text = str(data.get("InvoiceNumber"))
    ET.SubElement(root, q("cbc", "UUID")).text = str(data.get("UUID", str(uuid.uuid4())))
    ET.SubElement(root, q("cbc", "IssueDate")).text = str(data.get("IssueDate"))
    ET.SubElement(root, q("cbc", "DocumentCurrencyCode")).text = currency

    # ========= Seller =========
    cac_supplier = ET.SubElement(root, q("cac", "AccountingSupplierParty"))
    party = ET.SubElement(cac_supplier, q("cac", "Party"))
    ET.SubElement(party, q("cbc", "Name")).text = data.get("SellerName", "")
    tax_scheme = ET.SubElement(party, q("cac", "PartyTaxScheme"))
    ET.SubElement(tax_scheme, q("cbc", "CompanyID")).text = data.get("SellerVAT", "")

    # ========= Buyer =========
    cac_customer = ET.SubElement(root, q("cac", "AccountingCustomerParty"))
    party2 = ET.SubElement(cac_customer, q("cac", "Party"))
    ET.SubElement(party2, q("cbc", "Name")).text = data.get("BuyerName", "")
    tax_scheme2 = ET.SubElement(party2, q("cac", "PartyTaxScheme"))
    ET.SubElement(tax_scheme2, q("cbc", "CompanyID")).text = data.get("BuyerVAT", "")

    # ========= Line Items =========
    if has_items:
        index = 1
        for item in items:
            qty = _to_float(item.get("Quantity"))
            price = _to_float(item.get("UnitPrice"))
            rate = _to_float(item.get("VATRate"), 15) / 100

            line_sub = qty * price
            line_vat = round(line_sub * rate, 2)

            line = ET.SubElement(root, q("cac", "InvoiceLine"))
            ET.SubElement(line, q("cbc", "ID")).text = str(index)
            ET.SubElement(line, q("cbc", "InvoicedQuantity")).text = f"{qty:.2f}"

            amount = ET.SubElement(line, q("cbc", "LineExtensionAmount"))
            amount.set("currencyID", currency)
            amount.text = f"{line_sub:.2f}"

            # Item name
            item_el = ET.SubElement(line, q("cac", "Item"))
            ET.SubElement(item_el, q("cbc", "Name")).text = item.get("Description", "")

            # Price
            price_el = ET.SubElement(line, q("cac", "Price"))
            price_amount = ET.SubElement(price_el, q("cbc", "PriceAmount"))
            price_amount.set("currencyID", currency)
            price_amount.text = f"{price:.2f}"

            # Tax per line
            tax_total = ET.SubElement(line, q("cac", "TaxTotal"))
            tax_amt = ET.SubElement(tax_total, q("cbc", "TaxAmount"))
            tax_amt.set("currencyID", currency)
            tax_amt.text = f"{line_vat:.2f}"

            tax_sub = ET.SubElement(tax_total, q("cac", "TaxSubtotal"))
            taxable = ET.SubElement(tax_sub, q("cbc", "TaxableAmount"))
            taxable.set("currencyID", currency)
            taxable.text = f"{line_sub:.2f}"

            tax_amt2 = ET.SubElement(tax_sub, q("cbc", "TaxAmount"))
            tax_amt2.set("currencyID", currency)
            tax_amt2.text = f"{line_vat:.2f}"

            cat = ET.SubElement(tax_sub, q("cac", "TaxCategory"))
            ET.SubElement(cat, q("cbc", "Percent")).text = "15"
            scheme = ET.SubElement(cat, q("cac", "TaxScheme"))
            ET.SubElement(scheme, q("cbc", "ID")).text = "VAT"

            index += 1

    # ========= TaxTotal + Totals =========
    tax_total_main = ET.SubElement(root, q("cac", "TaxTotal"))
    amt_main = ET.SubElement(tax_total_main, q("cbc", "TaxAmount"))
    amt_main.set("currencyID", currency)
    amt_main.text = f"{vat_total:.2f}"

    legal = ET.SubElement(root, q("cac", "LegalMonetaryTotal"))
    a = ET.SubElement(legal, q("cbc", "LineExtensionAmount"))
    a.set("currencyID", currency)
    a.text = f"{subtotal:.2f}"

    b = ET.SubElement(legal, q("cbc", "TaxExclusiveAmount"))
    b.set("currencyID", currency)
    b.text = f"{subtotal:.2f}"

    c = ET.SubElement(legal, q("cbc", "TaxInclusiveAmount"))
    c.set("currencyID", currency)
    c.text = f"{total:.2f}"

    d = ET.SubElement(legal, q("cbc", "PayableAmount"))
    d.set("currencyID", currency)
    d.text = f"{total:.2f}"

    # ========= QR Code =========
    qr_value = generate_qr(
        seller_name=data.get("SellerName", ""),
        seller_vat=data.get("SellerVAT", ""),
        issue_date=data.get("IssueDate", ""),
        total=str(total),
        vat_total=str(vat_total)
    )

    qr_el = ET.SubElement(root, q("cbc", "EmbeddedDocumentBinaryObject"))
    qr_el.set("mimeCode", "text/plain")
    qr_el.text = qr_value

    return ET.tostring(root, encoding="utf-8").decode()
