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
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    try:
        data = request.get_json(force=True)

        # نبني UBL XML
        invoice_xml = build_invoice_xml(data)

        # فحص الفاتورة قبل التوقيع
        valid, msg = validate_invoice_xml(invoice_xml)
        if not valid:
            return jsonify({
                "status": "invalid",
                "message": msg,
                "invoice_xml": invoice_xml
            }), 400

        # توقيع XML
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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
