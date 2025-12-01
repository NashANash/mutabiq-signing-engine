import xml.etree.ElementTree as ET

VAT_RATE = 0.15  # 15% VAT

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
    يبني فاتورة UBL 2.1 من JSON بسيط.

    يدعم حالياً:
      - بيانات البائع / المشتري
      - ProfileID + UUID
      - Subtotal / Total / VAT (أعلى الفاتورة)
      - Line Items اختيارية:
        "Items": [
          {
            "Description": "Item 1",
            "Quantity": "2",
            "UnitPrice": "50",
            "VATRate": "15"
          }
        ]
    """

    currency = data.get("Currency", "SAR") or "SAR"

    # ---------------------------
    # 1) حساب المجاميع (من الـ Items أو من القيم المباشرة)
    # ---------------------------
    items = data.get("Items") or data.get("items") or []
    has_items = isinstance(items, list) and len(items) > 0

    subtotal = 0.0
    vat_total = 0.0
    total = 0.0

    if has_items:
        # نحسب المجاميع من الأصناف
        for item in items:
            qty = _to_float(item.get("Quantity"), 1.0)
            price = _to_float(item.get("UnitPrice"), 0.0)
            rate_percent = _to_float(item.get("VATRate"), VAT_RATE * 100)
            rate = rate_percent / 100.0

            line_subtotal = qty * price
            line_vat = round(line_subtotal * rate, 2)

            subtotal += line_subtotal
            vat_total += line_vat

        total = round(subtotal + vat_total, 2)
    else:
        # نرجع للمنطق القديم لو ما فيه Items
        subtotal_in = _to_float(data.get("Subtotal"))
        total_in = _to_float(data.get("Total"))
        vat_in = _to_float(data.get("VAT"))

        subtotal = subtotal_in
        vat_total = vat_in
        total = total_in

        # 1) لو فقط Subtotal
        if subtotal and not total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = round(subtotal + vat_total, 2)

        # 2) لو فقط Total
        elif total and not subtotal:
            subtotal = round(total / (1 + VAT_RATE), 2)
            vat_total = round(total - subtotal, 2)

        # 3) لو موجودين مع بعض
        elif subtotal and total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = round(subtotal + vat_total, 2)

        else:
            subtotal = 0.0
            vat_total = 0.0
            total = 0.0

    # ---------------------------
    # 2) تعريف الـ namespaces الخاصة بـ UBL
    # ---------------------------
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

    # ---------------------------
    # 3) الجذر: Invoice + ProfileID + UUID
    # ---------------------------
    root = ET.Element(qname("", "Invoice"))

    # ProfileID ثابت حالياً (ممكن نخليه من JSON لاحقاً)
    cbc_profile = ET.SubElement(root, qname("cbc", "ProfileID"))
    cbc_profile.text = "reporting:1.0"

    cbc_id = ET.SubElement(root, qname("cbc", "ID"))
    cbc_id.text = str(data.get("InvoiceNumber", ""))

    cbc_uuid = ET.SubElement(root, qname("cbc", "UUID"))
    cbc_uuid.text = str(data.get("UUID", ""))

    cbc_issue_date = ET.SubElement(root, qname("cbc", "IssueDate"))
    cbc_issue_date.text = str(data.get("IssueDate", ""))

    cbc_currency = ET.SubElement(root, qname("cbc", "DocumentCurrencyCode"))
    cbc_currency.text = currency

    # ---------------------------
    # 4) بيانات البائع
    # ---------------------------
    cac_supplier = ET.SubElement(root, qname("cac", "AccountingSupplierParty"))
    supplier_party = ET.SubElement(cac_supplier, qname("cac", "Party"))

    seller_name = ET.SubElement(supplier_party, qname("cbc", "Name"))
    seller_name.text = str(data.get("SellerName", ""))

    supplier_tax = ET.SubElement(supplier_party, qname("cac", "PartyTaxScheme"))
    seller_vat = ET.SubElement(supplier_tax, qname("cbc", "CompanyID"))
    seller_vat.text = str(data.get("SellerVAT", ""))

    # ---------------------------
    # 5) بيانات المشتري
    # ---------------------------
    cac_customer = ET.SubElement(root, qname("cac", "AccountingCustomerParty"))
    customer_party = ET.SubElement(cac_customer, qname("cac", "Party"))

    buyer_name = ET.SubElement(customer_party, qname("cbc", "Name"))
    buyer_name.text = str(data.get("BuyerName", ""))

    buyer_tax = ET.SubElement(customer_party, qname("cac", "PartyTaxScheme"))
    buyer_vat = ET.SubElement(buyer_tax, qname("cbc", "CompanyID"))
    buyer_vat.text = str(data.get("BuyerVAT", ""))

    # ---------------------------
    # 6) Line Items (اختيارية)
    # ---------------------------
    if has_items:
        line_index = 1
        for item in items:
            desc = str(item.get("Description", f"Item {line_index}"))
            qty = _to_float(item.get("Quantity"), 1.0)
            price = _to_float(item.get("UnitPrice"), 0.0)
            rate_percent = _to_float(item.get("VATRate"), VAT_RATE * 100)
            rate = rate_percent / 100.0

            line_subtotal = qty * price
            line_vat = round(line_subtotal * rate, 2)

            # InvoiceLine
            inv_line = ET.SubElement(root, qname("cac", "InvoiceLine"))

            line_id = ET.SubElement(inv_line, qname("cbc", "ID"))
            line_id.text = str(line_index)

            qty_el = ET.SubElement(inv_line, qname("cbc", "InvoicedQuantity"))
            qty_el.text = f"{qty:.2f}"

            line_amount = ET.SubElement(inv_line, qname("cbc", "LineExtensionAmount"))
            line_amount.set("currencyID", currency)
            line_amount.text = f"{line_subtotal:.2f}"

            # Item name
            cac_item = ET.SubElement(inv_line, qname("cac", "Item"))
            item_name = ET.SubElement(cac_item, qname("cbc", "Name"))
            item_name.text = desc

            # TaxTotal + TaxCategory لكل سطر
            tax_total = ET.SubElement(inv_line, qname("cac", "TaxTotal"))
            tax_amount = ET.SubElement(tax_total, qname("cbc", "TaxAmount"))
            tax_amount.set("currencyID", currency)
            tax_amount.text = f"{line_vat:.2f}"

            tax_subtotal = ET.SubElement(tax_total, qname("cac", "TaxSubtotal"))

            taxable_amount = ET.SubElement(tax_subtotal, qname("cbc", "TaxableAmount"))
            taxable_amount.set("currencyID", currency)
            taxable_amount.text = f"{line_subtotal:.2f}"

            line_tax_amount = ET.SubElement(tax_subtotal, qname("cbc", "TaxAmount"))
            line_tax_amount.set("currencyID", currency)
            line_tax_amount.text = f"{line_vat:.2f}"

            tax_cat = ET.SubElement(tax_subtotal, qname("cac", "TaxCategory"))
            percent_el = ET.SubElement(tax_cat, qname("cbc", "Percent"))
            percent_el.text = f"{rate_percent:.2f}"

            tax_scheme = ET.SubElement(tax_cat, qname("cac", "TaxScheme"))
            tax_scheme_id = ET.SubElement(tax_scheme, qname("cbc", "ID"))
            tax_scheme_id.text = "VAT"

            line_index += 1

    # ---------------------------
    # 7) TaxTotal (إجمالي) + LegalMonetaryTotal
    # ---------------------------
    cac_tax_total = ET.SubElement(root, qname("cac", "TaxTotal"))
    tax_amount = ET.SubElement(cac_tax_total, qname("cbc", "TaxAmount"))
    tax_amount.set("currencyID", currency)
    tax_amount.text = f"{vat_total:.2f}"

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
