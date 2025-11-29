import xml.etree.ElementTree as ET

VAT_RATE = 0.15

# يحول أي قيمة رقمية بشكل آمن
def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def build_invoice_xml(data):
    """
    يبني فاتورة UBL 2.1 من JSON — الإصدار الأساسي (B)
    """

    # قراءة القيم الرقمية
    subtotal_in = _to_float(data.get("Subtotal"))
    total_in = _to_float(data.get("Total"))
    vat_in = _to_float(data.get("VAT"))

    subtotal = subtotal_in
    vat = vat_in
    total = total_in

    # 1) لو فقط Subtotal
    if subtotal and not total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    # 2) لو فقط Total
    elif total and not subtotal:
        subtotal = round(total / (1 + VAT_RATE), 2)
        vat = round(total - subtotal, 2)

    # 3) لو موجودين مع بعض
    elif subtotal and total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    else:
        subtotal = 0.0
        vat = 0.0
        total = 0.0

    currency = data.get("Currency", "SAR") or "SAR"

    # namespaces الخاصة بـ UBL
    NSMAP = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }

    for prefix, uri in NSMAP.items():
        ET.register_namespace(prefix if prefix != "" else "", uri)

    def qname(prefix, tag):
        if prefix == "":
            return f"{{{NSMAP['']}}}{tag}"
        return f"{{{NSMAP[prefix]}}}{tag}"

    # الجذر: Invoice
    root = ET.Element(qname("", "Invoice"))

    # ID + IssueDate
    cbc_id = ET.SubElement(root, qname("cbc", "ID"))
    cbc_id.text = str(data.get("InvoiceNumber", ""))

    cbc_issue_date = ET.SubElement(root, qname("cbc", "IssueDate"))
    cbc_issue_date.text = str(data.get("IssueDate", ""))

    # DocumentCurrencyCode
    cbc_currency = ET.SubElement(root, qname("cbc", "DocumentCurrencyCode"))
    cbc_currency.text = currency

    # Seller
    cac_supplier = ET.SubElement(root, qname("cac", "AccountingSupplierParty"))
    supplier_party = ET.SubElement(cac_supplier, qname("cac", "Party"))

    seller_name = ET.SubElement(supplier_party, qname("cbc", "Name"))
    seller_name.text = str(data.get("SellerName", ""))

    supplier_tax = ET.SubElement(supplier_party, qname("cac", "PartyTaxScheme"))
    seller_vat = ET.SubElement(supplier_tax, qname("cbc", "CompanyID"))
    seller_vat.text = str(data.get("SellerVAT", ""))

    # Buyer
    cac_customer = ET.SubElement(root, qname("cac", "AccountingCustomerParty"))
    customer_party = ET.SubElement(cac_customer, qname("cac", "Party"))

    buyer_name = ET.SubElement(customer_party, qname("cbc", "Name"))
    buyer_name.text = str(data.get("BuyerName", ""))

    buyer_tax = ET.SubElement(customer_party, qname("cac", "PartyTaxScheme"))
    buyer_vat = ET.SubElement(buyer_tax, qname("cbc", "CompanyID"))
    buyer_vat.text = str(data.get("BuyerVAT", ""))

    # TaxTotal
    cac_tax_total = ET.SubElement(root, qname("cac", "TaxTotal"))
    tax_amount = ET.SubElement(cac_tax_total, qname("cbc", "TaxAmount"))
    tax_amount.set("currencyID", currency)
    tax_amount.text = f"{vat:.2f}"

    # LegalMonetaryTotal
    cac_legal = ET.SubElement(root, qname("cac", "LegalMonetaryTotal"))

    line_ext = ET.SubElement(cac_legal, qname("cbc", "LineExtensionAmount"))
    line_ext.set("currencyID", currency)
    line_ext.text = f"{subtotal:.2f}"

    tax_excl = ET.SubElement(cac_legal, qname("cbc", "TaxExclusiveAmount"))
    tax_excl.set("currencyID", currency)
    tax_excl.text = f"{subtotal:.2f}"

    tax_incl = ET.SubElement(cac_legal, qname("cbc", "TaxInclusiveAmount"))
    tax_incl.set("currencyID", currency)
    tax_incl.text = f"{total:.2f}"

    payable = ET.SubElement(cac_legal, qname("cbc", "PayableAmount"))
    payable.set("currencyID", currency)
    payable.text = f"{total:.2f}"

    return ET.tostring(root, encoding="utf-8").decode()
