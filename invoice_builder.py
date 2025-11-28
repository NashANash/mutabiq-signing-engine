import xml.etree.ElementTree as ET

VAT_RATE = 0.15

# نحاول نحول أي قيمة لرقم
def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def build_invoice_xml(data):
    """
    تبني فاتورة UBL 2.1 مبسّطة من JSON
    المدخل المتوقع (أمثلة مفيدة):
    {
      "InvoiceNumber": "INV-1001",
      "IssueDate": "2025-11-27",
      "SellerName": "Mutabiq",
      "SellerVAT": "300000000000003",
      "BuyerName": "Test Client",
      "BuyerVAT": "300000000000004",
      "Currency": "SAR",
      "Subtotal": "100",   (اختياري)
      "Total": "115",      (اختياري)
      "VAT": "15"          (اختياري)
    }
    """

    # نقرأ القيم الرقمية
    subtotal_in = _to_float(data.get("Subtotal"))
    total_in = _to_float(data.get("Total"))
    vat_in = _to_float(data.get("VAT"))

    subtotal = subtotal_in
    vat = vat_in
    total = total_in

    # 1) لو عندك Subtotal فقط
    if subtotal and not total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    # 2) لو عندك Total فقط
    elif total and not subtotal:
        subtotal = round(total / (1 + VAT_RATE), 2)
        vat = round(total - subtotal, 2)

    # 3) لو عندك الاثنين Subtotal + Total
    elif subtotal and total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    # 4) لو ما فيه شيء مفهوم
    else:
        subtotal = 0.0
        vat = 0.0
        total = 0.0

    currency = data.get("Currency", "SAR") or "SAR"

    # namespaces حق UBL
    NSMAP = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }

    for prefix, uri in NSMAP.items():
        if prefix == "":
            ET.register_namespace("", uri)
        else:
            ET.register_namespace(prefix, uri)

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

    # Currency
    cbc_doc_currency = ET.SubElement(root, qname("cbc", "DocumentCurrencyCode"))
    cbc_doc_currency.text = currency

    # البائع: AccountingSupplierParty
    cac_supplier = ET.SubElement(root, qname("cac", "AccountingSupplierParty"))
    cac_supplier_party = ET.SubElement(cac_supplier, qname("cac", "Party"))

    seller_name = ET.SubElement(cac_supplier_party, qname("cbc", "Name"))
    seller_name.text = str(data.get("SellerName", ""))

    seller_tax_scheme = ET.SubElement(
        cac_supplier_party,
        qname("cac", "PartyTaxScheme")
    )
    seller_vat_number = ET.SubElement(seller_tax_scheme, qname("cbc", "CompanyID"))
    seller_vat_number.text = str(data.get("SellerVAT", ""))

    # المشتري: AccountingCustomerParty
    cac_customer = ET.SubElement(root, qname("cac", "AccountingCustomerParty"))
    cac_customer_party = ET.SubElement(cac_customer, qname("cac", "Party"))

    buyer_name = ET.SubElement(cac_customer_party, qname("cbc", "Name"))
    buyer_name.text = str(data.get("BuyerName", ""))

    buyer_tax_scheme = ET.SubElement(
        cac_customer_party,
        qname("cac", "PartyTaxScheme")
    )
    buyer_vat_number = ET.SubElement(buyer_tax_scheme, qname("cbc", "CompanyID"))
    buyer_vat_number.text = str(data.get("BuyerVAT", ""))

    # TaxTotal (إجمالي الضريبة)
    cac_tax_total = ET.SubElement(root, qname("cac", "TaxTotal"))
    tax_amount = ET.SubElement(cac_tax_total, qname("cbc", "TaxAmount"))
    tax_amount.set("currencyID", currency)
    tax_amount.text = f"{vat:.2f}"

    # LegalMonetaryTotal (المجاميع النهائية)
    cac_legal_total = ET.SubElement(root, qname("cac", "LegalMonetaryTotal"))

    line_extension = ET.SubElement(cac_legal_total, qname("cbc", "LineExtensionAmount"))
    line_extension.set("currencyID", currency)
    line_extension.text = f"{subtotal:.2f}"

    tax_exclusive = ET.SubElement(cac_legal_total, qname("cbc", "TaxExclusiveAmount"))
    tax_exclusive.set("currencyID", currency)
    tax_exclusive.text = f"{subtotal:.2f}"

    tax_inclusive = ET.SubElement(cac_legal_total, qname("cbc", "TaxInclusiveAmount"))
    tax_inclusive.set("currencyID", currency)
    tax_inclusive.text = f"{total:.2f}"

    payable_amount = ET.SubElement(cac_legal_total, qname("cbc", "PayableAmount"))
    payable_amount.set("currencyID", currency)
    payable_amount.text = f"{total:.2f}"

    return ET.tostring(root, encoding="utf-8").decode()
