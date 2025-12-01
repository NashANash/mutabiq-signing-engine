from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml
from validator import validate_invoice_xml

app = Flask(__name__)

# ------------------------------------------------------
# 1) Health check
# ------------------------------------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine"
    })


# ------------------------------------------------------
# 2) Build + Sign Invoice
# ------------------------------------------------------
@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    try:
        data = request.get_json(force=True)
        invoice_xml = build_invoice_xml(data)
        signed = sign_xml(invoice_xml)

        return jsonify({
            "status": "success",
            "invoice_xml": invoice_xml,
            "signed_xml": signed
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ------------------------------------------------------
# 3) Validate Invoice XML
# ------------------------------------------------------
@app.route("/validate_invoice", methods=["POST"])
def validate_invoice():
    try:
        xml_input = request.data.decode("utf-8").strip()

        if not xml_input:
            return jsonify({
                "is_valid": False,
                "errors": ["No XML body provided"],
                "warnings": []
            }), 400

        result = validate_invoice_xml(xml_input)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "is_valid": False,
            "errors": [str(e)],
            "warnings": []
        }), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
