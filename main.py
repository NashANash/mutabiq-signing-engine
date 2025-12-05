from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml
from validator import validate_invoice_xml
from pdf_generator import generate_pdf_from_xml
import os

app = Flask(__name__)

# ===============================
# API KEY CONFIG
# ===============================
VALID_API_KEYS = {
    "test-key-123",
    "client-key-456"
}

def require_api_key():
    api_key = request.headers.get("X-API-Key")
    if api_key not in VALID_API_KEYS:
        return jsonify({
            "status": "error",
            "message": "Invalid or missing API Key"
        }), 401
    return None


# ===============================
# 0) Health Check (بدون API)
# ===============================
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine"
    })


# ===============================
# 1) Build + Sign Invoice
# ===============================
@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    auth_error = require_api_key()
    if auth_error:
        return auth_error

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


# ===============================
# 2) Validate XML
# ===============================
@app.route("/validate_invoice", methods=["POST"])
def validate_invoice():
    auth_error = require_api_key()
    if auth_error:
        return auth_error

    try:
        xml_input = request.data.decode("utf-8")
        result = validate_invoice_xml(xml_input)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "is_valid": False,
            "errors": [str(e)],
            "warnings": []
        }), 500


# ===============================
# 3) OpenAPI Spec
# ===============================
@app.route("/openapi.json", methods=["GET"])
def openapi():
    with open("openapi.json", "r") as f:
        return f.read(), 200, {"Content-Type": "application/json"}


# ===============================
# 4) Swagger Docs
# ===============================
@app.route("/docs", methods=["GET"])
def docs():
    html = """
    <html>
    <head>
      <title>Mutabiq API Docs</title>
      <link rel="stylesheet"
            href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
    </head>
    <body>
      <div id="swagger"></div>
      <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
      <script>
        window.onload = () => {
          SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger'
          })
        }
      </script>
    </body>
    </html>
    """
    return html


# ===============================
# 5) Generate PDF
# ===============================
@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    auth_error = require_api_key()
    if auth_error:
        return auth_error

    try:
        xml_input = request.data.decode("utf-8")
        filename = generate_pdf_from_xml(xml_input)

        return jsonify({
            "status": "success",
            "pdf_file": filename
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ===============================
# Run
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
