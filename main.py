from flask import Flask, request, jsonify
from signer import sign_xml
from invoice_builder import build_invoice_xml
from validator import validate_invoice_xml
from pdf_generator import generate_pdf_from_xml
import os
import time
import hashlib
from collections import defaultdict, deque

app = Flask(__name__)

# ===============================
# 1) CLIENTS + PLANS CONFIG (SaaS Core)
# ===============================
API_CLIENTS = {
    # Demo / Testing client
    "test-key-123": {
        "client_id": "cli_001",
        "name": "demo-client",
        "plan": "starter",
        "status": "active",
        "features": {"sign_invoice", "validate_invoice", "generate_pdf"},
        "rate_limit_per_min": 60,   # requests/min
    },

    # Another client example
    "client-key-456": {
        "client_id": "cli_002",
        "name": "second-client",
        "plan": "pro",
        "status": "active",
        "features": {"sign_invoice", "validate_invoice", "generate_pdf", "audit"},
        "rate_limit_per_min": 600,  # requests/min
    },
}

# ===============================
# 2) IN-MEMORY STORES (Phase 1)
# ===============================
# Usage logs (simple)
USAGE_LOGS = []  # list of dicts

# Rate limiting storage: {client_id: deque[timestamps]}
RATE_BUCKET = defaultdict(lambda: deque())

# Invoice fingerprint storage: {client_id: set(fingerprints)}
INVOICE_FINGERPRINTS = defaultdict(set)

# ===============================
# 3) HELPERS
# ===============================
def _get_api_key():
    # Support both x-api-key and X-API-Key to avoid Postman confusion
    return request.headers.get("x-api-key") or request.headers.get("X-API-Key")

def get_client_or_401():
    api_key = _get_api_key()
    client = API_CLIENTS.get(api_key)

    if not api_key or not client:
        return None, (jsonify({"status": "error", "message": "Invalid or missing API Key"}), 401)

    if client.get("status") != "active":
        return None, (jsonify({"status": "error", "message": "Client disabled"}), 403)

    return client, None

def require_feature(client, feature_name):
    if feature_name not in client.get("features", set()):
        return jsonify({
            "status": "error",
            "message": f"Feature '{feature_name}' not allowed for this client"
        }), 403
    return None

def rate_limit_check(client):
    """
    Simple fixed-window-ish limiter using sliding window (last 60 seconds).
    """
    client_id = client["client_id"]
    limit = int(client.get("rate_limit_per_min", 60))
    now = time.time()

    bucket = RATE_BUCKET[client_id]
    # remove older than 60s
    while bucket and (now - bucket[0]) > 60:
        bucket.popleft()

    if len(bucket) >= limit:
        retry_after = 60 - int(now - bucket[0])
        return jsonify({
            "status": "error",
            "message": "Rate limit exceeded",
            "retry_after_seconds": max(retry_after, 1)
        }), 429

    bucket.append(now)
    return None

def log_usage(client, endpoint, status_code, extra=None):
    USAGE_LOGS.append({
        "ts": int(time.time()),
        "client_id": client["client_id"],
        "plan": client["plan"],
        "endpoint": endpoint,
        "status_code": status_code,
        "extra": extra or {}
    })

def success_response(client, data):
    return jsonify({
        "status": "success",
        "client_id": client["client_id"],
        "plan": client["plan"],
        "data": data
    })

def error_response(client, message, code=500, error_code="SYSTEM_ERROR"):
    return jsonify({
        "status": "error",
        "client_id": client["client_id"] if client else None,
        "plan": client["plan"] if client else None,
        "error_code": error_code,
        "message": message
    }), code

def fingerprint_invoice(client_id: str, invoice_xml: str) -> str:
    # Hash invoice_xml for deduplication
    h = hashlib.sha256()
    h.update(invoice_xml.encode("utf-8"))
    return h.hexdigest()

def duplicate_check(client_id: str, fp: str):
    if fp in INVOICE_FINGERPRINTS[client_id]:
        return True
    INVOICE_FINGERPRINTS[client_id].add(fp)
    return False

# ===============================
# 0) Health Check (بدون API)
# ===============================
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mutabiq-signing-engine",
        "version": "v1.1-saas-core"
    })

# ===============================
# 1) Build + Sign Invoice
# ===============================
@app.route("/sign_invoice", methods=["POST"])
def sign_invoice():
    client, auth_error = get_client_or_401()
    if auth_error:
        return auth_error

    rl_error = rate_limit_check(client)
    if rl_error:
        log_usage(client, "/sign_invoice", 429)
        return rl_error

    feat_error = require_feature(client, "sign_invoice")
    if feat_error:
        log_usage(client, "/sign_invoice", 403)
        return feat_error

    try:
        data = request.get_json(force=True)
        invoice_xml = build_invoice_xml(data)

        # Fingerprint + Duplicate protection
        fp = fingerprint_invoice(client["client_id"], invoice_xml)
        if duplicate_check(client["client_id"], fp):
            log_usage(client, "/sign_invoice", 409, {"fingerprint": fp})
            return jsonify({
                "status": "error",
                "message": "Duplicate invoice detected",
                "fingerprint": fp
            }), 409

        signed = sign_xml(invoice_xml)

        log_usage(client, "/sign_invoice", 200, {"fingerprint": fp})

        return success_response(client, {
            "invoice_xml": invoice_xml,
            "signed_xml": signed,
            "fingerprint": fp
        })

    except Exception as e:
        log_usage(client, "/sign_invoice", 500, {"error": str(e)})
        return error_response(client, str(e), 500, "SIGN_ERROR")

# ===============================
# 2) Validate XML
# ===============================
@app.route("/validate_invoice", methods=["POST"])
def validate_invoice():
    client, auth_error = get_client_or_401()
    if auth_error:
        return auth_error

    rl_error = rate_limit_check(client)
    if rl_error:
        log_usage(client, "/validate_invoice", 429)
        return rl_error

    feat_error = require_feature(client, "validate_invoice")
    if feat_error:
        log_usage(client, "/validate_invoice", 403)
        return feat_error

    try:
        xml_input = request.data.decode("utf-8")
        result = validate_invoice_xml(xml_input)

        log_usage(client, "/validate_invoice", 200, {"is_valid": bool(result.get("is_valid", False))})

        # normalize response
        return success_response(client, result)

    except Exception as e:
        log_usage(client, "/validate_invoice", 500, {"error": str(e)})
        return error_response(client, str(e), 500, "VALIDATION_ERROR")

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
    client, auth_error = get_client_or_401()
    if auth_error:
        return auth_error

    rl_error = rate_limit_check(client)
    if rl_error:
        log_usage(client, "/generate_pdf", 429)
        return rl_error

    feat_error = require_feature(client, "generate_pdf")
    if feat_error:
        log_usage(client, "/generate_pdf", 403)
        return feat_error

    try:
        xml_input = request.data.decode("utf-8")
        filename = generate_pdf_from_xml(xml_input)

        log_usage(client, "/generate_pdf", 200, {"pdf_file": filename})

        return success_response(client, {"pdf_file": filename})

    except Exception as e:
        log_usage(client, "/generate_pdf", 500, {"error": str(e)})
        return error_response(client, str(e), 500, "PDF_ERROR")

# ===============================
# 6) Admin: Usage Summary (Backend-only helper)
# ===============================
@app.route("/admin/usage_summary", methods=["GET"])
def usage_summary():
    """
    Simple endpoint to view usage in dev.
    Protect it with a prod-only admin key later.
    """
    client, auth_error = get_client_or_401()
    if auth_error:
        return auth_error

    # allow only pro plan to view for now (or you can hardcode an admin feature)
    if client["plan"] != "pro":
        return jsonify({"status": "error", "message": "Not allowed"}), 403

    # summarize
    summary = defaultdict(int)
    for row in USAGE_LOGS:
        if row["client_id"] == client["client_id"]:
            key = f'{row["endpoint"]}:{row["status_code"]}'
            summary[key] += 1

    return success_response(client, {"summary": dict(summary), "total_logs": len(USAGE_LOGS)})

# ===============================
# Run
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
