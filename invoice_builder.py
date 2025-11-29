import xml.etree.ElementTree as ET
import uuid

VAT_RATE = 0.15

def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default


def build_invoice_xml(data):

    # ===== 1) PROFILE ID (UBL Profile) =====
    PROFILE_ID = "reporting:1.0"

    # ===== 2) UUID =====
    INVOICE_UUID = str(uuid.uuid4())

    # ===== 3) قراءة القيم =====
    subtotal_in = _to_float(data.get("Subtotal"))
    total_in = _to_float(data.get("Total"))
    vat_in = _to_float(data.get("VAT"))

    subtotal = subtotal_in
    vat = vat_in
    total = total_in

    if subtotal and not total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    elif total and not subtotal:
        subtotal = round(total / (1 + VAT_RATE), 2)
        vat = round(total - subtotal, 2)

    elif subtotal and total:
        vat = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

    else:
        subtotal = 0.0
        vat = 0.0
        total = 0.0

    currency = data.get("Currency", "SAR") or "SAR"

    # ===== 4) Namespaces =====
    NSMAP = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }

    for prefix, uri in NSMAP.items():
        ET.register_namespace(prefix if prefix != "" else "", uri)

    def q(prefix, tag):
        if prefix == "":
            return f"{{{NSMAP['']}}}{tag}"
        return f"{{{NSMAP[prefix]}}}{tag}"

    # ===== 5) ROOT =====
    root = ET.Element(q("", "Invoice"))

    # Profile ID
    profile_id = ET.SubElement(root, q("cbc", "ProfileID"))
    profile_id.text = PROFILE_ID

    # ID
    cbc_id = ET.SubElement(root, q("cbc", "ID"))
    cbc_id.text = str(data.get("InvoiceNumber", ""))

    # UUID
    cbc_uuid = ET.SubElement(root, q("cbc", "UUID"))
    cbc_uuid.text = INVOICE_UUID

    # IssueDate
    issue_date = ET.SubElement(root, q("cbc", "IssueDate"))
    issue_date.text = str(data.get("IssueDate", ""))

    # Currency
    currency_code = ET.SubElement(root, q("cbc", "DocumentCurrencyCode"))
    currency_code.text = currency

    # ===== 6) SUPPLIER =====
    supplier = ET.SubElement(root, q("cac", "AccountingSupplierParty"))
    supplier_party = ET.SubElement(supplier, q("cac", "Party"))

    seller_name = ET.SubElement(supplier_party, q("cbc", "Name"))
    seller_name.text = str(data.get("SellerName", ""))

    supplier_tax = ET.SubElement(supplier_party, q("cac", "PartyTaxScheme"))
    seller_vat = ET.SubElement(supplier_tax, q("cbc", "CompanyID"))
    seller_vat.text = str(data.get("SellerVAT", ""))

    # ===== 7) CUSTOMER =====
    customer = ET.SubElement(root, q("cac", "AccountingCustomerParty"))
    customer_party = ET.SubElement(customer, q("cac", "Party"))

    buyer_name = ET.SubElement(customer_party, q("cbc", "Name"))
    buyer_name.text = str(data.get("BuyerName", ""))

    buyer_tax = ET.SubElement(customer_party, q("cac", "PartyTaxScheme"))
    buyer_vat = ET.SubElement(buyer_tax, q("cbc", "CompanyID"))
    buyer_vat.text = str(data.get("BuyerVAT", ""))

    # ===== 8) TAX TOTAL =====
    tax_total = ET.SubElement(root, q("cac", "TaxTotal"))
    tax_amount = ET.SubElement(tax_total, q("cbc", "TaxAmount"))
    tax_amount.set("currencyID", currency)
    tax_amount.text = f"{vat:.2f}"

    # ===== 9) LEGAL MONETARY TOTAL =====
    legal = ET.SubElement(root, q("cac", "LegalMonetaryTotal"))

    line_ext = ET.SubElement(legal, q("cbc", "LineExtensionAmount"))
    line_ext.set("currencyID", currency)
    line_ext.text = f"{subtotal:.2f}"

    tax_excl = ET.SubElement(legal, q("cbc", "TaxExclusiveAmount"))
    tax_excl.set("currencyID", currency)
    tax_excl.text = f"{subtotal:.2f}"

    tax_incl = ET.SubElement(legal, q("cbc", "TaxInclusiveAmount"))
    tax_incl.set("currencyID", currency)
    tax_incl.text = f"{total:.2f}"

    payable = ET.SubElement(legal, q("cbc", "PayableAmount"))
    payable.set("currencyID", currency)
    payable.text = f"{total:.2f}"

    return ET.tostring(root, encoding="utf-8").decode()
