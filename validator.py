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
    يفحص فاتورة UBL XML بسيطة ويرجع:
    {
      "is_valid": bool,
      "errors": [..],
      "warnings": [..]
    }
    """

    errors = []
    warnings = []

    # 1) Parse XML
    try:
        root = ET.fromstring(xml_str)
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [f"XML parse error: {str(e)}"],
            "warnings": [],
        }

    # 2) حقول أساسية (Header)
    profile_id = _get_text(root, ".//cbc:ProfileID")
    invoice_id = _get_text(root, ".//cbc:ID")
    uuid = _get_text(root, ".//cbc:UUID")
    issue_date = _get_text(root, ".//cbc:IssueDate")
    currency = _get_text(root, ".//cbc:DocumentCurrencyCode")

    if not profile_id:
        errors.append("Missing ProfileID.")
    if not invoice_id:
        errors.append("Missing Invoice ID (cbc:ID).")
    if not uuid:
        errors.append("Missing UUID (cbc:UUID).")
    if not issue_date:
        errors.append("Missing IssueDate.")
    if not currency:
        errors.append("Missing DocumentCurrencyCode.")

    # 3) بيانات البائع والمشتري
    seller_name = _get_text(
        root, ".//cac:AccountingSupplierParty/cac:Party/cbc:Name"
    )
    seller_vat = _get_text(
        root,
        ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
    )

    buyer_name = _get_text(
        root, ".//cac:AccountingCustomerParty/cac:Party/cbc:Name"
    )
    buyer_vat = _get_text(
        root,
        ".//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
    )

    if not seller_name:
        errors.append("Missing seller name.")
    if not seller_vat:
        errors.append("Missing seller VAT (CompanyID).")
    if not buyer_name:
        errors.append("Missing buyer name.")
    if not buyer_vat:
        errors.append("Missing buyer VAT (CompanyID).")

    # 4) المجاميع في الـ Header
    tax_total_header = _get_text(root, ".//cac:TaxTotal/cbc:TaxAmount")
    line_ext_header = _get_text(
        root, ".//cac:LegalMonetaryTotal/cbc:LineExtensionAmount"
    )
    tax_inclusive_header = _get_text(
        root, ".//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"
    )

    tax_total_header_val = _to_float(tax_total_header, 0.0)
    line_ext_header_val = _to_float(line_ext_header, 0.0)
    tax_inclusive_header_val = _to_float(tax_inclusive_header, 0.0)

    # 5) حساب المجاميع من الـ Line Items
    lines = root.findall(".//cac:InvoiceLine", NS)
    sum_lines_subtotal = 0.0
    sum_lines_vat = 0.0

    for line in lines:
        line_ext = _get_text(line, "./cbc:LineExtensionAmount")
        line_ext_val = _to_float(line_ext, 0.0)
        sum_lines_subtotal += line_ext_val

        # VAT per line (TaxTotal/TaxSubtotal/TaxAmount)
        line_tax_amount = _get_text(
            line, "./cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount"
        )
        sum_lines_vat += _to_float(line_tax_amount, 0.0)

    # 6) مقارنة المجاميع (نسمح بفارق صغير 0.01)
    EPS = 0.01

    if lines:
        if abs(sum_lines_subtotal - line_ext_header_val) > EPS:
            errors.append(
                f"LineExtensionAmount total ({line_ext_header_val}) "
                f"does not match sum of lines ({sum_lines_subtotal})."
            )

        if abs(sum_lines_vat - tax_total_header_val) > EPS:
            errors.append(
                f"TaxTotal ({tax_total_header_val}) "
                f"does not match sum of line VAT ({sum_lines_vat})."
            )

        expected_tax_inclusive = round(
            sum_lines_subtotal + sum_lines_vat, 2
        )
        if abs(expected_tax_inclusive - tax_inclusive_header_val) > EPS:
            errors.append(
                f"TaxInclusiveAmount ({tax_inclusive_header_val}) "
                f"does not equal subtotal+VAT ({expected_tax_inclusive})."
            )

    # 7) QR / TLV موجود؟
    qr_node = root.find(".//cbc:EmbeddedDocumentBinaryObject", NS)
    if qr_node is None or not (qr_node.text or "").strip():
        warnings.append("QR (EmbeddedDocumentBinaryObject) is missing or empty.")

    # 8) النتيجة النهائية
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }
