import xml.etree.ElementTree as ET

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}

def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def _get_text(root, path: str) -> str:
    el = root.find(path, NS)
    if el is not None and el.text:
        return el.text.strip()
    return ""

def validate_invoice_xml(xml_str: str):
    """
    يفحص فاتورة UBL XML بعد البناء + بعد التوقيع.
    """

    errors = []
    warnings = []

    # -----------------------------
    # 1) Parse XML
    # -----------------------------
    try:
        root = ET.fromstring(xml_str)
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [f"XML parse error: {str(e)}"],
            "warnings": []
        }

    # -----------------------------
    # 2) التحقق من الحقول الأساسية
    # -----------------------------
    required_fields = {
        "ProfileID": ".//cbc:ProfileID",
        "Invoice ID": ".//cbc:ID",
        "UUID": ".//cbc:UUID",
        "IssueDate": ".//cbc:IssueDate",
        "DocumentCurrencyCode": ".//cbc:DocumentCurrencyCode"
    }

    for label, path in required_fields.items():
        if not _get_text(root, path):
            errors.append(f"Missing {label}.")

    # -----------------------------
    # 3) البائع Buyer / Seller
    # -----------------------------
    seller_name = _get_text(root, ".//cac:AccountingSupplierParty/cac:Party/cbc:Name")
    seller_vat = _get_text(root, ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID")

    buyer_name = _get_text(root, ".//cac:AccountingCustomerParty/cac:Party/cbc:Name")
    buyer_vat = _get_text(root, ".//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID")

    if not seller_name:
        errors.append("Missing seller name.")
    if not seller_vat:
        errors.append("Missing seller VAT (CompanyID).")
    if not buyer_name:
        errors.append("Missing buyer name.")
    if not buyer_vat:
        errors.append("Missing buyer VAT (CompanyID).")

    # -----------------------------
    # 4) المجاميع في الـ Header
    # -----------------------------
    tax_total_header = _to_float(_get_text(root, ".//cac:TaxTotal/cbc:TaxAmount"), 0.0)
    subtotal_header = _to_float(_get_text(root, ".//cac:LegalMonetaryTotal/cbc:LineExtensionAmount"), 0.0)
    tax_inclusive_header = _to_float(_get_text(root, ".//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"), 0.0)

    # -----------------------------
    # 5) قراءة سطور الفاتورة
    # -----------------------------
    lines = root.findall(".//cac:InvoiceLine", NS)

    sum_lines_subtotal = 0.0
    sum_lines_vat = 0.0

    for line in lines:
        line_sub = _to_float(_get_text(line, "./cbc:LineExtensionAmount"), 0.0)
        sum_lines_subtotal += line_sub

        line_vat = _to_float(
            _get_text(line, "./cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount"),
            0.0
        )
        sum_lines_vat += line_vat

    EPS = 0.01

    if lines:
        if abs(sum_lines_subtotal - subtotal_header) > EPS:
            errors.append(
                f"Header subtotal {subtotal_header} != sum of lines {sum_lines_subtotal}"
            )

        if abs(sum_lines_vat - tax_total_header) > EPS:
            errors.append(
                f"Header VAT {tax_total_header} != sum of lines VAT {sum_lines_vat}"
            )

        expected_total = round(sum_lines_subtotal + sum_lines_vat, 2)
        if abs(expected_total - tax_inclusive_header) > EPS:
            errors.append(
                f"Header TaxInclusive {tax_inclusive_header} != expected {expected_total}"
            )

    # -----------------------------
    # 6) QR موجود أو لا؟
    # -----------------------------
    qr_node = root.find(".//cbc:EmbeddedDocumentBinaryObject", NS)
    if qr_node is None or not (qr_node.text or "").strip():
        warnings.append("QR (EmbeddedDocumentBinaryObject) is missing or empty.")

    # -----------------------------
    # 7) الناتج
    # -----------------------------
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
