import xml.etree.ElementTree as ET

VAT_RATE = 0.15  # 15% VAT

def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_invoice_xml(data):
    currency = data.get("Currency", "SAR") or "SAR"

    items = data.get("Items") or data.get("items") or []
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
        subtotal_in = _to_float(data.get("Subtotal"))
        total_in = _to_float(data.get("Total"))
        vat_in = _to_float(data.get("VAT"))

        subtotal = subtotal_in
        vat_total = vat_in
        total = total_in

        if subtotal and not total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = round(subtotal + vat_total, 2)

        elif total and not subtotal:
            subtotal = round(total / (1 + VAT_RATE), 2)
            vat_total = round(total - subtotal, 2)

        elif subtotal and total:
            vat_total = round(subtotal * VAT_RATE, 2)
            total = round(subtotal + vat_total, 2)

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

    root = ET.Element(qname("", "Invoice"))

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

    # ---- Seller ----
    cac_supplier = ET.SubElement(root, qname("cac", "AccountingSupplierParty"))
    supplier_party = ET.SubElement(cac_supplier, qname("cac", "Party"))

    seller_name = ET.SubElement(supplier_party, qname("cbc", "Name"))
    seller_name.text = str(data.get("SellerName", ""))

    supplier_tax = ET.SubElement(supplier_party, qname("cac", "PartyTaxScheme"))
    seller_vat = ET.SubElement(supplier_tax, qname("cbc", "CompanyID"))
    seller_vat.text = str(data.get("SellerVAT", ""))

    # ---- Buyer ----
    cac_customer = ET.SubElement(root, qname("cac", "AccountingCustomerParty"))
    customer_party = ET.SubElement(cac_customer, qname("cac", "Party"))

    buyer_name = ET.SubElement(customer_party, qname("cbc", "Name"))
    buyer_name.text = str(data.get("BuyerName", ""))

    buyer_tax = ET.SubElement(customer_party, qname("cac", "PartyTaxScheme"))
    buyer_vat = ET.SubElement(buyer_tax, qname("cbc", "CompanyID"))
    buyer_vat.text = str(data.get("BuyerVAT", ""))

    # ---------------------------
    # D-2 + D-3  FULL Line Item Block
    # ---------------------------
    if has_items:
        index = 1
        for item in items:
            desc = str(item.get("Description", f"Item {index}"))
            qty = _to_float(item.get("Quantity"), 1.0)
            price = _to_float(item.get("UnitPrice"), 0.0)
            rate_percent = _to_float(item.get("VATRate"), 15)
            rate = rate_percent / 100.0

            line_subtotal = qty * price
            line_vat = round(line_subtotal * rate, 2)

            # InvoiceLine
            inv_line = ET.SubElement(root, qname("cac", "InvoiceLine"))

            line_id = ET.SubElement(inv_line, qname("cbc", "ID"))
            line_id.text = str(index)

            qty_el = ET.SubElement(inv_line, qname("cbc", "InvoicedQuantity"))
            qty_el.text = f"{qty:.2f}"

            ext_amount = ET.SubElement(inv_line, qname("cbc", "LineExtensionAmount"))
            ext_amount.set("currencyID", currency)
            ext_amount.text = f"{line_subtotal:.2f}"

            # ---- D-3: Item Details ----
            cac_item = ET.SubElement(inv_line, qname("cac", "Item"))
            name = ET.SubElement(cac_item, qname("cbc", "Name"))
            name.text = desc

            price_el = ET.SubElement(inv_line, qname("cac", "Price"))
            price_amount = ET.SubElement(price_el, qname("cbc", "PriceAmount"))
            price_amount.set("currencyID", currency)
            price_amount.text = f"{price:.2f}"

            # Tax block
            tax_total = ET.SubElement(inv_line, qname("cac", "TaxTotal"))
            tax_amount = ET.SubElement(tax_total, qname("cbc", "TaxAmount"))
            tax_amount.set("currencyID", currency)
            tax_amount.text = f"{line_vat:.2f}"

            tax_sub = ET.SubElement(tax_total, qname("cac", "TaxSubtotal"))

            taxable = ET.SubElement(tax_sub, qname("cbc", "TaxableAmount"))
            taxable.set("currencyID", currency)
            taxable.text = f"{line_subtotal:.2f}"

            tax_amt2 = ET.SubElement(tax_sub, qname("cbc", "TaxAmount"))
            tax_amt2.set("currencyID", currency)
            tax_amt2.text = f"{line_vat:.2f}"

            tax_cat = ET.SubElement(tax_sub, qname("cac", "TaxCategory"))
            percent_el = ET.SubElement(tax_cat, qname("cbc", "Percent"))
            percent_el.text = f"{rate_percent:.2f}"

            scheme = ET.SubElement(tax_cat, qname("cac", "TaxScheme"))
            scheme_id = ET.SubElement(scheme, qname("cbc", "ID"))
            scheme_id.text = "VAT"

            index += 1

    # ---- Totals ----
    cac_tax_total = ET.SubElement(root, qname("cac", "TaxTotal"))
    tax_amount = ET.SubElement(cac_tax_total, qname("cbc", "TaxAmount"))
    tax_amount.set("currencyID", currency)
    tax_amount.text = f"{vat_total:.2f}"

    cac_legal = ET.SubElement(root, qname("cac", "LegalMonetaryTotal"))

    ext = ET.SubElement(cac_legal, qname("cbc", "LineExtensionAmount"))
    ext.set("currencyID", currency)
    ext.text = f"{subtotal:.2f}"

    excl = ET.SubElement(cac_legal, qname("cbc", "TaxExclusiveAmount"))
    excl.set("currencyID", currency)
    excl.text = f"{subtotal:.2f}"

    incl = ET.SubElement(cac_legal, qname("cbc", "TaxInclusiveAmount"))
    incl.set("currencyID", currency)
    incl.text = f"{total:.2f}"

    payable = ET.SubElement(cac_legal, qname("cbc", "PayableAmount"))
    payable.set("currencyID", currency)
    payable.text = f"{total:.2f}"

    return ET.tostring(root, encoding="utf-8").decode()
