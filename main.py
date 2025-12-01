from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml
from validator import validate_invoice_xml

app = Flask(__name__)

# ---------------------------
# Health Check
# ---------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine"
    })


# ---------------------------
# 1) توقيع XML جاهز
# ---------------------------
@app.route("/sign", methods=["POST"])
def sign_only():
    try:
        xml_input = request.data.decode("utf-8")

        if not xml_input.strip():
            return jsonify({
                "status": "error",
                "message": "Empty XML body"
            }), 400

        signed = sign_xml(xml_input)

        return jsonify({
            "status": "success",
            "signed_xml": signed
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ---------------------------
# 2) بناء فاتورة + توقيعها
# ---------------------------
@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    try:
        data = request.get_json(force=True, silent=False)

        if not isinstance(data, dict):
            return jsonify({
                "status": "error",
                "message": "Body must be a JSON object"
            }), 400

        # Build UBL XML
        invoice_xml = build_invoice_xml(data)

        # Sign XML
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


# ---------------------------
# 3) فحص (Validation) للفاتورة
# ---------------------------
@app.route("/validate_invoice", methods=["POST"])
def validate_invoice():
    try:
        xml_input = request.data.decode("utf-8")

        if not xml_input.strip():
            return jsonify({
                "is_valid": False,
                "errors": ["Empty XML body"],
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


# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
