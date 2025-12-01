from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine",
        "version": "1.0.0"
    })

@app.route("/sign", methods=["POST"])
def sign_only():
    """
    يوقّع XML خام مُرسل مباشرة.
    """
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


@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    """
    يبني UBL XML من JSON ثم يوقّعه.
    """
    try:
        data = request.get_json(force=True, silent=False)

        if not isinstance(data, dict):
            return jsonify({
                "status": "error",
                "message": "Body must be a JSON object"
            }), 400

        # 1) بناء XML
        invoice_xml = build_invoice_xml(data)

        # 2) توقيع XML النهائي
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
