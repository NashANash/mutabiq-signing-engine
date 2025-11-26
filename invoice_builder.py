def build_invoice_xml(data):
    invoice_number = data.get("InvoiceNumber", "")
    customer = data.get("Customer", "")
    total = data.get("Total", "")
    vat = data.get("VAT", "")
    issue_date = data.get("IssueDate", "2025-01-01")

    xml = f"""
    <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
             xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
             xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">

        <cbc:ID>{invoice_number}</cbc:ID>
        <cbc:IssueDate>{issue_date}</cbc:IssueDate>

        <cac:AccountingCustomerParty>
            <cac:Party>
                <cbc:Name>{customer}</cbc:Name>
            </cac:Party>
        </cac:AccountingCustomerParty>

        <cac:LegalMonetaryTotal>
            <cbc:TaxInclusiveAmount>{total}</cbc:TaxInclusiveAmount>
            <cbc:TaxExclusiveAmount>{total}</cbc:TaxExclusiveAmount>
            <cbc:AllowanceTotalAmount>0</cbc:AllowanceTotalAmount>
            <cbc:ChargeTotalAmount>0</cbc:ChargeTotalAmount>
            <cbc:PayableAmount>{total}</cbc:PayableAmount>
        </cac:LegalMonetaryTotal>

        <cac:TaxTotal>
            <cbc:TaxAmount>{vat}</cbc:TaxAmount>
        </cac:TaxTotal>

    </Invoice>
    """

    return xml.strip()
