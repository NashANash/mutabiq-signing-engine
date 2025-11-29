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
    يبني فاتورة UBL 2.1 كاملة من JSON.
    يدعم:
      - Seller / Buyer
      - ProfileID + UUID
      - Line Items + Tax
      - Totals
      - VAT Category
    """

    currency = data.get("Currency", "SAR") or "SAR"

    # -----------------------------------------
    # (1) Line Items حساب المجاميع
    # -----------------------------------------
    items = data.get("Items") or []
    has_items = isinstance(items, list) and len(items) > 0

    subtotal = 0.0
    vat_total = 0.0
    total = 0.0

    if has_items:
        for item in items:
            qty = _to_float(item.get("Quantity"), 1.0)
            price = _to_float(item.get("UnitPrice"), 0.0)
            rate_percent = _to_float(item.get("VATRate"), 15)
            rate = rate_percent / 100.0

            line_subtotal = qty * price
            line_vat = round(line_subtotal * rate, 2)

            subtotal += line_subtotal
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
            vat_total = round(total - subtotal, 2)

        elif subtotal and total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = subtotal + vat_total

        else:
            subtotal = 0.0
            vat_total = 0.0
            total = 0.0

    # -----------------------------------------
    # (2) Namespaces
    # -----------------------------------------
    NSMAP = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }

    for p, u in NSMAP.items():
        ET.register_namespace(p, u)

    def q(prefix, tag):
        return f"{{{NSMAP[prefix]}}}{tag}"

    # -----------------------------------------
    # (3) الجذر + ProfileID + UUID
    # -----------------------------------------
    root = ET.Element(q("", "Invoice"))

    cbc_profile = ET.SubElement(root, q("cbc", "ProfileID"))
    cbc_profile.text = "reporting:1.0"

    cbc_id = ET.SubElement(root, q("cbc", "ID"))
    cbc_id.text = str(data.get("InvoiceNumber", ""))

    cbc_uuid = ET.SubElement(root, q("cbc", "UUID"))
    cbc_uuid.text = str(data.get("UUID", ""))

    cbc_issue = ET.SubElement(root, q("cbc", "IssueDate"))
    cbc_issue.text = str(data.get("IssueDate", ""))

    cbc_curr = ET.SubElement(root, q("cbc", "DocumentCurrencyCode"))
    cbc_curr.text = currency

    # -----------------------------------------
    # (4) Seller
    # -----------------------------------------
    supplier = ET.SubElement(root, q("cac", "AccountingSupplierParty"))
    party_s = ET.SubElement(supplier, q("cac", "Party"))

    seller_name = ET.SubElement(party_s, q("cbc", "Name"))
    seller_name.text = str(data.get("SellerName", ""))

    seller_tax = ET.SubElement(party_s, q("cac", "PartyTaxScheme"))
    seller_vat = ET.SubElement(seller_tax, q("cbc", "CompanyID"))
    seller_vat.text = str(data.get("SellerVAT", ""))

    # -----------------------------------------
    # (5) Buyer
    # -----------------------------------------
    customer = ET.SubElement(root, q("cac", "AccountingCustomerParty"))
    party_c = ET.SubElement(customer, q("cac", "Party"))

    buyer_name = ET.SubElement(party_c, q("cbc", "Name"))
    buyer_name.text = str(data.get("BuyerName", ""))

    buyer_tax = ET.SubElement(party_c, q("cac", "PartyTaxScheme"))
    buyer_vat = ET.SubElement(buyer_tax, q("cbc", "CompanyID"))
    buyer_vat.text = str(data.get("BuyerVAT", ""))

    # -----------------------------------------
    # (6) Line Items
    # -----------------------------------------
    if has_items:
        index = 1
        for item in items:
            qty = _to_float(item.get("Quantity"), 1.0)
            price = _to_float(item.get("UnitPrice"), 0.0)
            rate_percent = _to_float(item.get("VATRate"), 15)
            rate = rate_percent / 100.0

            line_subtotal = qty * price
            line_vat = round(line_subtotal * rate, 2)

            line = ET.SubElement(root, q("cac", "InvoiceLine"))

            lid = ET.SubElement(line, q("cbc", "ID"))
            lid.text = str(index)

            lqty = ET.SubElement(line, q("cbc", "InvoicedQuantity"))
            lqty.text = f"{qty:.2f}"

            lam = ET.SubElement(line, q("cbc", "LineExtensionAmount"))
            lam.set("currencyID", currency)
            lam.text = f"{line_subtotal:.2f}"

            # Item description
            item_block = ET.SubElement(line, q("cac", "Item"))
            name_el = ET.SubElement(item_block, q("cbc", "Name"))
            name_el.text = item.get("Description", f"Item {index}")

            # Tax
            tax_total = ET.SubElement(line, q("cac", "TaxTotal"))
            tax_amount = ET.SubElement(tax_total, q("cbc", "TaxAmount"))
            tax_amount.set("currencyID", currency)
            tax_amount.text = f"{line_vat:.2f}"

            tax_sub = ET.SubElement(tax_total, q("cac", "TaxSubtotal"))

            taxable = ET.SubElement(tax_sub, q("cbc", "TaxableAmount"))
            taxable.set("currencyID", currency)
            taxable.text = f"{line_subtotal:.2f}"

            taxamt = ET.SubElement(tax_sub, q("cbc", "TaxAmount"))
            taxamt.set("currencyID", currency)
            taxamt.text = f"{line_vat:.2f}"

            cat = ET.SubElement(tax_sub, q("cac", "TaxCategory"))
            percent_el = ET.SubElement(cat, q("cbc", "Percent"))
            percent_el.text = f"{rate_percent:.2f}"

            scheme = ET.SubElement(cat, q("cac", "TaxScheme"))
            sid = ET.SubElement(scheme, q("cbc", "ID"))
            sid.text = "VAT"

            index += 1

    # -----------------------------------------
    # (7) Totals
    # -----------------------------------------
    tax_total_root = ET.SubElement(root, q("cac", "TaxTotal"))
    tax_amt_root = ET.SubElement(tax_total_root, q("cbc", "TaxAmount"))
    tax_amt_root.set("currencyID", currency)
    tax_amt_root.text = f"{vat_total:.2f}"

    legal = ET.SubElement(root, q("cac", "LegalMonetaryTotal"))

    l1 = ET.SubElement(legal, q("cbc", "LineExtensionAmount"))
    l1.set("currencyID", currency)
    l1.text = f"{subtotal:.2f}"

    l2 = ET.SubElement(legal, q("cbc", "TaxExclusiveAmount"))
    l2.set("currencyID", currency)
    l2.text = f"{subtotal:.2f}"

    l3 = ET.SubElement(legal, q("cbc", "TaxInclusiveAmount"))
    l3.set("currencyID", currency)
    l3.text = f"{total:.2f}"

    l4 = ET.SubElement(legal, q("cbc", "PayableAmount"))
    l4.set("currencyID", currency)
    l4.text = f"{total:.2f}"

    return ET.tostring(root, encoding="utf-8").decode()
