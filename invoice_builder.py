import xml.etree.ElementTree as ET

def build_invoice_xml(data):
    root = ET.Element("Invoice")

    for key, value in data.items():
        child = ET.SubElement(root, key)
        child.text = str(value)

    return ET.tostring(root, encoding="utf-8").decode()