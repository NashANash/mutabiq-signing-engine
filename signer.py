import os
from signxml import XMLSigner, methods
from lxml import etree


def sign_xml(xml_input: str) -> str:
    # نقرأ المفتاح من Environment Variable بدل ملف
    pem = os.environ.get("PRIVATE_KEY")
    if not pem:
        raise RuntimeError("PRIVATE_KEY env var is not set")

    # نحول الـ XML إلى عنصر
    root = etree.fromstring(xml_input.encode("utf-8"))

    signer = XMLSigner(
        method=methods.detached,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
    )

    signed_root = signer.sign(
        root,
        key=pem.encode("utf-8"),
    )

    return etree.tostring(signed_root).decode("utf-8")