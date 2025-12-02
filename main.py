from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml
from validator import validate_invoice_xml

app = Flask(__name__)

# =========================
# 1) OpenAPI / Swagger Spec
# =========================

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Mutabiq Signing & Validation Engine",
        "version": "1.0.0",
        "description": "UBL Invoice builder + XML signer + validator for ZATCA-style invoices."
    },
    "paths": {
        "/": {
            "get": {
                "summary": "Health check",
                "description": "Simple health endpoint to check service status.",
                "responses": {
                    "200": {
                        "description": "Service is healthy"
                    }
                }
            }
        },
        "/sign_invoice": {
            "post": {
                "summary": "Build + Sign UBL invoice",
                "description": "Takes JSON invoice data, builds UBL 2.1 XML, and signs it with XML DSig.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "InvoiceNumber": {"type": "string"},
                                    "UUID": {"type": "string"},
                                    "IssueDate": {"type": "string", "example": "2025-11-27"},
                                    "Currency": {"type": "string", "example": "SAR"},
                                    "SellerName": {"type": "string", "example": "Mutabiq"},
                                    "SellerVAT": {"type": "string", "example": "300000000000003"},
                                    "BuyerName": {"type": "string", "example": "Test Client"},
                                    "BuyerVAT": {"type": "string", "example": "300000000000004"},
                                    "Items": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "Description": {"type": "string"},
                                                "Quantity": {"type": "number"},
                                                "UnitPrice": {"type": "number"},
                                                "VATRate": {"type": "number", "example": 15}
                                            },
                                            "required": ["Description", "Quantity", "UnitPrice"]
                                        }
                                    },
                                    "Subtotal": {"type": "number"},
                                    "Total": {"type": "number"},
                                    "VAT": {"type": "number"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Signed invoice XML",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "success"},
                                        "invoice_xml": {"type": "string"},
                                        "signed_xml": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/validate_invoice": {
            "post": {
                "summary": "Validate UBL invoice XML",
                "description": "Takes raw UBL XML in the body and returns validation result.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/xml": {
                            "schema": {
                                "type": "string"
                            }
                        },
                        "text/plain": {
                            "schema": {
                                "type": "string"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Validation result",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "is_valid": {"type": "boolean"},
                                        "errors": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "warnings": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


@app.route("/openapi.json", methods=["GET"])
def openapi_json():
    """
    يرجّع OpenAPI JSON للـ Swagger UI
    """
    return jsonify(OPENAPI_SPEC)


@app.route("/docs", methods=["GET"])
def swagger_ui():
    """
    صفحة Swagger UI بسيطة مبنية على CDN
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mutabiq API Docs</title>
        <link rel="stylesheet"
              href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    </head>
    <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = () => {
            window.ui = SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui'
            });
        };
    </script>
    </body>
    </html>
    """
    return html


# =========================
# 2) Endpoints الأساسية
# =========================

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine"
    })


@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    """
    يأخذ JSON لفاتورة، يبني UBL XML، ثم يوقّعه
    """
    try:
        data = request.get_json(force=True, silent=False)
        if not isinstance(data, dict):
            return jsonify({
                "status": "error",
                "message": "Body must be a JSON object"
            }), 400

        # بناء UBL XML
        invoice_xml = build_invoice_xml(data)

        # توقيع الفاتورة
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


@app.route("/validate_invoice", methods=["POST"])
def validate_invoice():
    """
    يستقبل XML خام في الـ body ويفحصه
    """
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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
