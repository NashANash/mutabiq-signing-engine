import xml.etree.ElementTree as ET

REQUIRED_CBC = [
    "ProfileID",
    "ID",
    "UUID",
    "IssueDate",
    "DocumentCurrencyCode",
]

REQUIRED_SUPPLIER = [
    "SellerName",
    "SellerVAT",
]

REQUIRED_BUYER = [
    "BuyerName",
    "BuyerVAT",
]

def _fail(msg):
    return {"status": "error", "message": msg}

def validate_invoice_xml(xml_string):
    """
    يتحقق من:
    - العناصر الأساسية D-1 + D-2 + D-3
    - البائع
    - المشتري
    - وجود الخطوط (Line Items)
    - TaxTotal + LegalMonetaryTotal
    """

    try:
        root = ET.fromstring(xml_string)
    except Exception as e:
        return _fail(f"XML parsing error: {str(e)}")

    ns = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }

    def find(path):
        return root.find(path, ns)

    # -----------------------------------
    # 1) التحقق من عناصر الـ CBC الأساسية
    # -----------------------------------
    for tag in REQUIRED_CBC:
        el = find(f"cbc:{tag}")
        if el is None or (el.text is None or el.text.strip() == ""):
            return _fail(f"Missing or empty field: {tag}")

    # -----------------------------------
    # 2) تحقق بيانات البائع D-2
    # -----------------------------------
    supplier_name = find("cac:AccountingSupplierParty/cac:Party/cbc:Name")
    supplier_vat = find("cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID")

    if supplier_name is None or supplier_name.text.strip() == "":
        return _fail("Missing SellerName")
    if supplier_vat is None or supplier_vat.text.strip() == "":
        return _fail("Missing SellerVAT")

    # -----------------------------------
    # 3) تحقق بيانات المشتري D-3
    # -----------------------------------
    buyer_name = find("cac:AccountingCustomerParty/cac:Party/cbc:Name")
    buyer_vat = find("cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID")

    if buyer_name is None or buyer_name.text.strip() == "":
        return _fail("Missing BuyerName")
    if buyer_vat is None or buyer_vat.text.strip() == "":
        return _fail("Missing BuyerVAT")

    # -----------------------------------
    # 4) تحقق من Line Items
    # -----------------------------------
    lines = root.findall("cac:InvoiceLine", ns)
    if len(lines) == 0:
        return _fail("Invoice must contain at least one InvoiceLine")

    # تحقق داخل كل Line
    for idx, line in enumerate(lines, start=1):
        id_el = line.find("cbc:ID", ns)
        amount = line.find("cbc:LineExtensionAmount", ns)
        item = line.find("cac:Item/cbc:Name", ns)

        if id_el is None:
            return _fail(f"Line {idx}: Missing ID")
        if amount is None:
            return _fail(f"Line {idx}: Missing LineExtensionAmount")
        if item is None:
            return _fail(f"Line {idx}: Missing Item Name")

    # -----------------------------------
    # 5) تحقق من وجود TaxTotal + LegalMonetaryTotal
    # -----------------------------------
    tax_total = find("cac:TaxTotal/cbc:TaxAmount")
    legal_total = find("cac:LegalMonetaryTotal/cbc:PayableAmount")

    if tax_total is None:
        return _fail("Missing TaxTotal")
    if legal_total is None:
        return _fail("Missing LegalMonetaryTotal → PayableAmount")

    # -----------------------------------
    # إذا مرّ كل شيء:
    # -----------------------------------
    return {"status": "success", "message": "Invoice XML is valid and compliant"}