from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml
from validator import validate_invoice_xml

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine"
    })

# ---------------------------
# 1) توقيع XML مباشر
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
# 2) بناء + توقيع فاتورة UBL
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

# ---------------------------
# 3) التحقق من الفاتورة (Validation)
# ---------------------------
@app.route("/validate_xml", methods=["POST"])
def validate_xml():
    try:
        xml_input = request.data.decode("utf-8")
        if not xml_input.strip():
            return jsonify({
                "status": "error",
                "message": "Empty XML body"
            }), 400

        result = validate_invoice_xml(xml_input)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "is_valid": False,
            "errors": [str(e)],
            "warnings": []
        }), 500


# تشغيل السيرفر لـ Render
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
